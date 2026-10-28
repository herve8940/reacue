"""Nouveau morceau / new song : copie un MP3 (ou WAV…) ou des stems dans <dossier des projets>/<Titre>/ et
écrit le projet REAPER <Titre>.RPP (une piste par fichier, à 0 s). Même convention que le bouton
« + Nouveau morceau » de la fenêtre ReaCue (reaper/ReaCue_newsong.lua) : un projet existant n'est jamais
écrasé ; les noms de fichiers d'origine sont gardés (ils portent le rôle, la tonalité et le BPM).
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from .concert import media_dir
from .i18n import get_lang

AUDIO_EXT = {".wav", ".mp3", ".aif", ".aiff", ".flac", ".ogg", ".m4a", ".wv"}

_ROLE_SEG = {
    "vocals", "vocal", "voice", "voix", "chant", "backing vocals", "choeurs", "chœurs",
    "drums", "drum", "batterie", "percussion", "percussions", "bass", "basse",
    "guitar", "guitars", "guitare", "guitares", "lead guitar", "lead guitars", "rhythm guitar", "rhythm guitars",
    "other", "others", "autre", "autres", "piano", "keys", "claviers", "synth",
    "instrumental", "accompaniment", "mix", "click", "metronome",
}
_NOISE = ("official", "officiel", "officielle", "clip", "lyric", "lyrics", "video", "vidéo", "audio",
          "remaster", "remastered", "visualizer", "live", "hd", "4k")
_ROLE_WORDS = [
    ("vocals", ("vocals", "vocal", "voice", "voices", "voix", "chant", "vox", "backing vocals", "choeurs", "chœurs")),
    ("drums", ("drums", "drum", "batterie", "percussion", "percussions", "perc", "kick", "batt")),
    ("bass", ("bass", "basse")),
    ("lead_guitar", ("lead guitar", "lead guitars", "lead gtr", "guitare solo", "solo guitar")),
    ("guitars", ("guitars", "guitar", "guitares", "guitare", "gtr", "rhythm guitar")),
    ("keys", ("piano", "keys", "clavier", "claviers", "synth", "synthesizer", "organ", "orgue")),
    ("other", ("other", "others", "autre", "autres")),
]
_ROLE_NAMES = {
    "fr": {"vocals": "Chant", "drums": "Batterie", "bass": "Basse", "lead_guitar": "Guitare solo",
           "guitars": "Guitares", "keys": "Claviers", "other": "Autres"},
    "en": {"vocals": "Vocals", "drums": "Drums", "bass": "Bass", "lead_guitar": "Lead guitar",
           "guitars": "Guitars", "keys": "Keys", "other": "Other"},
}


def _trim(s: str) -> str:
    return re.sub(r"^[\s\-_.]+|[\s\-_.]+$", "", s)


def _cut(seg: str) -> bool:
    s = _trim(seg).lower()
    if not s:
        return False
    if s in _ROLE_SEG or s.endswith("consolidated"):
        return True
    return bool(re.fullmatch(r"[a-g][#b]?\s*(major|minor|maj|min|m)", s)
                or re.fullmatch(r"\d+[.,]?\d*\s*bpm", s) or re.fullmatch(r"\d+\s*k?hz", s))


def clean_title(name: str) -> str:
    """« Luke - La sentinelle _Clip officiel_-Bass-E minor-188bpm-441hz.wav » → « Luke - La sentinelle »."""
    base = re.sub(r"\.\w+$", "", Path(str(name)).name)
    parts = base.split("-")
    keep = []
    for i, p in enumerate(parts):
        if i > 0 and _cut(p):
            break
        keep.append(p)
    s = "-".join(keep)

    def noisy(m):
        return "" if any(w in m.group(0).lower() for w in _NOISE) else m.group(0)
    s = re.sub(r"\s*\([^()]*\)", noisy, s)
    s = re.sub(r"\s*\[[^\[\]]*\]", noisy, s)
    s = re.sub(r"\s*_[^_]+_", noisy, s)
    s = re.sub(r"\s+", " ", s.replace("_", " "))
    s = _trim(s)
    return s or _trim(base)


def safe_name(title: str) -> str:
    s = _trim(re.sub(r"\s+", " ", re.sub(r'[\\/:*?"<>|]+', "-", str(title))))
    return s or "Song"


def stems_title(folder: Path, files: list[Path]) -> str:
    cand = clean_title(folder.name + ".x")
    if cand and cand.lower() not in _ROLE_SEG and cand.lower() != "stems":
        return cand
    return clean_title(files[0].name) if files else "Song"


def role_of(file: str | Path) -> str | None:
    base = re.sub(r"\.\w+$", "", Path(str(file)).name).lower()
    norm = re.sub(r"[^a-zA-Z0-9\u00C0-\u017F]+", " ", base).strip()
    for role, words in _ROLE_WORDS:
        for w in words:
            if re.search(rf"\b{re.escape(w)}\b", norm, re.IGNORECASE):
                return role
    return None


def track_name(file: Path, single: bool, lang: str | None = None) -> str:
    r = role_of(file)
    if r and not single:
        return _ROLE_NAMES.get(lang or get_lang(), _ROLE_NAMES["fr"])[r]
    base = re.sub(r"\.\w+$", "", file.name)
    return clean_title(base) if single else base


def existing(title: str, root: Path | None = None) -> Path | None:
    root = Path(root or media_dir())
    s = safe_name(title)
    for p in (root / s, root / f"{s}.RPP", root / f"{s}.rpp"):
        if p.exists():
            return p
    return None


def _duration(p: Path) -> float:
    try:
        import soundfile as sf
        return float(sf.info(str(p)).duration)
    except Exception:
        try:
            import librosa
            return float(librosa.get_duration(path=str(p)))
        except Exception:
            return 0.0


_SRC = {".mp3": "MP3", ".flac": "FLAC", ".ogg": "VORBIS"}


def _q(s: str) -> str:
    s = str(s)
    if '"' not in s:
        return f'"{s}"'
    if "'" not in s:
        return f"'{s}'"
    return f"`{s}`"


def write_rpp(rpp: Path, files: list[Path], single: bool, lang: str | None = None):
    lines = ['<REAPER_PROJECT 0.1 "7.0" 0', "  RIPPLE 0", "  TEMPO 120 4 4"]
    for f in files:
        dur = _duration(f)
        lines += ["  <TRACK", f"    NAME {_q(track_name(f, single, lang))}", "    <ITEM", "      POSITION 0",
                  f"      LENGTH {dur:.6f}", f"      NAME {_q(f.name)}",
                  f"      <SOURCE {_SRC.get(f.suffix.lower(), 'WAVE')}", f"        FILE {_q(str(f))}",
                  "      >", "    >", "  >"]
    lines.append(">")
    tmp = rpp.with_suffix(".rpp-tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(rpp)


def new_song(files: list[str], title: str | None = None, root: Path | None = None,
             lang: str | None = None) -> dict:
    """files : un fichier audio, plusieurs stems, ou un dossier de stems. Renvoie le projet créé."""
    paths = [Path(str(f)).expanduser() for f in files]
    if len(paths) == 1 and paths[0].is_dir():
        folder = paths[0]
        paths = sorted((p for p in folder.iterdir() if p.suffix.lower() in AUDIO_EXT and not p.name.startswith(".")),
                       key=lambda p: p.name.lower())
        if not paths:
            raise FileNotFoundError(f"no audio file in {folder}")
        single = False
        proposal = stems_title(folder, paths)
    else:
        for p in paths:
            if not p.is_file():
                raise FileNotFoundError(str(p))
            if p.suffix.lower() not in AUDIO_EXT:
                raise ValueError(f"not an audio file: {p}")
        single = len(paths) == 1
        proposal = clean_title(paths[0].name) if single else stems_title(paths[0].parent, paths)
    title = (title or proposal).strip()
    root = Path(root or media_dir())
    ex = existing(title, root)
    if ex:
        raise ValueError(f"a song “{title}” already exists: {ex}")
    dst = root / safe_name(title)
    dst.mkdir(parents=True, exist_ok=False)
    copied = []
    for p in paths:
        q = dst / p.name
        shutil.copyfile(p, q)
        if q.stat().st_size != p.stat().st_size:
            raise OSError(f"incomplete copy: {q}")
        copied.append(q)
    rpp = dst / f"{safe_name(title)}.RPP"
    write_rpp(rpp, copied, single, lang)
    return {"title": title, "project": str(rpp), "folder": str(dst), "files": [c.name for c in copied],
            "single_file": single,
            "next": "separate stems, then prepare" if single else "prepare"}
