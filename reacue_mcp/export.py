"""Exports audio de ReaCue Studio : stems séparés ou mixés, en WAV ou MP3, sur une région du morceau.

Une « tâche » (job) décrit le projet REAPER et la demande :
  {"id": "k3f9…", "title": "<titre>", "project_dir": "<dossier du .RPP>" | null,
   "tracks": [{"name": "Basse", "guid": "{…}", "vol": 1.0, "pan": 0.0,
               "items": [{"file", "position", "length", "offset", "rate", "vol"}]}],
   "selection": [début, fin] | null,                  # sélection temporelle de REAPER (s)
   "song": {…} | null,                                # reacue_song.json (sinon relu dans reaper_www_root)
   "request": {"stems": ["Basse", …], "format": "wav" | "mp3", "kbps": 320,
               "range": {"kind": "song" | "section" | "bars" | "selection" | "time",
                         "section": 3, "from": 12, "to": 20, "start": 10.0, "end": 20.0},
               "mode": "separate" | "mix", "click": false, "fader": null, "normalize": true}}

Écrit par la fenêtre ReaCue (commande « export » de la page Studio, voir ReaCue_concert_lib.lua) ou par
le serveur MCP (set_sections([{"export": {…}}])). Les fichiers vont dans <dossier du projet>/exports/
et une copie dans reaper_www_root/reacue_exports/ (téléchargement depuis la page) ; l'état est publié dans
reaper_www_root/reacue_export.json (lu par la page).

Découpe : aux temps de la grille ReaCue (bar_times de reacue_song.json, timeline REAPER), arrondis à
l'échantillon (début = round(t0 * sr), longueur = round(t1 * sr) - round(t0 * sr)). Sources lues avec leur
position, leur décalage (offset), le volume de l'item ; vitesse ≠ 1 ou fréquence différente : rééchantillonnage
linéaire (suffisant pour du travail, pas pour un master). Volume et panoramique de la piste : appliqués au mix
(« fader » = null : oui pour un mix, non pour un stem seul). Mix : ramené à -1 dBFS s'il dépasse (pas d'écrêtage).
"""
from __future__ import annotations

import json
import math
import re
import shutil
import time
import unicodedata
from pathlib import Path

import numpy as np

STATUS_NAME = "reacue_export.json"
WEB_DIR_NAME = "reacue_exports"
KEEP_WEB_JOBS = 5                    # exports gardés dans reaper_www_root/reacue_exports
CEILING_DB = -1.0                    # plafond du mix (dBFS)
MP3_RATES = (96, 128, 160, 192, 224, 256, 320)
GENERATED = {"CLICK", "CUES", "TIMECODE LTC", "TIMECODE MTC"}

TXT = {
    "fr": {"mix": "Mix", "click": "Click", "bars": "Mes. {a}-{b}", "selection": "Sélection", "song": "",
           "running": "Export en cours… {k}/{n}", "done": "{n} fichier(s) exporté(s)", "no_stem": "Aucun stem choisi.",
           "no_range": "Région vide ou invalide.", "no_song": "Morceau introuvable (prompteur non publié).",
           "no_mp3": "MP3 indisponible : mets à jour soundfile (≥ 0.13) ou installe lameenc ; exporte en WAV.",
           "unknown": "Piste introuvable : {n}", "busy": "Un export est déjà en cours."},
    "en": {"mix": "Mix", "click": "Click", "bars": "Bars {a}-{b}", "selection": "Selection", "song": "",
           "running": "Exporting… {k}/{n}", "done": "{n} file(s) exported", "no_stem": "No stem selected.",
           "no_range": "Empty or invalid range.", "no_song": "Song not found (prompter not published).",
           "no_mp3": "MP3 unavailable: update soundfile (≥ 0.13) or install lameenc; export as WAV.",
           "unknown": "Track not found: {n}", "busy": "An export is already running."},
}


class ExportError(Exception):
    pass


def _t(key: str, **kw) -> str:
    from .i18n import get_lang
    return TXT.get(get_lang(), TXT["fr"])[key].format(**kw)


# --------------------------------------------------------------------------- noms de fichiers
def safe_name(s: str, max_len: int = 80) -> str:
    """Nom lisible sans caractère interdit (Windows / macOS)."""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", str(s))
    s = re.sub(r"\s+", " ", s).strip(" .")
    return (s[:max_len].rstrip(" .")) or "export"


