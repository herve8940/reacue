"""ReaCue sans Claude : lancé par les boutons « ReaCue - Préparer le morceau » / « ReaCue - Republier
le prompteur » de REAPER (ou à la main).

    <python du venv> -m reacue_mcp.cli prepare      # analyse + régions, click, annonces, prompteur
    <python du venv> -m reacue_mcp.cli publish      # republie seulement le prompteur
    <python du venv> -m reacue_mcp.cli concert --setlist "<Concerts>/Concert.setlist.json"
    <python du venv> -m reacue_mcp.cli concert --name "Concert" --songs "Song A" "Song B"
    (Windows : reacue_cli.py, à la racine, fait la même chose sans dépendre du dossier courant)

Même code que le serveur MCP (mêmes réglages, même mémoire du dernier morceau) : on peut ensuite
continuer avec Claude sans rien perdre. L'avancement est écrit dans
<ressources REAPER>/ReaCueMCP/cli_status.json, lu par le script Lua qui affiche la progression.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import traceback
from pathlib import Path


def _dirs():
    from .bridge import BRIDGE_DIR
    return BRIDGE_DIR, BRIDGE_DIR / "cli_status.json", BRIDGE_DIR / "cli.log"


def _status(state: str, **kw):
    _, status, _ = _dirs()
    status.parent.mkdir(parents=True, exist_ok=True)
    d = {"state": state, "time": time.time(), "pid": os.getpid(), **kw}
    tmp = status.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, status)


def _message(res: dict, title: str) -> str:
    """Résumé lisible pour la fenêtre de REAPER (langue du réglage `language`)."""
    from .i18n import t, is_bpm_from_name_warning, get_lang
    if res.get("error"):
        return t("cli_error", e=res["error"])
    lines = [title, ""]
    if "bpm" in res:
        lines.append(t("cli_tempo", bpm=res["bpm"], sig=res.get("signature", ""), bars=res.get("bars", "?"))
                     + (t("cli_alt", alt=res["alt_bpm"]) if res.get("alt_bpm") else ""))
    secs = res.get("sections") or []
    se = res.get("structure_engine") or {}
    if se.get("message"):
        lines.append(se["message"])
    if secs:
        lines.append("")
        lines.append(t("cli_structure"))
        for s in secs:
            n = s.get("length_bars")
            lines.append(f"  {s.get('bars', ''):>9}  {s['name']}" + (f"  ({n})" if n else ""))
    p = res.get("prompteur") or {}
    if p:
        bits = [t(k) for k, v in (("cli_chords", p.get("chords")), ("cli_drums", p.get("drums"))) if v]
        if p.get("lyrics"):
            bits.append(t("cli_lyrics", n=p["lyrics"]))
        lines.append("")
        sep = ": " if get_lang() == "en" else " : "
        lines.append(t("cli_published") + (sep + ", ".join(bits) if bits else ""))
        if p.get("warning"):
            lines.append("  ! " + p["warning"])
    warns = [w for w in res.get("warnings") or [] if not is_bpm_from_name_warning(w)]
    if warns:
        lines.append("")
        lines.extend("! " + w for w in warns[:6])
    return "\n".join(lines)


async def _run(cmd: str, args) -> dict:
    from . import server          # import tardif : librosa est long à charger
    from .i18n import t
    if cmd == "prepare":
        # morceau déjà préparé (mêmes pistes) : on reconstruit en gardant la structure validée
        if not args.reanalyse and await _same_song(server):
            # régions modifiées à la main dans REAPER : reprises comme structure (update_options)
            res = await server.update_options(**_changed_settings(server))
            res["_title"] = t("cli_from_regions") if res.get("structure_from_regions") else t("cli_rebuilt")
            return res
        kw = {}
        if args.bpm:
            kw["bpm_hint"] = args.bpm
        if args.count_in is not None:
            kw["count_in_bars"] = args.count_in
        return await server.prepare_song(**kw)
    if cmd == "publish":
        return await server.set_sections([{"prompteur_seul": True}])
    raise ValueError(t("cli_unknown", cmd=cmd))


def _changed_settings(server) -> dict:
    """Réglages à réappliquer au morceau déjà préparé : seulement ceux de reacue_settings.json qui ont
    changé depuis la dernière préparation (les options réglées entre-temps avec Claude sont gardées ;
    session d'une ancienne version, sans instantané des réglages : rien n'est réappliqué)."""
    import inspect
    from .settings import option_defaults
    try:
        before = json.loads(server.SESSION.read_text(encoding="utf-8")).get("settings")
    except (OSError, ValueError):
        return {}
    if not isinstance(before, dict):
        return {}
    allowed = set(inspect.signature(server.update_options).parameters)
    return {k: v for k, v in option_defaults().items()
            if k in allowed and v is not None and before.get(k) != v}


async def _same_song(server) -> bool:
    """Les pistes audio du projet ouvert sont-elles celles du dernier morceau préparé ?"""
    try:
        _, item, _, items = server._load()
    except Exception:
        return False
    return await server._same_song(item, items)


def _concert_message(res) -> str:
    from .i18n import t
    lines = [t("concert_built", name=res.name), ""]
    for d in res.songs:
        lines.append(t("concert_line", n=d["n"], title=d["title"], bpm=d["bpm"], bars=d["bars"]))
    total = res.songs[-1]["stop"] if res.songs else 0
    lines += ["", t("concert_duration", m=int(total // 60), s=int(total % 60)), t("concert_extras_running")]
    if res.warnings:
        lines.append("")
        lines.extend("! " + w for w in res.warnings[:6])
    return "\n".join(lines)


def _log_exc(log):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + traceback.format_exc() + "\n")


def _concert(args, log) -> int:
    """Construit (ou reconstruit) un concert, puis enrichit son prompteur (accords, paroles, batterie)."""
    from . import concert as conc
    from .i18n import t
    if args.setlist:
        res = conc.build_from_setlist(args.setlist)
    elif args.name and args.songs:
        res = conc.build_concert(args.name, args.songs, args.gap if args.gap is not None else 4.0)
    else:
        raise ValueError(t("concert_args"))
    _status("done", cmd="concert", message=_concert_message(res), rpp=str(res.rpp))
    try:
        conc.extras_from_setlist(res.setlist)
    except Exception:
        _log_exc(log)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="reacue")
    ap.add_argument("cmd", choices=["prepare", "publish", "concert", "concert-extras"])
    ap.add_argument("--bpm", type=float, help="tempo approximatif (corrige double/moitié)")
    ap.add_argument("--count-in", type=int, help="mesures de count-in (défaut : réglages, 2)")
    ap.add_argument("--reanalyse", action="store_true",
                    help="refaire l'analyse même si le morceau est déjà préparé (structure remplacée)")
    ap.add_argument("--resource-dir", help="dossier des ressources REAPER (transmis par le script Lua)")
    ap.add_argument("--setlist", help="concert : fichier <nom>.setlist.json")
    ap.add_argument("--name", help="concert : nom du concert")
    ap.add_argument("--songs", nargs="+", help="concert : morceaux dans l'ordre (noms de projets ou chemins .RPP)")
    ap.add_argument("--gap", type=float, help="concert : blanc minimum entre deux morceaux (s)")
    args = ap.parse_args(argv)
    if args.resource_dir:
        # avant tout import de bridge : BRIDGE_DIR en dépend (REAPER portable, chemin non standard)
        os.environ["REAPER_RESOURCE_PATH"] = str(Path(args.resource_dir))
    from .i18n import t, use_settings_lang
    use_settings_lang()
    _, _, log = _dirs()
    if args.cmd == "concert-extras":           # arrière-plan, sans fenêtre de progression
        from . import concert as conc
        try:
            conc.extras_from_setlist(args.setlist)
            return 0
        except Exception:
            _log_exc(log)
            return 1
    if args.cmd == "concert":
        _status("running", cmd="concert", step=t("cli_concert_running"))
        try:
            return _concert(args, log)
        except Exception as e:
            _log_exc(log)
            _status("error", cmd="concert", message=t("cli_error_log", e=e, log=log))
            return 1
    titles = {"prepare": t("cli_prepared"), "publish": t("cli_published_title")}
    _status("running", cmd=args.cmd, step=t("cli_running"))
    from . import structure
    structure.PROGRESS = lambda msg: _status("running", cmd=args.cmd, step=msg)
    try:
        res = asyncio.run(_run(args.cmd, args))
        ok = not res.get("error")
        _status("done" if ok else "error", cmd=args.cmd,
                message=_message(res, res.pop("_title", None) or titles[args.cmd]))
        return 0 if ok else 1
    except Exception as e:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + traceback.format_exc() + "\n")
        _status("error", cmd=args.cmd, message=t("cli_error_log", e=e, log=log))
        return 1


if __name__ == "__main__":
    sys.exit(main())
