"""Analyse de structure par SongFormer (composant optionnel) / SongFormer structure analysis (optional).

ReaCue garde sa grille (tempo, mesures, count-in) ; SongFormer (ASLP-lab, CC BY 4.0) ne fait que
découper et nommer les sections. Le modèle tourne dans l'environnement séparé .venv-structure
(installé par install/install_structure_*), jamais dans le .venv de ReaCue : ce module-ci ne dépend
ni de torch ni de SongFormer, il lance `reacue_structure.py` en sous-processus, lit son résultat (avec
cache par morceau) et cale les sections sur la grille de ReaCue.

Réglage `structure_engine` : "auto" (défaut : SongFormer s'il est installé, sinon la détection de
ReaCue) | "reacue" (détection de ReaCue seule) ; la variable d'environnement REACUE_STRUCTURE_ENGINE
l'emporte (tests). Tout échec retombe sur la détection de ReaCue, avec un
avertissement : la préparation n'est jamais bloquée.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # dossier d'installation de ReaCue
ENGINE = "songformer"
# révisions figées des dépôts téléchargés par install/install_structure_* (mêmes valeurs là-bas)
SONGFORMER_REV = "139b2aa3b14bd1c6d961d0994e9fc975f1ef7fd5"
MUQ_REV = "28847ea50cd31ac4b8b6a7dacc051ad7d1c7606a"
MUSICFM_REV = "b83ebedb401bcef639b26b05c0c8bee1dc2dfe71"
CACHE_VERSION = 1
TIMEOUT_S = 1800                 # 30 min : CPU lent + 1er lancement ; au-delà, détection de ReaCue

# étiquettes SongFormer -> nom de base ReaCue (clés internes en français, traduites ensuite)
LABEL_BASE = {
    "intro": "Intro", "verse": "Couplet", "pre-chorus": "Pré-refrain", "prechorus": "Pré-refrain",
    "chorus": "Refrain", "bridge": "Pont", "inst": "Instrumental", "instrumental": "Instrumental",
    "solo": "Solo", "outro": "Outro", "silence": "Break", "end": "Outro", "start": "Intro",
}
ALWAYS_NUMBERED = {"Couplet", "Refrain", "Pré-refrain"}
MIN_BARS = 2                     # segment plus court : fusionné avec un voisin
PHRASE = 4                       # carrure préférée quand une frontière en est à <= 1 mesure
MERGE_SAME_MAX = 16              # deux segments consécutifs de même type fusionnés si <= 16 mesures…
MERGE_SAME_MIN = 8               # … et si l'un des deux fait moins de 8 mesures (8 + 8 : deux couplets)
NEVER_NUMBERED = {"Instrumental", "Solo", "Intro", "Outro", "Break"}

PROGRESS = None                  # callback(message) facultatif (CLI : fichier d'état lu par REAPER)


# --------------------------------------------------------------------------- #
# Composant installé ?
# --------------------------------------------------------------------------- #
def structure_python(install_dir: Path | None = None, windows: bool | None = None) -> Path:
    d = Path(install_dir or ROOT)
    windows = (os.name == "nt") if windows is None else windows
    if windows:
        return d / ".venv-structure" / "Scripts" / "python.exe"
    return d / ".venv-structure" / "bin" / "python"


def available(install_dir: Path | None = None) -> bool:
    d = Path(install_dir or ROOT)
    return (structure_python(d).exists() and (d / "reacue_structure.py").is_file()
            and (d / "structure" / "SongFormer" / "app.py").is_file())


def engine_setting() -> str:
    env = os.environ.get("REACUE_STRUCTURE_ENGINE", "").lower()
    if env in ("auto", "reacue"):
        return env
    try:
        from .settings import load_settings
        v = str(load_settings().get("structure_engine") or "auto").lower()
    except Exception:
        v = "auto"
    return v if v in ("auto", "reacue") else "auto"


# --------------------------------------------------------------------------- #
# Calage sur la grille de ReaCue
# --------------------------------------------------------------------------- #
def _bar_pos(t: float, downbeats: list[float]) -> float:
    """Temps (s) -> position en mesures (0 = 1re mesure), interpolée sur la grille (beatmap compris)."""
    db = downbeats
    if t <= db[0]:
        span = (db[1] - db[0]) if len(db) > 1 else 1.0
        return (t - db[0]) / span
    if t >= db[-1]:
        span = (db[-1] - db[-2]) if len(db) > 1 else 1.0
        return len(db) - 1 + (t - db[-1]) / span
    lo, hi = 0, len(db) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if db[mid] <= t:
            lo = mid
        else:
            hi = mid
    return lo + (t - db[lo]) / (db[hi] - db[lo])


def _norm_label(label: str) -> str:
    return re.sub(r"[\s_]+", "-", str(label or "").strip().lower())


def snap_segments(segments: list[dict], downbeats: list[float]) -> list[dict]:
    """Segments SongFormer (secondes) -> [{start_bar (0-based), end_bar, label}] calés sur les mesures.

    Chaque frontière va sur la mesure la plus proche ; si une carrure de 4 mesures est à <= 1 mesure,
    elle est préférée (sans croiser une frontière voisine). Silence en début / fin ignoré, segments
    < 2 mesures fusionnés, la 1re section commence à la mesure 0 et la dernière finit à la fin."""
    n_bars = len(downbeats) - 1
    segs = [{"start": float(s["start"]), "end": float(s["end"]), "label": _norm_label(s["label"])}
            for s in segments if float(s["end"]) > float(s["start"])]
    segs.sort(key=lambda s: s["start"])
    # silence / début / fin aux extrémités : ignorés
    while segs and segs[0]["label"] in ("silence", "start", "end"):
        segs.pop(0)
    while segs and segs[-1]["label"] in ("silence", "start", "end"):
        segs.pop()
    if not segs or n_bars <= 0:
        return []
    raw = [_bar_pos(s["start"], downbeats) for s in segs[1:]]
    # carrure : longueur depuis la frontière précédente multiple de 4 si c'est à <= 1 mesure ;
    # frontières croissantes, au moins 1 mesure d'écart (les trop courtes sont fusionnées ensuite)
    out_b = []
    for x in raw:
        prev = out_b[-1] if out_b else 0
        b = int(round(x))
        p4 = prev + int(round((x - prev) / PHRASE)) * PHRASE
        if p4 != b and p4 > prev and abs(p4 - x) <= 1.0:
            b = p4
        out_b.append(max(b, prev + 1))
    starts = [0] + out_b
    res = []
    for i, s in enumerate(segs):
        st = starts[i]
        en = starts[i + 1] if i + 1 < len(starts) else n_bars
        st, en = max(0, min(st, n_bars)), max(0, min(en, n_bars))
        if en <= st:
            continue
        res.append({"start_bar": st, "end_bar": en, "label": s["label"]})
    if not res:
        return []
    res[0]["start_bar"] = 0
    res[-1]["end_bar"] = n_bars
    # silence au milieu : gardé (« Break ») seulement s'il dure au moins 2 mesures
    return _merge(res)


def _merge(res: list[dict]) -> list[dict]:
    changed = True
    while changed and len(res) > 1:
        changed = False
        # 1. segments trop courts -> voisin (même type de préférence, sinon le précédent)
        for i, s in enumerate(res):
            if s["end_bar"] - s["start_bar"] >= MIN_BARS:
                continue
            if i == 0:
                j = 1
            elif i == len(res) - 1:
                j = i - 1
            else:
                prev, nxt = res[i - 1], res[i + 1]
                j = i + 1 if (nxt["label"] == s["label"] and prev["label"] != s["label"]) else i - 1
            a, b = sorted((i, j))
            keep = res[j]["label"]
            res[a:b + 1] = [{"start_bar": res[a]["start_bar"], "end_bar": res[b]["end_bar"], "label": keep}]
            changed = True
            break
        if changed:
            continue
        # 2. deux segments consécutifs du même type, courts au total : une seule section
        for i in range(len(res) - 1):
            a, b = res[i], res[i + 1]
            short = min(a["end_bar"] - a["start_bar"], b["end_bar"] - b["start_bar"]) < MERGE_SAME_MIN
            if a["label"] == b["label"] and short and b["end_bar"] - a["start_bar"] <= MERGE_SAME_MAX:
                res[i:i + 2] = [{"start_bar": a["start_bar"], "end_bar": b["end_bar"], "label": a["label"]}]
                changed = True
                break
    return res


def _is_solo(seg: dict, solo_ctx: dict | None) -> bool:
    """« inst » -> Solo : guitare (lead de préférence) nettement au-dessus de son niveau habituel et
    voix faible sur la section. solo_ctx : {"guitar_db": [dB par mesure], "lead": bool,
    "vocal": [0..1 par mesure]}."""
    if not solo_ctx or not solo_ctx.get("guitar_db"):
        return False
    g = solo_ctx["guitar_db"]
    a, b = seg["start_bar"], min(seg["end_bar"], len(g))
    if b <= a:
        return False
    act = sorted(v for v in g if v > -60)
    if not act:
        return False
    ref = act[len(act) // 2]
    mean_g = sum(g[a:b]) / (b - a)
    voc = solo_ctx.get("vocal") or []
    vv = [voc[i] for i in range(a, min(b, len(voc)))]
    mean_v = (sum(vv) / len(vv)) if vv else 0.0
    need = 6.0 if solo_ctx.get("lead") else 3.0
    return mean_g - ref >= need and mean_v < 0.3


def name_sections(snapped: list[dict], solo_ctx: dict | None = None) -> list[dict]:
    """Noms (clés FR internes, traduits ensuite) + numérotation + lettres de groupe.
    Renvoie [{start_bar (1-based, comme set_sections), name, label}]."""
    bases = []
    for s in snapped:
        base = LABEL_BASE.get(s["label"], "Section")
        if base == "Instrumental" and _is_solo(s, solo_ctx):
            base = "Solo"
        bases.append(base)
    totals = {b: bases.count(b) for b in set(bases)}
    seen, letters, out = {}, {}, []
    for s, base in zip(snapped, bases):
        seen[base] = seen.get(base, 0) + 1
        numbered = base in ALWAYS_NUMBERED or (totals[base] > 1 and base not in NEVER_NUMBERED)
        name = f"{base} {seen[base]}" if numbered else base
        if base not in letters:
            letters[base] = chr(ord("A") + len(letters)) if len(letters) < 26 else "?"
        out.append({"start_bar": s["start_bar"] + 1, "name": name, "label": letters[base]})
    return out


def sections_from_segments(segments: list[dict], downbeats: list[float], solo_ctx: dict | None = None) -> list[dict]:
    return name_sections(snap_segments(segments, downbeats), solo_ctx)


DOUBT_MOVED = 0.75               # frontière de SongFormer à >= 3/4 de mesure de la mesure retenue
DOUBT_UNSURE = 0.3               # entre 0,3 et 0,75 mesure : frontière entre deux mesures


def doubts(segments: list[dict], downbeats: list[float], sections: list[dict]) -> list[dict]:
    """Sections dont le début est douteux (affichées en orange dans la fenêtre) :
    « moved » = frontière déplacée par le calage (carrure, fusion), « unsure » = entre deux mesures.
    sections : sortie de sections_from_segments (start_bar 1-based). Renvoie [{start_bar, reason, off}]."""
    raw = [_bar_pos(float(s["start"]), downbeats) for s in segments
           if _norm_label(s.get("label")) not in ("silence", "start", "end") or float(s["start"]) > downbeats[0]]
    out = []
    for sec in sections[1:]:
        b = int(sec["start_bar"]) - 1
        if not raw:
            break
        off = min(raw, key=lambda x: abs(x - b)) - b
        reason = "moved" if abs(off) >= DOUBT_MOVED else "unsure" if abs(off) >= DOUBT_UNSURE else None
        if reason:
            out.append({"start_bar": int(sec["start_bar"]), "reason": reason, "off": round(off, 2)})
    return out


# --------------------------------------------------------------------------- #
# Lancement de SongFormer (sous-processus) avec cache
# --------------------------------------------------------------------------- #
def _safe(name: str) -> str:
    return re.sub(r"[^\w\-. ]+", "_", str(name)).strip(" .") or "song"


def cache_key(files: list[str], window: str = "auto") -> str:
    h = hashlib.sha1()
    h.update(f"{ENGINE}:{SONGFORMER_REV}:{CACHE_VERSION}:{window}".encode())
    for f in sorted(str(x) for x in files):
        p = Path(f)
        try:
            st = p.stat()
            h.update(f"{p.resolve()}|{st.st_size}|{int(st.st_mtime)}".encode())
        except OSError:
            h.update(f"{f}|missing".encode())
    return h.hexdigest()


def cache_path(ref_file: str, title: str) -> Path:
    return Path(ref_file).parent / ".reacue" / f"{_safe(title)}_structure.json"


def read_cache(path: Path, key: str) -> dict | None:
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(d, dict) and d.get("key") == key and isinstance(d.get("segments"), list):
        return d
    return None


def _progress(msg: str):
    if PROGRESS:
        try:
            PROGRESS(msg)
        except Exception:
            pass


def run_engine(audio: str, out_json: Path, install_dir: Path | None = None, timeout: float = TIMEOUT_S,
               window: str = "auto", python: str | None = None, script: str | None = None) -> dict:
    """Lance reacue_structure.py analyze ; renvoie le résultat (dict) ou lève RuntimeError."""
    from .i18n import t
    d = Path(install_dir or ROOT)
    py = python or str(structure_python(d))
    sc = script or str(d / "reacue_structure.py")
    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    status = out_json.with_name(out_json.stem + "_status.json")
    for p in (out_json, status):
        try:
            p.unlink()
        except OSError:
            pass
    cmd = [py, sc, "analyze", "--input", str(audio), "--out", str(out_json), "--status", str(status),
           "--window", str(window)]
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = 0x08000000          # CREATE_NO_WINDOW
    t0 = time.time()
    log = out_json.with_name(out_json.stem + ".log")
    with open(log, "w", encoding="utf-8") as lf:
        proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=str(d), **kw)
        last = 0.0
        while proc.poll() is None:
            el = time.time() - t0
            if el > timeout:
                proc.kill()
                raise RuntimeError(t("structure_timeout", min=int(timeout // 60)))
            if el - last >= 5:
                last = el
                step = ""
                try:
                    step = json.loads(status.read_text(encoding="utf-8")).get("step") or ""
                except (OSError, ValueError):
                    pass
                _progress(t("structure_running", s=int(el)) + (f" · {step}" if step else ""))
            time.sleep(0.5)
    try:
        res = json.loads(out_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        res = None
    if proc.returncode != 0 or not isinstance(res, dict) or not isinstance(res.get("segments"), list):
        msg = ""
        try:
            msg = json.loads(status.read_text(encoding="utf-8")).get("message") or ""
        except (OSError, ValueError):
            pass
        raise RuntimeError(msg or f"exit {proc.returncode} ({log})")
    return res


def _write_mix(stems: list[dict], wav: Path, sr: int = 22050) -> Path:
    """Somme des stems (calés comme pour l'analyse : temps du stem de référence) -> WAV mono."""
    import numpy as np
    import librosa
    import soundfile as sf
    ys, shifts = [], []
    for s in stems:
        y, _ = librosa.load(str(s["file"]), sr=sr, mono=True)
        ys.append(y)
        shifts.append(float(s.get("shift", 0.0) or 0.0))
    base = shifts[0] if shifts else 0.0
    ref_len = max((len(y) + max(0, int(round((sh - base) * sr))) for y, sh in zip(ys, shifts)), default=0)
    mix = np.zeros(ref_len, dtype=np.float32)
    for y, sh in zip(ys, shifts):
        off = int(round((sh - base) * sr))
        if off >= 0:
            seg = y[: max(0, ref_len - off)]
            mix[off:off + len(seg)] += seg
        else:
            seg = y[-off:][:ref_len]
            mix[:len(seg)] += seg
    peak = float(np.abs(mix).max()) or 1.0
    wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(wav), (mix / peak * 0.9).astype(np.float32), sr, subtype="PCM_16")
    return wav