def ascii_slug(s: str, max_len: int = 60) -> str:
    """Nom ASCII pour la copie web (servie par REAPER) : « Démo Étoile - Basse » -> « Demo_Etoile_-_Basse »."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z0-9._+-]+", "_", s).strip("_.")
    return s[:max_len] or "export"


def file_name(title: str, stem: str, region: str, ext: str) -> str:
    parts = [safe_name(title), safe_name(stem)] + ([safe_name(region)] if region else [])
    return " - ".join(parts) + "." + ext


# --------------------------------------------------------------------------- région
def bar_start(song: dict, bar: int) -> float:
    """Début de la mesure `bar` (1-based ; ≤ 0 = count-in ; n_bars + 1 = fin du morceau)."""
    bt = song["bar_times"]
    k = int(bar) - 1 + int(song.get("count_in_bars", 0))
    if not 0 <= k < len(bt):
        raise ExportError(_t("no_range"))
    return float(bt[k])


def resolve_range(song: dict | None, rng: dict | None, selection=None) -> tuple[float, float, str]:
    """(début, fin, libellé de la région) sur la timeline REAPER."""
    rng = rng or {"kind": "song"}
    kind = rng.get("kind", "song")
    if kind in ("selection", "time"):
        a, b = (selection or [None, None]) if kind == "selection" else (rng.get("start"), rng.get("end"))
        if a is None or b is None or float(b) - float(a) < 0.01:
            raise ExportError(_t("no_range"))
        return float(a), float(b), _t("selection") if kind == "selection" else ""
    if not song or not song.get("bar_times"):
        raise ExportError(_t("no_song"))
    if kind == "section":
        secs = song.get("sections") or []
        i = rng.get("section")
        s = None
        if isinstance(i, int) and 0 <= i < len(secs):
            s = secs[i]
        elif isinstance(i, str):
            s = next((x for x in secs if x.get("name") == i), None)
        if not s:
            raise ExportError(_t("no_range"))
        return bar_start(song, s["start_bar"]), bar_start(song, s["end_bar"] + 1), s["name"]
    if kind == "bars":
        a, b = int(rng.get("from", 1)), int(rng.get("to", 1))
        a, b = min(a, b), max(a, b)
        a = max(a, 1 - int(song.get("count_in_bars", 0)))
        b = min(b, int(song["n_bars"]))
        if b < a:
            raise ExportError(_t("no_range"))
        return bar_start(song, a), bar_start(song, b + 1), _t("bars", a=a, b=b)
    return bar_start(song, 1), float(song["bar_times"][-1]), _t("song")


# --------------------------------------------------------------------------- rendu
def _read(path: str, frames: tuple[int, int] | None = None) -> tuple[np.ndarray, int]:
    import soundfile as sf
    if frames:
        y, sr = sf.read(str(path), start=frames[0], stop=frames[1], dtype="float32", always_2d=True)
    else:
        y, sr = sf.read(str(path), dtype="float32", always_2d=True)
    return y, int(sr)


def _stereo(y: np.ndarray) -> np.ndarray:
    if y.shape[1] == 1:
        return np.repeat(y, 2, axis=1)
    return y[:, :2]


def source_rate(tracks: list[dict]) -> int:
    import soundfile as sf
    for tr in tracks:
        for it in tr.get("items") or []:
            try:
                return int(sf.info(str(it["file"])).samplerate)
            except Exception:
                continue
    return 44100


def render_item(it: dict, s0: int, s1: int, sr: int) -> tuple[int, np.ndarray] | None:
    """Échantillons [s0, s1) de la timeline (fréquence sr) couverts par l'item : (indice, données stéréo)."""
    import soundfile as sf
    pos = float(it.get("position", 0.0))
    off = float(it.get("offset", 0.0))
    rate = float(it.get("rate") or 1.0)
    length = it.get("length")
    info = sf.info(str(it["file"]))
    ssr = int(info.samplerate)
    src_len_t = info.frames / ssr                   # durée de la source (s)
    t_end = pos + (src_len_t - off) / rate
    if length:
        t_end = min(t_end, pos + float(length))
    ps, pe = int(round(pos * sr)), int(round(t_end * sr))
    a, b = max(ps, s0), min(pe, s1)
    if b <= a:
        return None
    gain = float(it.get("vol", 1.0) if it.get("vol") is not None else 1.0)
    if ssr == sr and abs(rate - 1.0) < 1e-9:
        # cas exact : échantillon j de la timeline = échantillon j - ps + round(offset * sr) de la source
        o = int(round(off * sr))
        fa, fb = a - ps + o, b - ps + o
        lo = max(0, fa)
        y, _ = _read(it["file"], (lo, max(lo, min(fb, info.frames))))
        y = _stereo(y)
        out = np.zeros((b - a, 2), np.float32)
        k = lo - fa
        out[k:k + len(y)] = y[:max(0, b - a - k)]
        return a, out * gain
    # vitesse ou fréquence différente : rééchantillonnage linéaire
    tt = np.arange(a, b, dtype=np.float64) / sr
    src_t = off + (tt - pos) * rate                  # temps dans la source
    fa = max(0, int(math.floor(src_t[0] * ssr)) - 1)
    fb = min(info.frames, int(math.ceil(src_t[-1] * ssr)) + 2)
    if fb <= fa:
        return None
    y, _ = _read(it["file"], (fa, fb))
    y = _stereo(y)
    x = np.arange(fa, fa + len(y), dtype=np.float64) / ssr
    out = np.stack([np.interp(src_t, x, y[:, c], left=0.0, right=0.0) for c in range(2)], axis=1)
    return a, out.astype(np.float32) * gain


