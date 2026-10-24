"""Pistes timecode pour la lumière grandMA3 : TIMECODE LTC (audio) et TIMECODE MTC (MIDI).

REAPER envoie lui-même le timecode à la console : un item « générateur SMPTE LTC/MTC » (action 40208,
Insert > SMPTE LTC/MTC Timecode Generator) couvre tout le projet ; la piste LTC va vers une sortie audio
(`gma3_ltc_output`, ex. 7 = sortie 7, "7/8" = paire), la piste MTC vers une sortie MIDI
(`gma3_mtc_output`, nom du périphérique, ex. "IAC Driver Bus 1"). Réglage vide = pas de piste.
Temps envoyé = temps projet + `gma3_tc_start` (à `gma3_fps`), comme les temps du Timecode XML.

Format du générateur dans le .RPP : le bloc `<SOURCE LTC …>` est bien le type de source du générateur
(SWS : GetMediaSourceType == "LTC"), mais ses champs (départ, fps, « Send MIDI (MTC) ») ne sont PAS
documentés. ReaCue ne les écrit donc jamais de lui-même : il insère le générateur par l'action REAPER
puis réapplique le bloc SOURCE que l'utilisateur a réglé UNE fois dans « Propriétés de la source »
(mémorisé par réglage fps + départ dans <ressources REAPER>/ReaCueMCP/timecode/). Tant que ce n'est
pas fait, la préparation le rappelle (avertissement).
"""
from __future__ import annotations

import re
from pathlib import Path

from .bridge import BRIDGE_DIR

TRACK_LTC = "TIMECODE LTC"
TRACK_MTC = "TIMECODE MTC"
TRACKS = (TRACK_LTC, TRACK_MTC)
TEMPLATE_DIR_NAME = "timecode"
TAIL_S = 8.0                    # le timecode continue un peu après la fin du morceau / du concert
LTC_VOLUME = 0.5                # -6 dB : niveau ligne raisonnable pour l'entrée LTC de la console
MONO_FLAG = 1024                # I_DSTCHAN / I_SRCCHAN : bit « mono »


def template_dir() -> Path:
    return BRIDGE_DIR / TEMPLATE_DIR_NAME


# --------------------------------------------------------------------------- #
# Réglages
# --------------------------------------------------------------------------- #
def parse_audio_output(v) -> dict | None:
    """gma3_ltc_output -> {"dst": I_DSTCHAN, "src": I_SRCCHAN, "label": "7" | "7/8"} ; None = pas de sortie.

    7 ou "7" : sortie 7 seule (mono) ; "7/8" (ou "7-8", "7+8") : paire 7/8 (stéréo). Les numéros
    commencent à 1, comme dans REAPER (le click, lui, garde son index 0 = 1/2)."""
    if v is None or isinstance(v, bool):
        return None
    s = str(v).strip()
    if not s or s.lower() in ("none", "null", "off", "no", "0"):
        return None
    m = re.fullmatch(r"(\d{1,3})(?:\s*[/+\-]\s*(\d{1,3}))?", s)
    if not m:
        try:
            f = float(s)
        except ValueError:
            return None
        if f != int(f) or f < 1:
            return None
        m = re.fullmatch(r"(\d{1,3})()", str(int(f)))
    a = int(m.group(1))
    b = int(m.group(2)) if m.group(2) else None
    if a < 1 or a > 512:
        return None
    if b is None or b == a:
        return {"dst": (a - 1) | MONO_FLAG, "src": 0 | MONO_FLAG, "label": str(a)}
    if b != a + 1:
        return None
    return {"dst": a - 1, "src": 0, "label": f"{a}/{b}"}


def midi_output_name(v) -> str | None:
    if v is None or isinstance(v, bool):
        return None
    s = str(v).strip()
    return s if s and s.lower() not in ("none", "null", "off", "no") else None


def tc_slot(v) -> int:
    """gma3_tc_slot : 1 à 8 (TCSlot 1 à 8 de grandMA3) ; toute autre valeur -> 1."""
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return 1
    return n if 1 <= n <= 8 else 1


def config(settings: dict | None = None) -> dict:
    """{"fps", "tc_start", "offset_s", "slot", "ltc" (sortie audio | None), "mtc" (périphérique | None),
    "enabled"} ; fps et départ validés comme pour l'export lumière (lighting.config)."""
    if settings is None:
        from .settings import load_settings
        settings = load_settings()
    from .lighting import config as light_config
    lc = light_config(settings)
    ltc = parse_audio_output(settings.get("gma3_ltc_output"))
    mtc = midi_output_name(settings.get("gma3_mtc_output"))
    return {"fps": lc["fps"], "tc_start": lc["tc_start"], "offset_s": lc["offset_s"],
            "slot": tc_slot(settings.get("gma3_tc_slot")), "ltc": ltc, "mtc": mtc,
            "enabled": bool(ltc or mtc)}