def _solo_context(a, stems: list[dict] | None) -> dict | None:
    """Niveau de la guitare par mesure (lead si présente) + activité de la voix, pour « inst » -> Solo."""
    if not stems:
        return None
    try:
        from .analysis import assign_roles, _bar_db, SR
        import librosa
        files = [str(s["file"]) for s in stems]
        roles = assign_roles(files)
        pick = None
        for want in ("lead_guitar", "guitars"):
            if want in roles:
                pick = roles.index(want)
                break
        if pick is None:
            return None
        ref_shift = float(stems[0].get("shift", 0.0) or 0.0)
        y, _ = librosa.load(files[pick], sr=SR, mono=True)
        off = int(round((float(stems[pick].get("shift", 0.0) or 0.0) - ref_shift) * SR))
        if off > 0:
            import numpy as np
            y = np.concatenate([np.zeros(off, dtype=y.dtype), y])
        elif off < 0:
            y = y[-off:]
        g = [float(v) for v in _bar_db(y, SR, a.downbeats)]
        return {"guitar_db": g, "lead": roles[pick] == "lead_guitar", "vocal": list(a.vocal_activity or [])}
    except Exception:
        return None


def apply_engine(a, stems: list[dict] | None = None, title: str | None = None,
                 install_dir: Path | None = None, engine: str | None = None) -> tuple[object, dict]:
    """Remplace les sections de l'Analysis `a` par celles de SongFormer (calées sur sa grille).

    stems : [{"file", "shift"}] (mode stems, temps du stem de référence = stems[0] après tri par
    l'appelant) ou None (fichier unique a.file). Renvoie (analyse, info) ; info = {"engine": "songformer"
    | "reacue", "cached": bool, "seconds": …} ; en cas d'échec, l'analyse est inchangée et un
    avertissement est ajouté à a.warnings."""
    from .i18n import t
    from .analysis import resection
    engine = engine or engine_setting()
    info = {"engine": "reacue"}
    if engine != "auto":
        return a, info
    if not available(install_dir):
        info["missing"] = True               # la fenêtre propose « Installer » (pastille Structure)
        return a, info
    files = [str(s["file"]) for s in stems] if stems else [a.file]
    ref = files[0] if not stems else str(stems[0]["file"])
    title = title or Path(a.file).stem
    key = cache_key(files)
    cpath = cache_path(ref, title)
    res = read_cache(cpath, key)
    cached = res is not None
    try:
        if res is None:
            _progress(t("structure_running", s=0))
            t0 = time.time()
            with tempfile.TemporaryDirectory(prefix="reacue_structure_") as tmp:
                audio = a.file
                if stems and len(stems) > 1:
                    audio = str(_write_mix(stems, Path(tmp) / "mix.wav"))
                out = run_engine(audio, Path(tmp) / "result.json", install_dir)
            res = {"key": key, "engine": ENGINE, "rev": SONGFORMER_REV, "segments": out["segments"],
                   "window_s": out.get("window_s"), "seconds": out.get("seconds", round(time.time() - t0))}
            try:
                cpath.parent.mkdir(parents=True, exist_ok=True)
                cpath.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
            except OSError:
                pass
        secs = sections_from_segments(res["segments"], a.downbeats, _solo_context(a, stems))
        if not secs:
            raise RuntimeError(t("structure_empty"))
        a = resection(a, secs)
        info = {"engine": ENGINE, "cached": cached, "seconds": res.get("seconds"), "window_s": res.get("window_s"),
                "message": t("structure_used_cached" if cached else "structure_used", s=res.get("seconds") or 0),
                "doubts": doubts(res["segments"], a.downbeats, secs)}
    except Exception as e:                      # noqa: BLE001 - la détection de ReaCue prend le relais
        a.warnings.append(t("structure_failed", e=e))
        info = {"engine": "reacue", "error": str(e), "fallback": True}
    return a, info