def render_track(tr: dict, s0: int, s1: int, sr: int, fader: bool = False) -> np.ndarray:
    out = np.zeros((s1 - s0, 2), np.float32)
    for it in tr.get("items") or []:
        try:
            r = render_item(it, s0, s1, sr)
        except Exception:
            continue
        if r is None:
            continue
        a, y = r
        out[a - s0:a - s0 + len(y)] += y
    if fader:
        out *= float(tr.get("vol", 1.0) if tr.get("vol") is not None else 1.0)
        pan = max(-1.0, min(1.0, float(tr.get("pan") or 0.0)))
        if pan:
            out[:, 0] *= min(1.0, 1.0 - pan)
            out[:, 1] *= min(1.0, 1.0 + pan)
    return out


def render_click(song: dict, s0: int, s1: int, sr: int, level: float = 0.5) -> np.ndarray:
    """Click synthétique aux temps de la grille (le click de REAPER n'est pas un fichier) : 1er temps aigu."""
    out = np.zeros((s1 - s0, 2), np.float32)
    bt = [float(x) for x in song.get("bar_times") or []]
    bpb = max(1, int(song.get("beats_per_bar", 4)))
    n = int(0.03 * sr)
    env = np.exp(-np.arange(n) / (0.006 * sr)).astype(np.float32)
    tone = {f: (np.sin(2 * np.pi * f * np.arange(n) / sr).astype(np.float32) * env * level) for f in (1000, 1600)}
    for k in range(len(bt) - 1):
        L = bt[k + 1] - bt[k]
        for b in range(bpb):
            j = int(round((bt[k] + L * b / bpb) * sr)) - s0
            if j >= len(out) or j + n <= 0:
                continue
            x = tone[1600 if b == 0 else 1000]
            a, z = max(0, j), min(len(out), j + n)
            out[a:z] += x[a - j:z - j, None]
    return out


def limit(y: np.ndarray, ceiling_db: float = CEILING_DB) -> tuple[np.ndarray, float]:
    """Ramène le pic à `ceiling_db` s'il le dépasse (gain unique : pas de distorsion). Renvoie (y, gain)."""
    peak = float(np.max(np.abs(y))) if y.size else 0.0
    ceil = 10 ** (ceiling_db / 20)
    if peak > ceil:
        g = ceil / peak
        return (y * g).astype(np.float32), g
    return y, 1.0


# --------------------------------------------------------------------------- écriture
def mp3_backend() -> str | None:
    """"soundfile" (libsndfile ≥ 1.1 + soundfile ≥ 0.13 : débit réglable), "lameenc", ou None."""
    try:
        import soundfile as sf
        import inspect
        if "MP3" in sf.available_formats() and "bitrate_mode" in inspect.signature(sf.SoundFile.__init__).parameters:
            return "soundfile"
    except Exception:
        pass
    try:
        import lameenc  # noqa: F401
        return "lameenc"
    except Exception:
        return None


