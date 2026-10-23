"""Prompteur des musiciens : données du morceau pour la page web servie par REAPER.

Après chaque construction (prepare_song, set_sections…), le serveur écrit dans
<ressources REAPER>/reaper_www_root/ :
  - prompteur.html       : la page (une seule, chaque musicien choisit son rôle) ;
  - reacue_song.json     : le morceau (mesures sur la timeline, sections, présence des instruments).
La page lit la position de lecture via l'interface web de REAPER (/_/TRANSPORT) : pendant le
live, seul REAPER doit tourner.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import numpy as np

from .analysis import Analysis, reference_index
from .bridge import BRIDGE_DIR
from .i18n import section_color, section_kind, get_lang

WWW_DIR = BRIDGE_DIR.parent / "reaper_www_root"
PAGE_SRC = Path(__file__).parent / "web" / "prompteur.html"
PAGE_NAME = "prompteur.html"
SONG_NAME = "reacue_song.json"
CACHE = BRIDGE_DIR / "prompter_activity.json"

NOTE_FR = {"C": "Do", "D": "Ré", "E": "Mi", "F": "Fa", "G": "Sol", "A": "La", "B": "Si"}


# --------------------------------------------------------------------------- #
# Tonalité lue dans le nom des fichiers (« …-E minor-188bpm… »)
# --------------------------------------------------------------------------- #
def key_from_names(names: list[str]) -> dict | None:
    for n in names:
        m = re.search(r"(?<![A-Za-z])([A-G])\s?(#|b|♯|♭)?\s?(major|minor|maj|min|majeur|mineur)(?![a-z])",
                      Path(str(n)).name, re.I)
        if m:
            root, acc, mode = m.group(1).upper(), m.group(2) or "", m.group(3).lower()
            minor = mode.startswith("min")
            acc_s = "#" if acc in ("#", "♯") else ("b" if acc in ("b", "♭") else "")
            fr_acc = {"#": " dièse", "b": " bémol"}.get(acc_s, "")
            en_acc = {"#": "♯", "b": "♭"}.get(acc_s, "")
            return {"chord": f"{root}{acc_s}{'m' if minor else ''}",
                    "fr": f"{NOTE_FR[root]}{fr_acc} {'mineur' if minor else 'majeur'}",
                    "en": f"{root}{en_acc} {'minor' if minor else 'major'}"}
    return None


# --------------------------------------------------------------------------- #
# Présence de chaque instrument par mesure (à partir des stems)
# --------------------------------------------------------------------------- #
def _shifts(items: list[dict]) -> dict[str, float]:
    """Décalage de chaque fichier par rapport au stem de référence (même calcul que prepare_song)."""
    files = [d["file"] for d in items]
    ref = items[reference_index(files)]

    def t0(d):
        return float(d["position"]) - float(d.get("offset", 0.0)) / float(d.get("rate") or 1.0)
    return {d["file"]: t0(d) - t0(ref) for d in items}


def stem_activity(a: Analysis, items: list[dict] | None, min_share: float = 0.2,
                  cache: Path | None = None) -> dict[str, list[int]]:
    """{rôle: [1 si l'instrument joue dans la mesure, sinon 0]} ; vide sans stems.
    Seuil relatif au niveau actif du stem (p90 − 20 dB) : la repisse est ignorée.
    cache : fichier de cache (défaut : un seul morceau mémorisé dans ReaCueMCP ; mode concert : un par morceau)."""
    cache = Path(cache) if cache else CACHE
    if not items or len(items) < 2:
        return {}
    import librosa
    from .analysis import SR, HOP, _place, _frame_db, _bar_agg, assign_roles

    shifts = _shifts(items)
    files = [d["file"] for d in items]
    key = hashlib.md5(json.dumps([files, [round(shifts[f], 4) for f in files],
                                  a.downbeats[:1], a.downbeats[-1:], len(a.downbeats)]).encode()).hexdigest()
    try:
        c = json.loads(cache.read_text(encoding="utf-8"))
        if c.get("key") == key:
            return c["activity"]
    except Exception:
        pass
    roles = assign_roles(files)
    out = {}
    for role, f in zip(roles, files):
        y = librosa.load(f, sr=SR, mono=True)[0]
        n = len(y) + max(0, int(round(shifts[f] * SR))) + SR
        y = _place(y, shifts[f], SR, n)
        d = _frame_db(y)
        if d.max() < -80:
            out[role] = [0] * (len(a.downbeats) - 1)
            continue
        act = (d > np.percentile(d, 90) - 20.0).astype(float)
        frames = librosa.time_to_frames(np.array(a.downbeats), sr=SR, hop_length=HOP)
        share = _bar_agg(act, frames, len(act))
        out[role] = [int(s >= min_share) for s in share]
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"key": key, "activity": out}), encoding="utf-8")
    except OSError:
        pass
    return out


# --------------------------------------------------------------------------- #
# Données du morceau
# --------------------------------------------------------------------------- #
def section_type(name: str) -> str:
    """Type de section pour la page (indépendant de la langue) : intro, verse, prechorus, chorus,
    bridge, solo, break, outro, interlude, riff, other."""
    return section_kind(name)


def _timeline_time(timeline: dict, bpb: int, bar: int, pos: float) -> float:
    """Mesure (1-based) + position en temps -> secondes sur la timeline REAPER (bar_times)."""
    bt = timeline["bar_times"]
    ci = int(timeline.get("count_in_bars", 0))
    idx = bar - 1 + ci
    if len(bt) < 2:
        return float(bt[0]) if bt else 0.0
    k = min(max(idx, 0), len(bt) - 2)
    L = bt[k + 1] - bt[k]
    return round(float(bt[k] + L * ((idx - k) + pos / max(1, bpb))), 4)


def _file_bar_pos(downbeats, bpb: int, t: float) -> tuple[int, float]:
    """Temps du fichier de référence -> (mesure 1-based, position en temps), comme lyrics._bar_pos."""
    db = np.asarray(downbeats, dtype=float)
    m = max(1, int(bpb))
    if t < db[0]:
        L = db[1] - db[0]
        k = int(np.floor((t - db[0]) / L))
        pos = (t - (db[0] + k * L)) / L * m
    else:
        k = int(min(len(db) - 2, np.searchsorted(db, t, "right") - 1))
        pos = (t - db[k]) / (db[k + 1] - db[k]) * m
    return k + 1, max(0.0, float(pos))


def _words_on_timeline(o: dict, t0: float, t1: float, timeline: dict, bpb: int, downbeats) -> list[dict]:
    """Mots d'une ligne (temps du fichier) -> temps de la timeline : par la grille (downbeats) si elle est
    connue, sinon proportionnellement entre le début et la fin de la ligne. Bornés à la ligne, croissants."""
    ws = o.get("words") or []
    ft0, ft1 = float(o.get("t", 0.0)), float(o.get("end", 0.0))
    use_grid = downbeats is not None and len(downbeats) >= 2

    def conv(x):
        if use_grid:
            return _timeline_time(timeline, bpb, *_file_bar_pos(downbeats, bpb, float(x)))
        if ft1 - ft0 <= 1e-6:
            return t0
        return t0 + (float(x) - ft0) * (t1 - t0) / (ft1 - ft0)
    out, last = [], t0
    for w in ws:
        if not isinstance(w, dict) or "t" not in w:
            return []
        a = max(last, min(conv(w["t"]), t1))
        b = max(a, min(conv(w.get("end", w["t"])), t1))
        out.append({"w": str(w.get("w", "")), "t": round(a, 4), "end": round(b, 4)})
        last = a
    return out


def lyrics_on_timeline(lyrics: list[dict], timeline: dict, bpb: int, n_bars: int, downbeats=None) -> list[dict]:
    """Paroles calées (temps du fichier) -> temps de la timeline REAPER via mesure/temps.
    Mots ("words", facultatifs) : convertis aussi (downbeats = grille du fichier de référence)."""
    out = []
    for o in lyrics or []:
        bar, pos = int(o["bar"]), float(o.get("pos", o.get("beat", 0)))
        if bar > n_bars:
            continue
        eb, ep = int(o.get("end_bar", bar)), float(o.get("end_pos", pos + 1))
        t0 = _timeline_time(timeline, bpb, bar, pos)
        t1 = max(t0 + 0.2, _timeline_time(timeline, bpb, eb, ep))
        e = {"i": o["i"], "line": o.get("line", o["i"] + 1), "bar": bar, "beat": int(o.get("beat", 0)),
             "pos": round(pos, 3), "t": t0, "end": round(t1, 4), "text": o["text"],
             "confidence": o.get("confidence", 0.5), "copy": bool(o.get("copy", False))}
        if o.get("words"):
            ws = _words_on_timeline(o, t0, t1, timeline, bpb, downbeats)
            if ws:
                e["words"] = ws
        out.append(e)
    out.sort(key=lambda x: x["t"])
    return out


def build_song(a: Analysis, item: dict, timeline: dict, items: list[dict] | None = None,
               activity: dict | None = None, chords: list[dict] | None = None,
               lyrics: list[dict] | None = None, drums: dict | None = None) -> dict:
    """timeline : plan['prompter'] (temps de chaque mesure sur la timeline REAPER).
    chords : grille d'accords par mesure (chords.detect_chords), facultative.
    lyrics : paroles calées (lyrics.align_lyrics, temps du fichier), facultatives : converties en
    temps de la timeline par leur position mesure/temps.
    drums : transcription de la batterie (drums.detect_drums), facultative."""
    names = [d["file"] for d in items] if items else [item.get("file", "")]
    voc = list(a.vocal_activity or [])
    act = dict(activity or {})
    if "vocals" not in act and len(voc) == a.n_bars:
        act["vocals"] = [int(v >= 0.15) for v in voc]
    for k, v in act.items():                 # un silence d'une seule mesure = respiration, pas un arrêt
        v = list(v)
        for i in range(1, len(v) - 1):
            if v[i] == 0 and v[i - 1] == 1 and v[i + 1] == 1:
                v[i] = 1
        act[k] = v
    sections = []
    for s in a.sections:
        sections.append({
            "name": s.name, "type": section_type(s.name), "group": s.label,
            "start_bar": s.start_bar + 1, "end_bar": s.end_bar,      # 1-based, fin incluse
            "color": "#%02x%02x%02x" % tuple(section_color(s.name)),
        })
    song = {
        "version": 1,
        "language": get_lang(),
        "title": item.get("title") or Path(item.get("file", "Song")).stem,
        "bpm": timeline["bpm"],
        "beats_per_bar": a.beats_per_bar,
        "tempo_mode": timeline["tempo_mode"],
        "count_in_bars": timeline["count_in_bars"],
        "n_bars": a.n_bars,
        # bar_times[i] = début de la mesure (i - count_in_bars + 1) ; dernière valeur = fin du morceau
        "bar_times": timeline["bar_times"],
        "key": key_from_names(names),
        "sections": sections,
        "activity": {k: v[:a.n_bars] for k, v in act.items()},
        "roles": sorted(act.keys()),
    }
    if chords:
        # une entrée par mesure (1-based) : {"bar", "chords": [{"beat", "chord", "bass", "confidence"}]}
        song["chords"] = [c for c in chords if 1 <= int(c.get("bar", 0)) <= a.n_bars]
    if lyrics:
        # une entrée par ligne chantée : {"i", "line", "bar", "beat", "pos", "t", "end" (timeline), "text", …,
        #  "words" facultatif : [{"w", "t", "end"}] (timeline), si le calage mot par mot est installé}
        song["lyrics"] = lyrics_on_timeline(lyrics, timeline, a.beats_per_bar, a.n_bars,
                                            downbeats=a.downbeats if len(a.downbeats or []) >= 2 else None)
    if drums and drums.get("bars"):
        # {"steps", "lanes", "patterns": {"A": {"name", "hits", "accents"}}, "bars": [{"bar", "pattern", "fill",
        #  "crash", "rest", "hits"}]} : une entrée par mesure (1-based)
        song["drums"] = {**drums, "bars": [e for e in drums["bars"] if 1 <= int(e.get("bar", 0)) <= a.n_bars]}
    song["id"] = hashlib.md5(json.dumps(song, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    return song


def publish(song: dict, www: Path | None = None) -> dict:
    """Écrit la page et les données dans reaper_www_root ; renvoie les chemins."""
    www = Path(www or WWW_DIR)
    www.mkdir(parents=True, exist_ok=True)
    tmp = www / (SONG_NAME + ".tmp")
    tmp.write_text(json.dumps(song, ensure_ascii=False), encoding="utf-8")
    tmp.replace(www / SONG_NAME)                       # écriture atomique : la page ne lit jamais un demi-fichier
    page = www / PAGE_NAME
    if PAGE_SRC.exists() and (not page.exists() or page.read_bytes() != PAGE_SRC.read_bytes()):
        shutil.copyfile(PAGE_SRC, page)
    return {"page": str(page), "data": str(www / SONG_NAME)}