def web_status(cfg: dict) -> dict:
    """État des sorties pour l'onglet Lumière du prompteur."""
    return {"ltc": cfg["ltc"]["label"] if cfg.get("ltc") else None, "mtc": cfg.get("mtc"),
            "slot": cfg.get("slot", 1), "fps": cfg.get("fps"), "tc_start": cfg.get("tc_start")}


# --------------------------------------------------------------------------- #
# Blocs SOURCE mémorisés (réglés une fois par l'utilisateur dans REAPER)
# --------------------------------------------------------------------------- #
def template_key(kind: str, cfg: dict) -> str:
    """ltc_25_01-00-00-00 / mtc_29.97_00-00-00-00 : un bloc par sorte, fps et départ."""
    fps = f"{cfg['fps']:g}"
    return f"{kind}_{fps}_{re.sub(r'[^0-9]+', '-', cfg['tc_start']).strip('-')}"


def is_source_block(text) -> bool:
    """Bloc `<SOURCE LTC` … `>` équilibré (seul format accepté, jamais du code)."""
    if not isinstance(text, str):
        return False
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines or not re.fullmatch(r"<SOURCE LTC\b.*", lines[0]) or lines[-1] != ">":
        return False
    depth = 0
    for ln in lines:
        if ln.startswith("<"):
            depth += 1
        elif ln == ">":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _norm_block(text: str) -> str:
    return "\n".join(ln.strip() for ln in text.strip().splitlines() if ln.strip())


def _path(key: str, default: bool = False) -> Path:
    return template_dir() / (f"{key}.default.txt" if default else f"{key}.txt")


def load_template(key: str) -> str | None:
    try:
        txt = _path(key).read_text(encoding="utf-8")
    except OSError:
        return None
    return _norm_block(txt) if is_source_block(txt) else None