def write_audio(path: Path, y: np.ndarray, sr: int, fmt: str = "wav", kbps: int = 320):
    import soundfile as sf
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    y = np.clip(y, -1.0, 1.0).astype(np.float32)
    if fmt == "wav":
        sf.write(str(path), y, sr, subtype="PCM_24")
        return
    kbps = min(MP3_RATES, key=lambda r: abs(r - int(kbps or 320)))
    be = mp3_backend()
    if be == "soundfile":
        # libsndfile : débit constant = 320 - niveau * 288 kbit/s (MPEG-1 couche III)
        sf.write(str(path), y, sr, format="MP3", subtype="MPEG_LAYER_III", bitrate_mode="CONSTANT",
                 compression_level=max(0.0, min(0.99, (320 - kbps) / 288)))
    elif be == "lameenc":
        import lameenc
        enc = lameenc.Encoder()
        enc.set_bit_rate(kbps)
        enc.set_in_sample_rate(sr)
        enc.set_channels(2)
        enc.set_quality(2)
        pcm = (y * 32767).astype("<i2")
        path.write_bytes(enc.encode(pcm.tobytes()) + enc.flush())
    else:
        raise ExportError(_t("no_mp3"))


# --------------------------------------------------------------------------- état publié
def write_status(www: Path | None, data: dict):
    if not www:
        return
    from .studio import write_json
    try:
        write_json(Path(www) / STATUS_NAME, {**data, "time": time.time()})
    except OSError:
        pass


def clean_web(dir_: Path, keep: int = KEEP_WEB_JOBS, current: str | None = None):
    """Garde les fichiers des `keep` derniers exports (préfixe « <id>_ ») dans reaper_www_root/reacue_exports."""
    if not dir_.is_dir():
        return
    jobs: dict[str, float] = {}
    for f in dir_.iterdir():
        if f.is_file() and "_" in f.name:
            j = f.name.split("_", 1)[0]
            jobs[j] = max(jobs.get(j, 0.0), f.stat().st_mtime)
    old = sorted((j for j in jobs if j != current), key=lambda j: jobs[j], reverse=True)[max(0, keep - 1):]
    for f in dir_.iterdir():
        if f.is_file() and f.name.split("_", 1)[0] in old:
            try:
                f.unlink()
            except OSError:
                pass


