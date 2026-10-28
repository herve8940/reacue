"""Bibliothèque des morceaux (écran BIBLIO de ReaCue Studio) et état durable de ReaCue.

Deux fichiers dans <ressources REAPER>/ReaCueMCP/ :
  - reacue_state.json      : état durable, écrit par la fenêtre ReaCue (Lua) et lu ici :
        {"version": 1, "songs": {"<clé>": {"title", "stage" (étape réglée à la main, absent = auto),
          "notes": {"<mesure de début de section>": "texte"}, "solo_s", "band_s",
          "days": {"AAAA-MM-JJ": secondes jouées en groupe}, "last"}}}
    clé = chemin du projet .RPP en minuscules avec des « / » (song_key, même calcul côté Lua) ;
  - library_cache.json     : cache Python (résumé des morceaux publiés, lecture des .RPP par date).

Et dans reaper_www_root/ : reacue_library.json, lu par la page (publish_library), mis à jour à chaque
publication du prompteur, à chaque construction de concert et à l'ouverture de la fenêtre ReaCue
(commande « library » de la CLI).

Étape du parcours (calcul automatique, remplaçable à la main dans la page) :
  new    Découvert            : rien de mesuré ;
  solo   Travaillé seul       : ≥ 5 min de lecture sans autre musicien connecté ;
  band   Répété en groupe     : ≥ 3 min de lecture avec au moins 2 prompteurs de musiciens connectés ;
  stage  Prêt pour la scène   : morceau préparé (régions + click) et répété en groupe sur 2 jours différents
                                (au moins 2 min de groupe chaque jour).
Le temps de lecture est compté par la fenêtre ReaCue (ReaCue_concert_lib.lua, L.practice_tick).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

from .bridge import BRIDGE_DIR

LIBRARY_NAME = "reacue_library.json"
STATE_NAME = "reacue_state.json"
CACHE_NAME = "library_cache.json"
STAGES = ("new", "solo", "band", "stage")
SOLO_S = 300            # Travaillé seul : 5 min de lecture
BAND_S = 180            # Répété en groupe : 3 min avec au moins 2 musiciens connectés
BAND_DAY_S = 120        # une journée de répétition compte à partir de 2 min de groupe
STAGE_DAYS = 2          # Prêt pour la scène : répété en groupe sur 2 jours différents
MAX_NOTE = 200          # caractères par note de section
SKIP_DIRS = {"concerts", "backups", "media", "peaks"}


# --------------------------------------------------------------------------- clés, état durable
def song_key(path) -> str:
    """Clé d'un morceau : chemin du .RPP, « / » et minuscules (même règle que L.song_key en Lua)."""
    return str(path or "").replace("\\", "/").lower()


def state_path() -> Path:
    return BRIDGE_DIR / STATE_NAME


