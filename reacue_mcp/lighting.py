"""Export lumière grandMA3 : une Sequence (un cue par section) et un Timecode qui déclenche ces cues.

Source des cues : les sections ReaCue (régions REAPER) déjà publiées pour le prompteur. Un cue par
section, au début de sa région, en temps PROJET REAPER (0 = début du projet, count-in compris).

    Morceau seul :  <dossier du .RPP>/grandMA3/<Titre>_Sequence.xml, _Timecode.xml, _conduite.csv
    Concert :       <dossier des concerts>/grandMA3/<Concert>/<Titre>_Sequence.xml (un par morceau),
                    <Concert>_Timecode.xml (une piste par morceau), <Concert>_conduite.csv

Les fichiers sont aussi copiés dans reaper_www_root (préfixe « reacue_gma3_ ») : l'onglet Lumière du
prompteur propose de les télécharger.

Les générateurs XML reprennent À L'IDENTIQUE ceux validés sur une vraie console (DataVersion 2.4.2.2,
BOM UTF-8, OffCue + CueZero, No sur 3 caractères, Target sans apostrophes, Object="13.13.0.5.<piste>",
ValCueDestination="0.5.<piste>.<n°*1000>", CueDestination = nom exact du cue). Ne pas les « nettoyer ».

Réglages (reacue_settings.json) : gma3_export, gma3_fps, gma3_tc_start (le décalage du timecode est
ajouté aux temps du XML et de la fiche de conduite) ; gma3_song_gap et gma3_song_slot agissent sur le
placement des morceaux du concert (concert.py).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
import uuid
from pathlib import Path

from .i18n import get_lang, section_kind

FPS_CHOICES = (24.0, 25.0, 29.97, 30.0)
WEB_PREFIX = "reacue_gma3_"
FOLDER = "grandMA3"

# --------------------------------------------------------------------------- #
# Bibliothèque d'effets (reprise de l'appli de référence) et types de cues
# --------------------------------------------------------------------------- #
TYPE_LABELS = {
    "intro": ("Intro", "Intro"), "build": ("Montée", "Build-up"), "drop": ("Drop", "Drop"),
    "breakdown": ("Descente", "Breakdown"), "outro": ("Outro", "Outro"), "custom": ("Perso", "Custom"),
    "verse": ("Couplet", "Verse"), "chorus": ("Refrain", "Chorus"), "bridge": ("Pont", "Bridge"),
    "inst": ("Instrumental", "Instrumental"),
}

EFFECT_LIBRARY = {
    "fr": {
        "intro": ["Wash tamisé, teintes chaudes", "Fondu progressif général, faible intensité", "Contre-jour doux",
                  "Gobo lent, faible intensité"],
        "build": ["Chase qui accélère", "Strobe progressif montant", "Balayage de position ascendant",
                  "Montée d'intensité + couleur qui se réchauffe"],
        "drop": ["Strobe plein feu", "Blinder public", "Flash d'impact + coupure noire avant",
                 "Chase rapide toutes fixtures"],
        "breakdown": ["Retour calme, wash unique", "Coupure partielle, une seule zone", "Couleur froide, mouvement lent",
                      "Fade vers ambiance tamisée"],
        "outro": ["Fondu long vers noir", "Wash statique qui s'éteint", "House light progressif",
                  "Dernier effet qui se fige"],
        "custom": ["Repère à personnaliser", "Effet ponctuel", "Accent rapide", "Highlight bref"],
        "verse": ["Wash calme, mouvement discret", "Une seule couleur dominante, faible intensité",
                  "Position statique, focus voix"],
        "chorus": ["Effet plein, toutes les têtes en mouvement", "Couleur saturée + strobe ponctuel",
                   "Chase synchronisé sur le refrain", "Intensité max, palette large"],
        "bridge": ["Rupture d'ambiance, nouvelle couleur", "Effet inhabituel, contraste avec le reste",
                   "Position/gobo différent du reste du titre"],
        "inst": ["Solo lumière sur l'instrument, suiveur", "Effet de mouvement complexe, sans à-coup vocal",
                 "Chase rapide, pas de wash statique"],
    },
    "en": {
        "intro": ["Dimmed wash, warm tones", "Slow general fade-in, low intensity", "Soft backlight",
                  "Slow gobo, low intensity"],
        "build": ["Accelerating chase", "Rising progressive strobe", "Upward position sweep",
                  "Intensity rising + colour warming up"],
        "drop": ["Full strobe", "Audience blinder", "Impact flash + blackout just before", "Fast chase on all fixtures"],
        "breakdown": ["Back to calm, single wash", "Partial blackout, one zone only", "Cold colour, slow movement",
                      "Fade to a dimmed look"],
        "outro": ["Long fade to black", "Static wash fading out", "Progressive house light", "Last effect freezing"],
        "custom": ["Cue to customise", "One-off effect", "Quick accent", "Short highlight"],
        "verse": ["Calm wash, subtle movement", "One dominant colour, low intensity", "Static position, focus on vocals"],
        "chorus": ["Full effect, all heads moving", "Saturated colour + occasional strobe", "Chase synced to the chorus",
                   "Max intensity, wide palette"],
        "bridge": ["Change of mood, new colour", "Unusual effect, contrast with the rest",
                   "Position/gobo different from the rest of the song"],
        "inst": ["Light solo on the instrument, follow spot", "Complex movement effect, no vocal hit",
                 "Fast chase, no static wash"],
    },
}

# type de section ReaCue (i18n.section_kind, FR et EN) -> type de cue de la bibliothèque
KIND_TO_TYPE = {
    "intro": "intro", "verse": "verse", "prechorus": "build", "chorus": "chorus", "bridge": "bridge",
    "solo": "inst", "break": "breakdown", "interlude": "inst", "riff": "inst", "outro": "outro",
    "other": "custom",
}


def cue_type(section_name: str) -> str:
    """« Refrain 2 » / « Chorus 2 » -> chorus ; « Pré-refrain » -> build ; « Coda » -> outro…"""
    return KIND_TO_TYPE.get(section_kind(section_name), "custom")


def effect_for(ctype: str, idx: int = 0, lang: str | None = None) -> str:
    lib = EFFECT_LIBRARY["en" if (lang or get_lang()) == "en" else "fr"]
    arr = lib.get(ctype) or lib["custom"]
    return arr[((idx % len(arr)) + len(arr)) % len(arr)]


def type_label(ctype: str, lang: str | None = None) -> str:
    fr, en = TYPE_LABELS.get(ctype, TYPE_LABELS["custom"])
    return en if (lang or get_lang()) == "en" else fr


# --------------------------------------------------------------------------- #
# Réglages, timecode
# --------------------------------------------------------------------------- #
def parse_tc(tc, fps: float = 25.0) -> float | None:
    """« 01:00:00:00 » (HH:MM:SS:FF, « ; » accepté) -> secondes ; None si illisible."""
    m = re.fullmatch(r"\s*(\d{1,2})[:;.](\d{1,2})[:;.](\d{1,2})(?:[:;.](\d{1,2}))?\s*", str(tc or ""))
    if not m:
        return None
    h, mi, s, f = (int(x or 0) for x in m.groups())
    if mi > 59 or s > 59 or f >= round(fps):
        return None
    return h * 3600 + mi * 60 + s + f / fps


def seconds_to_smpte(sec: float, fps: float) -> str:
    """Port exact de secondsToSMPTE (appli de référence) : HH:MM:SS:FF, non drop-frame."""
    sec = max(0.0, float(sec))
    total_frames = _js_round(sec * fps)
    fr = total_frames % _js_round(fps)
    total_sec = math.floor(total_frames / fps)
    s = total_sec % 60
    total_min = math.floor(total_sec / 60)
    m = total_min % 60
    h = math.floor(total_min / 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}:{int(fr):02d}"


def _js_round(x: float) -> int:
    """Math.round de JavaScript (demi vers +∞), pas l'arrondi bancaire de Python."""
    return int(math.floor(x + 0.5))


