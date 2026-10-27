"""ReaCue Studio : données de l'écran « Travail » (page web studio.html servie par REAPER).

Publié dans <ressources REAPER>/reaper_www_root/ à côté du prompteur :
  - studio.html + reacue_studio/ (CSS, JS, polices embarquées) : copiés depuis reacue_mcp/web/ ;
  - reacue_peaks.json : formes d'onde des stems (pics min/max précalculés, ~1 valeur par 40 ms), avec le
    nom de la piste REAPER de chaque stem (la page retrouve la piste par son nom dans /_/TRACK), son rôle
    et le réglage du timecode (SMPTE affiché).

Les pics sont calculés sur la timeline de REAPER (position des items APRÈS calage) : la page les aligne
directement sur la position de lecture. Format compact : par piste, une chaîne base64 d'octets
(min, max) entrelacés, 0..254 avec 127 = silence, normalisés au pic de la piste (affichage seulement).
"""
from __future__ import annotations

import base64
import json
import math
import shutil
from pathlib import Path

import numpy as np

WEB_DIR = Path(__file__).parent / "web"
STATIC_PAGES = ("studio.html",)
STATIC_DIR = "reacue_studio"              # CSS, JS et polices (sous-dossier de reaper_www_root)
PEAKS_NAME = "reacue_peaks.json"
HOP = 0.04                                # s par valeur (25 valeurs / s)
MAX_SECONDS = 3 * 3600                    # garde-fou (projet anormalement long)


# --------------------------------------------------------------------------- fichiers statiques
def static_files() -> list[tuple[Path, str]]:
    """[(source, chemin publié relatif à reaper_www_root)] : page Studio, CSS/JS, polices et licences."""
    out = [(WEB_DIR / p, p) for p in STATIC_PAGES if (WEB_DIR / p).exists()]
    root = WEB_DIR / STATIC_DIR
    if root.is_dir():
        for f in sorted(root.rglob("*")):
            if f.is_file() and not f.name.startswith("."):
                out.append((f, f.relative_to(WEB_DIR).as_posix()))
    return out


def publish_static(www: Path) -> list[str]:
    """Copie la page Studio et ses ressources dans reaper_www_root (seulement les fichiers changés)."""
    www = Path(www)
    done = []
    for src, rel in static_files():
        dst = www / rel
        try:
            if dst.exists() and dst.stat().st_size == src.stat().st_size and dst.read_bytes() == src.read_bytes():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            tmp = dst.with_name(dst.name + ".tmp")
            shutil.copyfile(src, tmp)
            tmp.replace(dst)
            done.append(rel)
        except OSError:
            continue
    return done


# --------------------------------------------------------------------------- pics
def _read_mono(path: str) -> tuple[np.ndarray, int]:
    import soundfile as sf
    try:
        y, sr = sf.read(str(path), dtype="float32", always_2d=True)
        return y.mean(axis=1), int(sr)
    except Exception:                    # format non lu par libsndfile (rare) : librosa (audioread)
        import librosa
        y, sr = librosa.load(str(path), sr=None, mono=True)
        return y.astype(np.float32), int(sr)


def item_peaks(y: np.ndarray, sr: int, position: float, offset: float, rate: float, length: float | None,
               n: int, hop: float = HOP) -> tuple[np.ndarray, np.ndarray]:
    """Pics (min, max) d'un item sur la grille de la timeline (n cases de `hop` secondes).
    Échantillon i de la source -> temps timeline position + (i/sr - offset)/rate ; borné à l'item."""
    lo = np.zeros(n, dtype=np.float32)
    hi = np.zeros(n, dtype=np.float32)
    rate = float(rate or 1.0)
    if rate <= 0 or len(y) == 0 or n <= 0:
        return lo, hi
    i0 = max(0, int(math.floor(offset * sr)))
    i1 = len(y)
    if length is not None and length > 0:
        i1 = min(i1, int(math.ceil((offset + length * rate) * sr)))
    if i1 <= i0:
        return lo, hi
    block = 1 << 20                      # par blocs : mémoire bornée sur les longs fichiers
    for a in range(i0, i1, block):
        b = min(i1, a + block)
        seg = y[a:b]
        t = position + (np.arange(a, b, dtype=np.float64) / sr - offset) / rate
        idx = np.floor(t / hop).astype(np.int64)
        keep = (idx >= 0) & (idx < n)
        if not keep.any():
            continue
        seg, idx = seg[keep], idx[keep]
        starts = np.flatnonzero(np.r_[True, idx[1:] != idx[:-1]])
        cells = idx[starts]
        np.minimum.at(lo, cells, np.minimum.reduceat(seg, starts))
        np.maximum.at(hi, cells, np.maximum.reduceat(seg, starts))
    return lo, hi