def load_state(path: Path | None = None) -> dict:
    """État durable (écrit par la fenêtre ReaCue) ; absent ou illisible : vide."""
    try:
        d = json.loads(Path(path or state_path()).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    songs = d.get("songs")
    d["songs"] = songs if isinstance(songs, dict) else {}
    return d


def song_state(state: dict, path) -> dict:
    rec = (state.get("songs") or {}).get(song_key(path))
    return rec if isinstance(rec, dict) else {}


def notes_for(path, state: dict | None = None) -> dict[str, str]:
    """Notes de section d'un projet : {"<mesure de début>": "texte"} (vide si aucune)."""
    if not path:
        return {}
    rec = song_state(state if state is not None else load_state(), path)
    notes = rec.get("notes")
    if not isinstance(notes, dict):
        return {}
    return {str(k): str(v or "")[:MAX_NOTE] for k, v in notes.items()}


def rehash(d: dict) -> dict:
    """Identifiant des données publiées recalculé (les pages rechargent quand il change)."""
    d.pop("id", None)
    d["id"] = hashlib.md5(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    return d


def attach(song: dict, project, state: dict | None = None, recompute: bool = True) -> dict:
    """Ajoute au morceau publié le chemin de son projet (« project ») et ses notes de section (« notes »)."""
    if project:
        song["project"] = str(project)
    notes = notes_for(project, state)
    for s in song.get("sections") or []:
        k = str(s.get("start_bar"))
        if k in notes:
            s["notes"] = notes[k]
        else:
            s.setdefault("notes", "")
    if recompute:
        rehash(song)
    return song


# --------------------------------------------------------------------------- étapes
def band_days(rec: dict) -> int:
    days = rec.get("days")
    if not isinstance(days, dict):
        return 0
    return sum(1 for v in days.values() if isinstance(v, (int, float)) and v >= BAND_DAY_S)


def auto_stage(rec: dict, prepared: bool) -> str:
    """Étape calculée à partir du temps de lecture compté par la fenêtre ReaCue."""
    solo = float(rec.get("solo_s") or 0)
    band = float(rec.get("band_s") or 0)
    if prepared and band_days(rec) >= STAGE_DAYS:
        return "stage"
    if band >= BAND_S:
        return "band"
    if solo >= SOLO_S:
        return "solo"
    return "new"


def stage_of(rec: dict, prepared: bool) -> tuple[str, str, str | None]:
    """(étape affichée, étape automatique, étape manuelle ou None)."""
    auto = auto_stage(rec, prepared)
    manual = rec.get("stage") if rec.get("stage") in STAGES else None
    return manual or auto, auto, manual


# --------------------------------------------------------------------------- cache Python
def _cache_path() -> Path:
    return BRIDGE_DIR / CACHE_NAME


def _load_cache() -> dict:
    try:
        d = json.loads(_cache_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    for k in ("published", "rpp"):
        if not isinstance(d.get(k), dict):
            d[k] = {}
    return d


def _save_cache(c: dict):
    try:
        p = _cache_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        pass


def summary_from_song(song: dict) -> dict:
    """Résumé d'un morceau publié (prompteur) pour la bibliothèque."""
    bt = song.get("bar_times") or []
    ci = int(song.get("count_in_bars") or 0)
    dur = (bt[-1] - bt[min(ci, len(bt) - 1)]) if len(bt) > 1 else 0.0
    roles = [r for r in song.get("roles") or [] if r != "mix"]
    return {
        "title": song.get("title") or "",
        "bpm": song.get("bpm"),
        "sig": f"{song.get('beats_per_bar') or 4}/4",
        "key_name": song.get("key"),
        "duration_s": round(float(dur), 1),
        "bars": int(song.get("n_bars") or 0),
        "sections": [{"name": s.get("name", ""), "type": s.get("type", "other"), "color": s.get("color", "#4A5361"),
                      "bars": int(s.get("end_bar", 0)) - int(s.get("start_bar", 0)) + 1}
                     for s in song.get("sections") or []],
        "components": {"stems": len(roles) if len(roles) >= 2 else 0, "chords": bool(song.get("chords")),
                       "lyrics": len(song.get("lyrics") or []), "drums": bool(song.get("drums")),
                       "lighting": bool(song.get("lighting"))},
    }


def record_song(song: dict, project, lighting: bool | None = None) -> None:
    """Mémorise le résumé d'un morceau publié (morceau seul ou morceau d'un concert). Jamais bloquant."""
    if not project:
        return
    try:
        c = _load_cache()
        s = summary_from_song(song)
        if lighting is not None:
            s["components"]["lighting"] = bool(lighting) or s["components"]["lighting"]
        s["t"] = int(time.time())
        s["path"] = str(project)
        c["published"][song_key(project)] = s
        _save_cache(c)
    except Exception:
        pass


# --------------------------------------------------------------------------- lecture des projets
def _hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(int(x) for x in rgb)


def _extras_cache(path: Path, audio: list[dict]) -> dict:
    """Composants déjà calculés pour un morceau jamais publié seul : caches du mode concert (.reacue/)."""
    from .concert import _norm
    out = {"chords": False, "lyrics": 0, "drums": False}
    slug = re.sub(r"[^A-Za-z0-9]+", "_", _norm(path.stem)) or "song"
    dirs = {Path(d["file"]).parent for d in audio if d.get("file")} | {path.parent}
    for d in dirs:
        base = d / ".reacue"
        for kind in ("chords", "lyrics", "drums"):
            f = base / f"{slug}_{kind}.json"
            try:
                v = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            body = v.get(kind) if isinstance(v, dict) else v
            if kind == "lyrics":
                out["lyrics"] = max(out["lyrics"], len(body or []) if isinstance(body, list) else int(bool(body)))
            else:
                out[kind] = out[kind] or bool(body)
    return out


def info_from_rpp(path: Path) -> dict:
    """Titre, tempo, durée, structure et composants lus dans le .RPP (rien n'est analysé)."""
    from . import concert as C
    from .i18n import section_color, section_kind
    from .prompter import key_from_names
    s = C.load_song(path)
    secs = []
    for x in s.sections:
        secs.append({"name": x.name, "type": section_kind(x.name), "color": _hex(section_color(x.name)),
                     "bars": int(x.end_bar - x.start_bar)})
    roles = {d["role"] for d in s.audio}
    n_audio = len(s.audio)
    comps = {"stems": len(roles - {"mix"}) if n_audio > 1 else 0, "lighting": (path.parent / "grandMA3").is_dir()}
    comps.update(_extras_cache(path, s.audio))
    return {
        "title": s.title, "bpm": round(s.bpm, 2), "sig": f"{s.beats_per_bar}/{s.denominator}",
        "key_name": key_from_names([d["file"] for d in s.audio]),
        "duration_s": round(max(0.0, s.song_end - s.bar1), 1), "bars": int(s.n_bars),
        "sections": secs if s.regions else [],
        "prepared": bool(s.regions) and "CLICK" in s.gen,
        "components": comps,
    }


def _rpp_info(path: Path, cache: dict) -> dict | None:
    key = song_key(path)
    try:
        st = path.stat()
    except OSError:
        return None
    sig = [int(st.st_mtime), st.st_size]
    hit = cache["rpp"].get(key)
    if isinstance(hit, dict) and hit.get("sig") == sig and isinstance(hit.get("info"), dict):
        return hit["info"]
    try:
        info = info_from_rpp(path)
    except Exception:
        info = {"title": path.stem, "bpm": None, "sig": "4/4", "key_name": None, "duration_s": 0, "bars": 0,
                "sections": [], "prepared": False,
                "components": {"stems": 0, "chords": False, "lyrics": 0, "drums": False, "lighting": False},
                "unreadable": True}
    cache["rpp"][key] = {"sig": sig, "info": info}
    return info


def scan_projects(root: Path | None = None, cdir: Path | None = None) -> list[Path]:
    """Projets des morceaux : dossier des projets et ses sous-dossiers directs (comme l'onglet Concert de la
    fenêtre ReaCue) ; sans le dossier des concerts, les sauvegardes et les dossiers de stems."""
    from . import concert as C
    root = Path(root or C.media_dir())
    cdir = Path(cdir or C.concert_dir())
    out = []

    def add(d: Path):
        try:
            files = sorted(d.iterdir())
        except OSError:
            return
        for f in files:
            low = f.name.lower()
            if f.is_file() and low.endswith(".rpp") and not low.endswith("-bak.rpp") and "backup" not in low:
                out.append(f)
    add(root)
    try:
        subs = sorted(x for x in root.iterdir() if x.is_dir())
    except OSError:
        subs = []
    for d in subs:
        if d.name.lower() in SKIP_DIRS or d.name.endswith("-stems") or d.name.startswith("."):
            continue
        try:
            if d.resolve() == cdir.resolve():
                continue
        except OSError:
            pass
        add(d)
    return out


def scan_concerts(cdir: Path | None = None) -> list[dict]:
    """Concerts (setlists) du dossier des concerts : nom, projet, construit ?, chemins des morceaux."""
    from . import concert as C
    cdir = Path(cdir or C.concert_dir())
    out = []
    try:
        files = sorted(cdir.glob("*.setlist.json"))
    except OSError:
        files = []
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        stem = f.name[:-len(".setlist.json")]
        rpp = f.with_name(stem + ".RPP")
        if not rpp.exists() and f.with_name(stem + ".rpp").exists():
            rpp = f.with_name(stem + ".rpp")
        paths = []
        for e in d.get("songs") or []:
            ref = e.get("project") if isinstance(e, dict) else e
            try:
                paths.append(C.find_project(ref))
            except Exception:
                p = Path(str(ref))
                if p.suffix.lower() == ".rpp":
                    paths.append(p)
        out.append({"name": d.get("name") or stem, "setlist": str(f), "rpp": str(rpp), "built": rpp.exists(),
                    "paths": paths})
    return out


# --------------------------------------------------------------------------- bibliothèque
def build_library(state: dict | None = None, root: Path | None = None, cdir: Path | None = None) -> dict:
    from . import concert as C
    from .i18n import get_lang
    state = state if state is not None else load_state()
    cache = _load_cache()
    concerts = scan_concerts(cdir)
    paths, seen = [], set()
    for p in scan_projects(root, cdir) + [p for c in concerts for p in c["paths"]]:
        k = song_key(p)
        if k not in seen and Path(p).exists():
            seen.add(k)
            paths.append(Path(p))
    in_concert: dict[str, list[str]] = {}
    for c in concerts:
        for p in c["paths"]:
            in_concert.setdefault(song_key(p), [])
            if c["name"] not in in_concert[song_key(p)]:
                in_concert[song_key(p)].append(c["name"])
    songs = []
    for p in paths:
        key = song_key(p)
        info = _rpp_info(p, cache)
        if info is None:
            continue
        info = json.loads(json.dumps(info))
        pub = cache["published"].get(key)
        if isinstance(pub, dict):
            # le dernier prompteur publié : tonalité, accords, paroles, batterie, lumière, structure exacte
            for k in ("bpm", "sig", "key_name", "duration_s", "bars", "sections"):
                if pub.get(k) not in (None, [], ""):
                    info[k] = pub[k]
            for k, v in (pub.get("components") or {}).items():
                old = info["components"].get(k)
                info["components"][k] = max(old, v) if isinstance(v, (int, float)) and isinstance(old, (int, float)) else (v or old)
        rec = song_state(state, p)
        stage, auto, manual = stage_of(rec, bool(info.get("prepared")))
        notes = rec.get("notes") if isinstance(rec.get("notes"), dict) else {}
        songs.append({
            "key": key, "path": str(p), "title": info.get("title") or p.stem, "folder": p.parent.name,
            "bpm": info.get("bpm"), "sig": info.get("sig") or "4/4", "key_name": info.get("key_name"),
            "duration_s": info.get("duration_s") or 0, "bars": info.get("bars") or 0,
            "sections": info.get("sections") or [], "prepared": bool(info.get("prepared")),
            "components": info.get("components") or {}, "concerts": in_concert.get(key, []),
            "published": (pub or {}).get("t") if isinstance(pub, dict) else None,
            "stage": stage, "stage_auto": auto, "stage_manual": manual,
            "practice": {"solo_min": round(float(rec.get("solo_s") or 0) / 60, 1),
                         "band_min": round(float(rec.get("band_s") or 0) / 60, 1),
                         "band_days": band_days(rec), "last": rec.get("last")},
            "notes": sum(1 for v in notes.values() if str(v or "").strip()),
        })
    songs.sort(key=lambda s: (s["title"].lower(), s["path"].lower()))
    _save_cache(cache)
    data = {
        "version": 1, "generated": int(time.time()), "language": get_lang(),
        "projects_dir": str(root or C.media_dir()), "concert_dir": str(cdir or C.concert_dir()),
        "stages": list(STAGES),
        "rules": {"solo_min": SOLO_S / 60, "band_min": BAND_S / 60, "stage_days": STAGE_DAYS,
                  "day_min": BAND_DAY_S / 60},
        "songs": songs,
        "concerts": [{"name": c["name"], "rpp": c["rpp"], "built": c["built"],
                      "songs": [song_key(p) for p in c["paths"]]} for c in concerts],
    }
    sig = json.dumps({k: v for k, v in data.items() if k != "generated"}, sort_keys=True, ensure_ascii=False)
    data["id"] = hashlib.md5(sig.encode()).hexdigest()[:12]
    return data


def publish_library(www: Path | None = None, **kw) -> dict:
    """Écrit reaper_www_root/reacue_library.json (écriture atomique) ; renvoie les données."""
    if www is None:
        from .prompter import WWW_DIR
        www = WWW_DIR
    www = Path(www)
    data = build_library(**kw)
    www.mkdir(parents=True, exist_ok=True)
    tmp = www / (LIBRARY_NAME + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, www / LIBRARY_NAME)
    return data


# --------------------------------------------------------------------------- notes publiées
def apply_notes_published(www: Path | None = None, state: dict | None = None) -> dict:
    """Recopie les notes de section de l'état durable dans le prompteur publié (reacue_song.json) et, pour un
    concert, dans <concert>.prompteur.json (sinon la fenêtre les effacerait en republiant le concert)."""
    from . import concert as C
    if www is None:
        from .prompter import WWW_DIR
        www = WWW_DIR
    www = Path(www)
    state = state if state is not None else load_state()
    f = www / "reacue_song.json"
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"updated": False}
    songs = data["songs"] if data.get("concert") and isinstance(data.get("songs"), list) else [data]
    before = json.dumps(data, sort_keys=True, ensure_ascii=False)
    for s in songs:
        if s.get("project"):
            attach(s, s["project"], state, recompute=data is s)
            if data is not s:
                rehash(s)
    if data.get("concert"):
        rehash(data)
    if json.dumps(data, sort_keys=True, ensure_ascii=False) == before:
        return {"updated": False}
    text = json.dumps(data, ensure_ascii=False)
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, f)
    out = {"updated": True, "file": str(f)}
    if data.get("concert"):
        name = data["concert"].get("name") or ""
        pf = C.concert_dir() / f"{C._slug(name)}.prompteur.json"
        try:
            cur = json.loads(pf.read_text(encoding="utf-8"))
            if (cur.get("concert") or {}).get("name") == name:
                tmp = pf.with_suffix(".tmp")
                tmp.write_text(text, encoding="utf-8")
                os.replace(tmp, pf)
                out["concert_file"] = str(pf)
        except (OSError, ValueError):
            pass
    return out


# --------------------------------------------------------------------------- morceau ouvert depuis BIBLIO
def published_project() -> str | None:
    """Projet du morceau seul actuellement publié (None : concert ou rien)."""
    from .prompter import WWW_DIR, SONG_NAME
    try:
        d = json.loads((WWW_DIR / SONG_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return None if d.get("concert") else d.get("project")


def song_from_project(path, extras: bool = False, log=None) -> dict:
    """Prompteur d'un morceau déjà préparé, reconstruit depuis son .RPP (grille, régions validées, notes) :
    même calcul que pour un morceau de concert, placé à son propre temps (aucun décalage)."""
    from types import SimpleNamespace
    from . import concert as C
    p = Path(path)
    s = C.load_song(p)
    if not s.regions:
        raise ValueError("not prepared")
    s.stop = s.song_end
    res = SimpleNamespace(song_srcs=[s], songs=[{"n": 1, "title": s.title, "start": 0.0, "stop": s.song_end,
                                                   "next": s.song_end}], name=s.title)
    data = C.concert_prompter(res, extras=extras, log=log)
    song = data["songs"][0]
    for k in ("n", "start_t", "stop_t", "next_t", "next_title"):
        song.pop(k, None)
    try:                                   # onglet Lumière du prompteur (cues grandMA3), sans écrire de fichier
        from . import lighting
        cfg = lighting.config()
        if cfg["export"]:
            song["lighting"] = lighting.web_data(lighting.show_from_songs([song]), cfg)
    except Exception:
        pass
    return attach(song, str(p))


def publish_project(path, log=None) -> dict:
    """Commande « open-song » (ouverture depuis BIBLIO) : publie tout de suite la structure du morceau, puis
    ses accords, paroles et batterie (caches ou calcul) s'il est toujours celui qui est affiché."""
    from . import prompter
    key = song_key(path)
    out = {"project": str(path)}
    try:
        quick = song_from_project(path, extras=False)
    except ValueError:
        out["prepared"] = False
        publish_library()
        return out
    prompter.publish(quick)
    out["published"] = True
    try:
        full = song_from_project(path, extras=True, log=log)
        if song_key(published_project() or "") == key:
            prompter.publish(full)
            record_song(full, path)
            out["extras"] = True
    except Exception as e:                 # jamais bloquant : la structure reste publiée
        out["warning"] = str(e)
    publish_library()
    return out