def config(settings: dict | None = None) -> dict:
    """Réglages lumière validés : export, fps, tc_start (texte) et offset_s (secondes), gap_s, slot_s."""
    if settings is None:
        from .settings import load_settings
        settings = load_settings()
    fps = _fps(settings.get("gma3_fps"))
    tc = str(settings.get("gma3_tc_start") or "00:00:00:00")
    off = parse_tc(tc, fps)
    if off is None:
        tc, off = "00:00:00:00", 0.0
    return {"export": bool(settings.get("gma3_export", True)), "fps": fps, "tc_start": tc,
            "offset_s": round(off, 6), "gap_s": _num(settings.get("gma3_song_gap"), None),
            "slot_s": _num(settings.get("gma3_song_slot"), 0.0) or 0.0}


def _fps(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 25.0
    for c in FPS_CHOICES:
        if abs(f - c) < 0.01:
            return c
    return 25.0


def _num(v, default):
    if v is None or isinstance(v, bool):
        return default
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    return f if f >= 0 and math.isfinite(f) else default


# --------------------------------------------------------------------------- #
# Noms
# --------------------------------------------------------------------------- #
def clean_name(name, default: str = "Song") -> str:
    """Nom de Sequence grandMA3 : ASCII, lettres/chiffres et « _ » (« Démo du soir » -> Demo_du_soir).
    Un nom qui commencerait par un chiffre est préfixé (« Seq_42 ») : Sequences.42 désignerait le
    numéro 42 de la console, pas un nom."""
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    if not s:
        s = default
    if s[0].isdigit():
        s = "Seq_" + s
    return s


def unique(names: list[str], fmt: str = "{} ({})") -> list[str]:
    """Dédoublonne en gardant l'ordre : « Refrain », « Refrain » -> « Refrain », « Refrain (2) »."""
    used, out = set(), []
    for n in names:
        cand, k = n, 2
        while cand in used:
            cand = fmt.format(n, k)
            k += 1
        used.add(cand)
        out.append(cand)
    return out


# --------------------------------------------------------------------------- #
# Spectacle : pistes (morceaux) et cues, à partir des données du prompteur
# --------------------------------------------------------------------------- #
def _bar_t(song: dict, bar: int) -> float:
    bt = song["bar_times"]
    i = min(max(int(bar) - 1 + int(song.get("count_in_bars", 0)), 0), len(bt) - 1)
    return float(bt[i])


def show_from_songs(songs: list[dict], name: str | None = None) -> dict:
    """songs : morceaux au format du prompteur (prompter.build_song ; concert : + start_t / stop_t).

    Renvoie {"name", "concert", "tracks": [{"title", "seq", "start", "duration", "cues": [...]}]} ;
    cue : {"n", "name" (unique dans la Sequence), "label" (nom de section), "time" (s depuis le début du
    morceau), "type", "effect": {"fr", "en"}, "type_label": {"fr", "en"}}. start = temps projet du début
    du morceau (0 pour un morceau seul)."""
    concert = name is not None
    seqs = unique([clean_name(s.get("title"), "Song") for s in songs], "{}_{}")
    tracks = []
    for s, seq in zip(songs, seqs):
        start = float(s.get("start_t", 0.0)) if concert else 0.0
        end = float(s["stop_t"]) if concert and s.get("stop_t") is not None else float(s["bar_times"][-1])
        secs = sorted(s.get("sections") or [], key=lambda x: int(x["start_bar"]))
        names = unique([str(x.get("name") or "Cue").strip() or "Cue" for x in secs])
        cues = []
        for n, (sec, cname) in enumerate(zip(secs, names), 1):
            ct = cue_type(sec.get("name") or "")
            cues.append({
                "n": n, "name": cname, "label": sec.get("name") or cname,
                "time": round(_bar_t(s, sec["start_bar"]) - start, 6), "type": ct,
                "type_label": {lg: type_label(ct, lg) for lg in ("fr", "en")},
                "effect": {lg: effect_for(ct, 0, lg) for lg in ("fr", "en")},
            })
        tracks.append({"title": s.get("title") or seq, "seq": seq, "start": round(start, 6),
                       "duration": round(max(0.0, end - start), 6), "cues": cues})
    base = clean_name(name, "Concert") if concert else (tracks[0]["seq"] if tracks else "Song")
    return {"name": base, "concert": concert, "tracks": tracks}


def file_names(show: dict) -> dict:
    """Noms des fichiers : {"sequences": [...], "timecode", "csv"} (identiques sur disque et en téléchargement)."""
    b = show["name"]
    return {"sequences": [f"{tr['seq']}_Sequence.xml" for tr in show["tracks"]],
            "timecode": f"{b}_Timecode.xml", "csv": f"{b}_conduite.csv"}


def web_name(show: dict, fname: str) -> str:
    """Nom dans reaper_www_root (préfixé ; concert : + nom du concert, pour ne pas mélanger)."""
    return WEB_PREFIX + (f"{show['name']}__{fname}" if show["concert"] else fname)


# --------------------------------------------------------------------------- #
# Générateurs grandMA3 (port exact de buildSequenceXML / buildTrackEvents / buildTimecodeXML)
# --------------------------------------------------------------------------- #
def escape_xml(s) -> str:
    return (str("" if s is None else s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))


def guid() -> str:
    return " ".join(f"{b:02X}" for b in uuid.uuid4().bytes)


def cue_no_str(n: int) -> str:
    return str(n).rjust(3, " ")


def _comment(effect: str, lang: str) -> str:
    return ("Suggested effect: " if lang == "en" else "Effet suggéré : ") + escape_xml(effect)


def build_sequence_xml(title: str, cues: list[dict], lang: str | None = None) -> str:
    lang = "en" if (lang or get_lang()) == "en" else "fr"
    part = lambda: ('            <Part Guid="' + guid() + '" AlignRangeX="No" AlignRangeY="No" AlignRangeZ="No" '
                    'PreserveGridPositions="No" MAgic="No" Mode="0" Action="Pool Default"/>\n')
    c = ''
    c += '        <Cue Name="OffCue" Release="Yes" Assert="Assert" AllowDuplicates="" TrigType="">\n'
    c += part()
    c += '        </Cue>\n'
    c += '        <Cue Name="CueZero" No="  0">\n'
    c += part()
    c += '        </Cue>\n'
    for i, m in enumerate(cues):
        n = i + 1
        c += '        <!-- ' + _comment(_eff(m, lang), lang) + ' -->\n'
        c += '        <Cue Name="' + escape_xml(m["name"]) + '" No="' + cue_no_str(n) + '" AllowDuplicates="">\n'
        c += part()
        c += '        </Cue>\n'
    return ('﻿<?xml version="1.0" encoding="UTF-8"?>\n'
            '<GMA3 DataVersion="2.4.2.2">\n'
            '    <Sequence Name="' + escape_xml(title) + '" Guid="' + guid() + '" AutoStart="Yes" AutoStop="Yes" '
            'AutoFix="No" AutoStomp="No" SoftLTP="Yes" XFadeReload="No" SwapProtect="No" KillProtect="No" '
            'UseExecutorTime="Yes" OffwhenOverridden="Yes" SequMIB="Enabled" AutoPrePos="Yes" WrapAround="Yes" '
            'MasterGoMode="None" SpeedfromRate="No" Tracking="Yes" IncludeLinkLastGo="Yes" RateScale="One" '
            'SpeedScale="One" PreferCueAppearance="No" ExecutorDisplayMode="Data and&#xD;Appearance" '
            'Action="Pool Default">\n'
            + c +
            '    </Sequence>\n'
            '</GMA3>\n')


def _eff(m: dict, lang: str) -> str:
    e = m.get("effect") or ""
    return e.get(lang, "") if isinstance(e, dict) else str(e)


def _fixed(x: float, nd: int) -> str:
    """Number.toFixed (arrondi au plus proche, demi vers le haut sur la valeur décimale)."""
    q = 10 ** nd
    v = math.floor(abs(float(x)) * q + 0.5) / q
    return ("-" if x < 0 and v else "") + f"{v:.{nd}f}"


def build_track_events(track: dict, track_index: int, lang: str | None = None) -> str:
    """track : {"start" (s, temps du timecode), "cues": [{"time" (s depuis start), "name", "effect"}]}."""
    lang = "en" if (lang or get_lang()) == "en" else "fr"
    ev = ''
    for i, m in enumerate(track["cues"]):
        n = i + 1
        t = _fixed(float(m["time"]) + float(track.get("start") or 0), 3)
        cue_name = escape_xml(m["name"])
        ev += '                        <!-- ' + _comment(_eff(m, lang), lang) + ' -->\n'
        # CueDestination = NOM exact du cue dans la Sequence (validé sur console)
        ev += '                        <CmdEvent Name="Goto" Time="' + t + '" CueDestination="' + cue_name + '">\n'
        # « 5 » fixe ; le dernier index = rang de la Track dans ce Timecode (0, 1, 2…)
        ev += ('                            <RealtimeCmd Type="Key" Source="Original" UserProfile="0" Environment="0" '
               'User="1" Status="On" IsRealtime="1" IsXFade="0" IgnoreFollow="0" IgnoreCommand="0" Assert="0" '
               'IgnoreNetwork="0" FromTriggerNode="0" IgnoreExecTime="0" IssuedByTimecode="0" '
               'FromLocalHardwareFader="1" IgnoreExecXFade="0" IsExecXFade="0" Object="13.13.0.5.'
               + str(track_index) + '" ExecToken="Goto" ValCueDestination="0.5.' + str(track_index) + '.'
               + str(n * 1000) + '"/>\n')
        ev += '                        </CmdEvent>\n'
    return ev


def build_timecode_xml(tracks: list[dict], lang: str | None = None) -> str:
    """tracks : [{"seq" (nom de la Sequence), "start", "duration", "cues"}] ; une Track par élément."""
    out = ''
    for idx, tr in enumerate(tracks):
        title = escape_xml(tr["seq"])
        # Target SANS guillemets/apostrophes autour du nom (validé sur console)
        out += ('            <Track Name="' + title + '" Guid="' + guid() + '" Play="" Rec="" '
                'Target="ShowData.DataPools.Default.Sequences.' + title + '">\n')
        out += '                <TimeRange Guid="' + guid() + '" Duration="To End" Play="" Rec="" Start="0.000">\n'
        out += '                    <CmdSubTrack>\n'
        out += build_track_events(tr, idx, lang)
        out += '                    </CmdSubTrack>\n'
        out += '                </TimeRange>\n'
        out += '            </Track>\n'
    total = max([0.0] + [float(tr.get("start") or 0) + float(tr.get("duration") or 0) for tr in tracks])
    dur = _fixed(total, 2)
    return ('﻿<?xml version="1.0" encoding="UTF-8"?>\n'
            '<GMA3 DataVersion="2.4.2.2">\n'
            '    <Timecode Name="" Guid="' + guid() + '" Cursor="' + dur + '" Duration="' + dur + '" LoopCount="0" '
            'TCSlot="-1" AutoStop="No" SwitchOff="Keep Playbacks" TimeDisplayFormat="Default" FrameReadout="Seconds">\n'
            '        <TrackGroup Play="" Rec="">\n'
            '            <MarkerTrack Name="Marker" Guid="' + guid() + '"/>\n'
            + out +
            '        </TrackGroup>\n'
            '    </Timecode>\n'
            '</GMA3>\n')


def _tc_tracks(show: dict, offset_s: float) -> list[dict]:
    """Pistes du Timecode : départ = temps projet du morceau + départ du timecode (gma3_tc_start)."""
    return [dict(tr, start=round(tr["start"] + offset_s, 6)) for tr in show["tracks"]]


def escape_csv(s) -> str:
    s = str(s)
    if re.search(r'[",\n]', s):
        return '"' + s.replace('"', '""') + '"'
    return s


def build_conduite_csv(show: dict, fps: float, offset_s: float = 0.0, lang: str | None = None) -> str:
    """Fiche de conduite : Timecode SMPTE, Cue, Libellé, Type, Effet (concert : + colonne Morceau)."""
    en = (lang or get_lang()) == "en"
    lg = "en" if en else "fr"
    head = ["Timecode", "Cue", "Label" if en else "Libellé", "Type", "Suggested effect" if en else "Effet suggéré"]
    if show["concert"]:
        head.insert(0, "Song" if en else "Morceau")
    rows = [",".join(head)]
    for tr in show["tracks"]:
        for m in tr["cues"]:
            r = [seconds_to_smpte(offset_s + tr["start"] + m["time"], fps), f"Cue {m['n']}", escape_csv(m["name"]),
                 escape_csv(m["type_label"][lg]), escape_csv(_eff(m, lg))]
            if show["concert"]:
                r.insert(0, escape_csv(tr["seq"]))
            rows.append(",".join(r))
    return "﻿" + "\n".join(rows) + "\n"


# --------------------------------------------------------------------------- #
# Données du prompteur (onglet Lumière) et écriture des fichiers
# --------------------------------------------------------------------------- #
def web_data(show: dict, cfg: dict) -> dict:
    """Bloc « lighting » publié dans reacue_song.json (onglet Lumière)."""
    fn = file_names(show)
    files = [{"kind": "sequence", "name": n, "url": web_name(show, n), "song": tr["title"]}
             for n, tr in zip(fn["sequences"], show["tracks"])]
    files += [{"kind": "timecode", "name": fn["timecode"], "url": web_name(show, fn["timecode"])},
              {"kind": "csv", "name": fn["csv"], "url": web_name(show, fn["csv"])}]
    cues = []
    for k, tr in enumerate(show["tracks"]):
        for m in tr["cues"]:
            t = tr["start"] + m["time"]
            cues.append({"track": k, "song": tr["title"], "seq": tr["seq"], "n": m["n"], "name": m["name"],
                         "t": round(t, 4), "tc": seconds_to_smpte(cfg["offset_s"] + t, cfg["fps"]),
                         "type": m["type"], "type_label": m["type_label"], "effect": m["effect"]})
    out = {"version": 1, "fps": cfg["fps"], "tc_start": cfg["tc_start"], "offset_s": cfg["offset_s"],
           "concert": show["concert"], "files": files, "cues": cues}
    if show["concert"]:
        out["slot_s"] = cfg.get("slot_s") or 0
        if cfg.get("gap_s") is not None:
            out["gap_s"] = cfg["gap_s"]
    return out


def render_files(show: dict, cfg: dict, lang: str | None = None) -> dict[str, str]:
    """{nom de fichier: contenu} des Sequences, du Timecode et de la fiche de conduite."""
    fn = file_names(show)
    out = {n: build_sequence_xml(tr["seq"], tr["cues"], lang) for n, tr in zip(fn["sequences"], show["tracks"])}
    out[fn["timecode"]] = build_timecode_xml(_tc_tracks(show, cfg["offset_s"]), lang)
    out[fn["csv"]] = build_conduite_csv(show, cfg["fps"], cfg["offset_s"], lang)
    return out


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))
    tmp.replace(path)