def _song(job: dict, www: Path | None) -> dict | None:
    s = job.get("song")
    if not s and www and (Path(www) / "reacue_song.json").exists():
        try:
            s = json.loads((Path(www) / "reacue_song.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            s = None
    if s and s.get("concert") and s.get("songs"):           # concert : le morceau qui contient la région
        t = job.get("at")
        songs = s["songs"]
        cur = songs[0]
        for x in songs:
            if t is not None and x.get("start_t", 0) <= float(t) + 0.05:
                cur = x
        return cur
    return s


def run_job(job: dict, www: Path | None = None, progress=None) -> dict:
    """Exécute une tâche d'export ; renvoie {"files": [...], "dir": …}. Lève ExportError si la demande est invalide."""
    from .prompter import WWW_DIR
    www = Path(www) if www is not None else WWW_DIR
    req = job.get("request") or {}
    jid = re.sub(r"[^A-Za-z0-9]", "", str(job.get("id") or "")) or format(int(time.time() * 1000), "x")
    song = _song(job, www)
    title = job.get("title") or (song or {}).get("title") or "ReaCue"
    tracks = [t for t in job.get("tracks") or [] if t.get("items")]
    by_name = {t["name"]: t for t in tracks}
    names = [n for n in req.get("stems") or [] if n]
    missing = [n for n in names if n not in by_name]
    if missing:
        raise ExportError(_t("unknown", n=", ".join(missing)))
    click = bool(req.get("click"))
    if not names and not click:
        raise ExportError(_t("no_stem"))
    fmt = "mp3" if str(req.get("format", "wav")).lower() == "mp3" else "wav"
    if fmt == "mp3" and not mp3_backend():
        raise ExportError(_t("no_mp3"))
    kbps = int(req.get("kbps") or 320)
    t0, t1, region = resolve_range(song, req.get("range"), job.get("selection"))
    if click and not song:
        raise ExportError(_t("no_song"))
    sr = int(job.get("sr") or source_rate([by_name[n] for n in names] or tracks))
    s0, s1 = int(round(t0 * sr)), int(round(t1 * sr))
    if s1 - s0 < int(0.01 * sr):
        raise ExportError(_t("no_range"))
    mode = "mix" if req.get("mode") == "mix" else "separate"
    fader = req.get("fader")
    fader = (mode == "mix") if fader is None else bool(fader)
    out_dir = Path(job["project_dir"]) / "exports" if job.get("project_dir") else (www.parent / "ReaCueMCP" / "exports")
    web_dir = www / WEB_DIR_NAME
    files = []
    steps = len(names) + (1 if click else 0)

    def say(k):
        msg = _t("running", k=min(k, steps), n=steps)
        write_status(www, {"id": jid, "state": "running", "progress": round(k / max(1, steps + 1), 3), "step": msg})
        if progress:
            progress(msg)

    def emit(label: str, y: np.ndarray, normalize: bool):
        if normalize:
            y, _ = limit(y)
        name = file_name(title, label, region, fmt)
        dst = out_dir / name
        write_audio(dst, y, sr, fmt, kbps)
        web = web_dir / f"{jid}_{ascii_slug(Path(name).stem)}.{fmt}"
        try:
            web_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(dst, web)
            url = f"{WEB_DIR_NAME}/{web.name}"
        except OSError:
            url = None
        files.append({"name": name, "path": str(dst), "url": url, "bytes": dst.stat().st_size,
                      "seconds": round((s1 - s0) / sr, 3)})

    say(0)
    normalize = req.get("normalize", True) is not False
    if mode == "mix":
        acc = np.zeros((s1 - s0, 2), np.float32)
        for k, n in enumerate(names):
            acc += render_track(by_name[n], s0, s1, sr, fader)
            say(k + 1)
        if click:
            acc += render_click(song, s0, s1, sr)
        label = _t("mix") if len(names) != 1 else names[0]
        if len(names) in (2, 3):
            label = " + ".join(names)
        if click:
            label += " + " + _t("click")
        emit(label, acc, True)
    else:
        for k, n in enumerate(names):
            y = render_track(by_name[n], s0, s1, sr, fader)
            emit(n, y, normalize and float(np.max(np.abs(y)) if y.size else 0) > 1.0)
            say(k + 1)
        if click:
            emit(_t("click"), render_click(song, s0, s1, sr), False)
    clean_web(web_dir, current=jid)
    res = {"id": jid, "state": "done", "progress": 1.0, "files": files, "dir": str(out_dir),
           "region": region, "start": round(t0, 4), "end": round(t1, 4), "sr": sr, "format": fmt,
           "kbps": kbps if fmt == "mp3" else None, "message": _t("done", n=len(files))}
    write_status(www, res)
    return res


def run_job_file(path: Path, www: Path | None = None, progress=None) -> dict:
    """CLI : lit la tâche écrite par la fenêtre ReaCue ; en cas d'erreur, l'état publié l'indique."""
    from .prompter import WWW_DIR
    www = Path(www) if www is not None else WWW_DIR
    job = {}
    try:
        job = json.loads(Path(path).read_text(encoding="utf-8"))
        return run_job(job, www, progress)
    except Exception as e:
        write_status(www, {"id": str(job.get("id", "")), "state": "error", "message": str(e)})
        raise


def mcp_job(request: dict, items: list[dict], project: str | None, title: str | None = None,
            song: dict | None = None) -> dict:
    """Tâche construite par le serveur MCP à partir des items audio du pont (get_audio_items)."""
    tracks: dict[str, dict] = {}
    for d in items:
        name = d.get("track") or Path(str(d.get("file", ""))).stem
        if name in GENERATED:
            continue
        tr = tracks.setdefault(name, {"name": name, "guid": "", "vol": 1.0, "pan": 0.0, "items": []})
        tr["items"].append({"file": d["file"], "position": d.get("position", 0.0), "length": d.get("length"),
                            "offset": d.get("offset", 0.0), "rate": d.get("rate") or 1.0, "vol": 1.0})
    req = dict(request)
    if not req.get("stems") and not req.get("click"):
        req["stems"] = list(tracks)                    # par défaut : tous les stems
    return {"id": format(int(time.time() * 1000), "x"), "title": title,
            "project_dir": str(Path(project).parent) if project else None,
            "tracks": list(tracks.values()), "song": song, "request": req}