def _write(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(_norm_block(text) + "\n", encoding="utf-8")
    tmp.replace(p)


def _load_default(key: str) -> str | None:
    try:
        txt = _path(key, True).read_text(encoding="utf-8")
    except OSError:
        return None
    return _norm_block(txt) if is_source_block(txt) else None


# --------------------------------------------------------------------------- #
# Plan envoyé au pont REAPER, retour du pont
# --------------------------------------------------------------------------- #
def plan_block(cfg: dict, min_len: float) -> dict:
    """Bloc « timecode » du plan (ReaCue_Bridge.lua ≥ 1.4). tracks vide : les pistes timecode existantes
    sont seulement retirées (réglages vidés)."""
    tracks = []
    if cfg.get("ltc"):
        key = template_key("ltc", cfg)
        tracks.append({"kind": "ltc", "name": TRACK_LTC, "key": key, "template": load_template(key),
                       "audio_dst": cfg["ltc"]["dst"], "audio_src": cfg["ltc"]["src"],
                       "label": cfg["ltc"]["label"], "volume": LTC_VOLUME})
    if cfg.get("mtc"):
        key = template_key("mtc", cfg)
        tracks.append({"kind": "mtc", "name": TRACK_MTC, "key": key, "template": load_template(key),
                       "midi_out": cfg["mtc"]})
    return {"tracks": tracks, "min_len": round(max(0.0, float(min_len)), 3),
            "fps": cfg["fps"], "tc_start": cfg["tc_start"]}


def handle_result(res: dict | None, cfg: dict) -> tuple[dict | None, list[str]]:
    """Après apply_plan : mémorise les blocs SOURCE réglés par l'utilisateur, renvoie (résumé, avertissements).

    origin (pont) : "kept" = générateur déjà présent sur la piste, mêmes réglages ReaCue (fps + départ) :
    l'utilisateur a pu le régler, c'est lui qui compte ; "template" = bloc mémorisé réappliqué ;
    "default" = générateur neuf, réglages par défaut de REAPER (à régler une fois)."""
    from .i18n import t
    if not res:
        return None, []
    warns = list(res.get("warnings") or [])
    out = []
    fps, tc = f"{cfg['fps']:g}", cfg["tc_start"]
    for tr in res.get("tracks") or []:
        kind, key, block = tr.get("kind"), str(tr.get("key") or ""), tr.get("block")
        origin = tr.get("origin")
        configured = False
        if key and is_source_block(block):
            block = _norm_block(block)
            tpl, dflt = load_template(key), _load_default(key)
            if origin == "default":
                if dflt is None:
                    _write(_path(key, True), block)
                configured = tpl is not None and block == tpl
            elif origin == "kept" and block != dflt:
                if block != tpl:
                    _write(_path(key), block)
                configured = True
            elif origin == "template":
                configured = True
        if tr.get("item") is False:
            warns.append(t("tc_no_generator", track=tr.get("name")))
        elif not configured:
            warns.append(t("tc_configure_" + ("mtc" if kind == "mtc" else "ltc"), track=tr.get("name"),
                           fps=fps, tc=tc))
        if kind == "mtc" and tr.get("midi_found") is False:
            warns.append(t("tc_midi_missing", dev=tr.get("midi_out")))
        out.append({"piste": tr.get("name"), "sortie": tr.get("label") if kind == "ltc" else tr.get("midi_out"),
                    "longueur_s": tr.get("length"), "generateur_regle": configured})
    if not out:
        return None, warns
    return {"pistes": out, "fps": cfg["fps"], "depart": tc, "tc_slot": cfg["slot"]}, warns


# --------------------------------------------------------------------------- #
# Concert (projet écrit par concert.py) : UNE piste par sorte, sur toute la durée du concert
# --------------------------------------------------------------------------- #
def concert_tracks(song_gens: list[dict], length: float, cfg: dict | None = None) -> tuple[list, list[str]]:
    """Pistes TIMECODE du projet concert (Nodes RPP) + avertissements.

    song_gens : pour chaque morceau, {nom de piste: (en-tête Node, [items Node])} (concert.SongSrc.gen).
    Le bloc SOURCE vient du réglage mémorisé (même fps + départ), sinon de l'item du 1er morceau qui en a
    un ; l'en-tête de piste (routage écrit par REAPER : sortie audio, MIDI, pas de master) du 1er morceau
    qui a la piste. Rien à recopier : pas de piste, avertissement."""
    from . import concert as C
    from .i18n import t
    cfg = cfg if cfg is not None else config()
    nodes, warns = [], []
    for kind, name, on in (("ltc", TRACK_LTC, cfg.get("ltc")), ("mtc", TRACK_MTC, cfg.get("mtc"))):
        if not on:
            continue
        head, item = None, None
        for g in song_gens:
            if name in g:
                h, items = g[name]
                head = head or h
                item = item or next((it for it in items if it.blocks("SOURCE")), None)
        tpl = load_template(template_key(kind, cfg))
        src = C.parse_rpp(tpl) if tpl else (item.blocks("SOURCE")[0].copy() if item is not None else None)
        if src is None:
            warns.append(t("tc_concert_missing", track=name))
            continue
        it = item.copy() if item is not None else C.Node("ITEM", [
            "POSITION 0", "SNAPOFFS 0", "LENGTH 1", "LOOP 0", "ALLTAKES 0", "FADEIN 1 0 0 1 0 0 0",
            "FADEOUT 1 0 0 1 0 0 0", "MUTE 0 0", "SEL 0", "IGUID x", "IID 1", "NAME Timecode",
            "VOLPAN 1 0 1 -1", "SOFFS 0", "PLAYRATE 1 1 0 -1 0 0.0025", "CHANMODE 0", "GUID x"])
        it.children = [c for c in it.children if not (isinstance(c, C.Node) and c.tag == "SOURCE")]
        it.children.append(src)
        for line in ("POSITION 0", f"LENGTH {round(float(length), 6)}", "LOOP 0", "SOFFS 0",
                     "FADEIN 1 0 0 1 0 0 0", "FADEOUT 1 0 0 1 0 0 0", "MUTE 0 0", f"IGUID {C.guid()}",
                     f"GUID {C.guid()}"):
            it.set_line(line.split(" ", 1)[0], line)
        it.drop("SEL")
        it.drop("IID")
        tr = C._track(name, None, [it], head)
        if head is None:                          # aucun morceau n'avait la piste : routage à faire
            tr.set_line("MAINSEND", "MAINSEND 0 0")
            warns.append(t("tc_concert_route", track=name))
        nodes.append(tr)
        if not tpl:
            warns.append(t("tc_configure_" + kind, track=name, fps=f"{cfg['fps']:g}", tc=cfg["tc_start"]))
    return nodes, warns