def write_files(show: dict, cfg: dict, folder: Path | None, www: Path | None, lang: str | None = None) -> dict:
    """Écrit les fichiers dans folder (dossier grandMA3) et/ou www (préfixés) ; renvoie les chemins."""
    files = render_files(show, cfg, lang)
    out = {"files": [], "web": []}
    if folder is not None:
        folder = Path(folder)
        for n, txt in files.items():
            _write(folder / n, txt)
            out["files"].append(str(folder / n))
        out["dir"] = str(folder)
    if www is not None:
        www = Path(www)
        keep = {web_name(show, n) for n in files}
        # anciens fichiers du même genre (morceau seul : ceux du morceau précédent ; concert : même concert)
        pre = WEB_PREFIX + (f"{show['name']}__" if show["concert"] else "")
        for old in www.glob(WEB_PREFIX + "*"):
            if old.name in keep or not old.name.startswith(pre) or (not show["concert"] and "__" in old.name):
                continue
            try:
                old.unlink()
            except OSError:
                pass
        for n, txt in files.items():
            _write(www / web_name(show, n), txt)
            out["web"].append(web_name(show, n))
    return out


def rehash(d: dict) -> dict:
    """Recalcule l'identifiant des données publiées (la page recharge quand il change)."""
    d.pop("id", None)
    d["id"] = hashlib.md5(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    return d


def export_song(song: dict, project: str | Path | None, www: Path | None = None, cfg: dict | None = None) -> dict | None:
    """Morceau seul : écrit les fichiers à côté du .RPP (sous-dossier grandMA3/) et dans le dossier web,
    ajoute le bloc « lighting » à song (identifiant recalculé). None si gma3_export est désactivé.
    project : chemin du .RPP ouvert (None / "" : projet non enregistré -> dossier web seulement)."""
    cfg = cfg or config()
    if not cfg["export"]:
        return None
    if www is None:
        from .prompter import WWW_DIR
        www = WWW_DIR
    show = show_from_songs([song])
    folder = Path(project).parent / FOLDER if project else None
    res = write_files(show, cfg, folder, www)
    song["lighting"] = web_data(show, cfg)
    rehash(song)
    res["cues"] = sum(len(tr["cues"]) for tr in show["tracks"])
    return res


def export_concert(name: str, data: dict, out_dir: Path, www: Path | None, cfg: dict | None = None) -> dict | None:
    """Concert : une Sequence par morceau + un seul Timecode (une piste par morceau) + fiche de conduite,
    dans <dossier des concerts>/grandMA3/<concert>/ (et le dossier web si www). data : prompteur du concert."""
    cfg = cfg or config()
    if not cfg["export"]:
        return None
    show = show_from_songs(data["songs"], name)
    res = write_files(show, cfg, Path(out_dir) / FOLDER / show["name"], www)
    res["cues"] = sum(len(tr["cues"]) for tr in show["tracks"])
    return res