def encode_peaks(lo: np.ndarray, hi: np.ndarray) -> tuple[str, float]:
    """(base64 des octets min/max entrelacés, pic d'origine). Normalisé au pic de la piste."""
    peak = float(max(np.max(np.abs(lo)) if len(lo) else 0.0, np.max(np.abs(hi)) if len(hi) else 0.0))
    g = 1.0 / peak if peak > 1e-6 else 0.0
    q = np.empty(len(lo) * 2, dtype=np.uint8)
    q[0::2] = np.clip(np.round(lo * g * 127.0) + 127, 0, 254).astype(np.uint8)
    q[1::2] = np.clip(np.round(hi * g * 127.0) + 127, 0, 254).astype(np.uint8)
    return base64.b64encode(q.tobytes()).decode("ascii"), round(peak, 5)


def decode_peaks(s: str) -> tuple[np.ndarray, np.ndarray]:
    """Inverse d'encode_peaks (tests) : valeurs -1..1."""
    q = np.frombuffer(base64.b64decode(s), dtype=np.uint8).astype(np.float32)
    return (q[0::2] - 127) / 127.0, (q[1::2] - 127) / 127.0


def build_peaks(items: list[dict], duration: float, song_id: str = "", hop: float = HOP,
                roles: list[str] | None = None, tc: dict | None = None) -> dict:
    """items : [{file, position (timeline, après calage), offset, rate, length, track, guid}].
    Une entrée par piste REAPER (plusieurs items sur une même piste : réunis)."""
    from .analysis import assign_roles
    duration = max(hop, min(float(duration), MAX_SECONDS))
    n = int(math.ceil(duration / hop))
    roles = roles or assign_roles([d.get("file", "") for d in items])
    tracks: dict[str, dict] = {}
    order: list[str] = []
    rate0 = None
    for d, role in zip(items, roles):
        name = str(d.get("track") or Path(str(d.get("file", ""))).stem)
        if name not in tracks:
            tracks[name] = {"lo": np.zeros(n, np.float32), "hi": np.zeros(n, np.float32), "role": role,
                            "guid": d.get("guid", ""), "files": []}
            order.append(name)
        try:
            y, sr = _read_mono(d["file"])
        except Exception:
            continue
        rate0 = rate0 or sr
        rate = float(d.get("rate") or 1.0)
        lo, hi = item_peaks(y, sr, float(d.get("position", 0.0)), float(d.get("offset", 0.0)), rate,
                            float(d["length"]) if d.get("length") else None, n, hop)
        tr = tracks[name]
        tr["lo"] = np.minimum(tr["lo"], lo)
        tr["hi"] = np.maximum(tr["hi"], hi)
        tr["files"].append(Path(str(d["file"])).name)
    out = []
    for name in order:
        tr = tracks[name]
        data, peak = encode_peaks(tr["lo"], tr["hi"])
        out.append({"name": name, "role": str(tr["role"]).split("_")[0] if tr["role"] else "other",
                    "guid": tr["guid"], "peak": peak, "data": data})
    res = {"version": 1, "song_id": song_id, "hop": hop, "n": n, "duration": round(n * hop, 3), "sr": rate0,
           "tracks": out}
    if tc:
        res["tc"] = tc
    return res


def tc_info() -> dict:
    """Réglages du timecode pour l'afficheur SMPTE : fps, départ, sortie LTC/MTC configurée."""
    try:
        from . import timecode
        c = timecode.config()
        return {"fps": c["fps"], "tc_start": c["tc_start"], "offset_s": c["offset_s"],
                "ltc": bool(c.get("ltc")), "mtc": bool(c.get("mtc"))}
    except Exception:
        return {"fps": 25, "tc_start": "00:00:00:00", "offset_s": 0.0, "ltc": False, "mtc": False}


def placed_items(items: list[dict] | None, item: dict | None, plan_items: list[dict] | None,
                 plan_item: dict | None = None) -> list[dict]:
    """Items avec leur position APRÈS calage (plan["items"] / plan["item"] : {guid, position})."""
    src = list(items or ([item] if item else []))
    moved = {d["guid"]: d["position"] for d in (plan_items or []) if d.get("guid")}
    if plan_item and plan_item.get("guid"):
        moved[plan_item["guid"]] = plan_item["position"]
    out = []
    for d in src:
        if not d or not d.get("file"):
            continue
        e = dict(d)
        if d.get("guid") in moved:
            e["position"] = moved[d["guid"]]
        out.append(e)
    return out


def write_json(path: Path, data: dict):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)


def publish_peaks(items: list[dict], song: dict, www: Path | None = None) -> dict:
    """Calcule et publie reacue_peaks.json pour le morceau publié (song : reacue_song.json)."""
    from .prompter import WWW_DIR
    www = Path(www or WWW_DIR)
    bt = song.get("bar_times") or [0.0]
    end = max([float(bt[-1])] + [float(d.get("position", 0)) + float(d.get("length") or 0) for d in items])
    data = build_peaks(items, end + 1.0, song.get("id", ""), tc=tc_info())
    write_json(www / PEAKS_NAME, data)
    return {"peaks": str(www / PEAKS_NAME), "tracks": [t["name"] for t in data["tracks"]]}
