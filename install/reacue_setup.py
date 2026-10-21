#!/usr/bin/env python3
"""Configuration de ReaCue dans REAPER (et Claude Desktop) : partie commune macOS / Windows.

Appelé par install_mac.sh / install_windows.ps1 (après création du .venv) et par les scripts de
désinstallation. Bibliothèque standard uniquement. Idempotent : relançable sans risque.

    python install/reacue_setup.py install   --lang fr|en [--install-dir D] [--reaper-dir R] [--mcp yes|no|ask]
    python install/reacue_setup.py uninstall [--lang fr|en] [--reaper-dir R] [--purge]
    python install/reacue_setup.py status    [--reaper-dir R]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

STARTUP_MARK = "-- ReaCue MCP"
STARTUP_LINE = 'dofile(reaper.GetResourcePath() .. "/Scripts/ReaCue/ReaCue_Bridge.lua") ' + STARTUP_MARK
SCRIPT_FILES = ("ReaCue_Bridge.lua", "ReaCue_run.lua", "ReaCue_Preparer.lua", "ReaCue_Republier_prompteur.lua",
                "ReaCue_stems.lua", "ReaCue_Separer_stems.lua", "ReaCue_concert_lib.lua", "ReaCue_qrcode.lua",
                "ReaCue_Concert.lua", "ReaCue_Morceau_suivant.lua", "ReaCue_Morceau_precedent.lua",
                "ReaCue.lua", "ReaCue_ui.lua", "ReaCue_tab_song.lua", "ReaCue_tab_concert.lua",
                "ReaCue_tab_stage.lua", "ReaCue_tab_settings.lua")
ACTIONS = (   # (identifiant de commande, fichier, nom FR, nom EN)
    ("REACUE_MAIN", "ReaCue.lua", "ReaCue", "ReaCue"),
    ("REACUE_PREPARE", "ReaCue_Preparer.lua", "ReaCue - Préparer le morceau", "ReaCue - Prepare the song"),
    ("REACUE_PUBLISH", "ReaCue_Republier_prompteur.lua", "ReaCue - Republier le prompteur",
     "ReaCue - Republish the prompter"),
    ("REACUE_STEMS", "ReaCue_Separer_stems.lua", "ReaCue - Séparer les stems", "ReaCue - Separate stems"),
    ("REACUE_CONCERT", "ReaCue_Concert.lua", "ReaCue - Concert", "ReaCue - Concert"),
    ("REACUE_NEXT_SONG", "ReaCue_Morceau_suivant.lua", "ReaCue - Morceau suivant", "ReaCue - Next song"),
    ("REACUE_PREV_SONG", "ReaCue_Morceau_precedent.lua", "ReaCue - Morceau précédent", "ReaCue - Previous song"),
)
SETTINGS_DEFAULTS = {
    "language": "fr", "announce_voice": None, "count_voice": None, "count_lang": "en",
    "count_in_bars": 2, "cue_lead_bars": 2, "voice_cues": True, "voice_count_in": True,
    "voice_count_each": True, "voice_volume": 0.8, "click_volume": 0.5, "click_to_master": True,
    "click_hw_output": None, "tempo_mode": "auto", "count_rate": 240, "stems_model": "htdemucs_6s",
    "projects_dir": None, "concert_dir": None,
}

MSG = {
    "reaper_dir": ("Dossier des ressources REAPER : {d}", "REAPER resource folder: {d}"),
    "no_reaper_dir": ("Dossier des ressources REAPER introuvable ({d}).\nLance REAPER une fois, ferme-le, puis "
                      "relance l'installation (ou indique le dossier avec --reaper-dir).",
                      "REAPER resource folder not found ({d}).\nStart REAPER once, close it, then run the "
                      "installer again (or give the folder with --reaper-dir)."),
    "scripts": ("Scripts copiés dans {d}", "Scripts copied to {d}"),
    "startup_added": ("Démarrage automatique du pont ajouté à {f}", "Bridge auto-start added to {f}"),
    "startup_present": ("Démarrage automatique du pont : déjà présent", "Bridge auto-start: already there"),
    "startup_removed": ("Démarrage automatique du pont retiré de {f}", "Bridge auto-start removed from {f}"),
    "settings_new": ("Réglages créés : {f}", "Settings created: {f}"),
    "settings_kept": ("Réglages existants conservés (langue : {lang}) : {f}",
                      "Existing settings kept (language: {lang}): {f}"),
    "install_path": ("Dossier d'installation mémorisé : {d}", "Install folder recorded: {d}"),
    "reaper_running": ("REAPER est ouvert : les actions ne peuvent pas être enregistrées automatiquement.",
                       "REAPER is running: the actions cannot be registered automatically."),
    "actions_manual": (
        "Dans REAPER : Actions > Show action list > New action > Load ReaScript…, puis choisis\n"
        "      {d}{sep}ReaCue_Preparer.lua, ReaCue_Republier_prompteur.lua, ReaCue_Separer_stems.lua,\n"
        "      ReaCue_Concert.lua, ReaCue_Morceau_suivant.lua et ReaCue_Morceau_precedent.lua\n"
        "      (ou ferme REAPER et relance l'installation).",
        "In REAPER: Actions > Show action list > New action > Load ReaScript…, then pick\n"
        "      {d}{sep}ReaCue_Preparer.lua, ReaCue_Republier_prompteur.lua, ReaCue_Separer_stems.lua,\n"
        "      ReaCue_Concert.lua, ReaCue_Morceau_suivant.lua and ReaCue_Morceau_precedent.lua\n"
        "      (or close REAPER and run the installer again)."),
    "action_added": ("Action enregistrée : « {name} »", "Action registered: “{name}”"),
    "action_present": ("Action déjà présente : « {name} »", "Action already there: “{name}”"),
    "action_other": ("Action déjà chargée depuis un autre emplacement (gardée) : {path}",
                     "Action already loaded from another location (kept): {path}"),
    "actions_removed": ("Actions ReaCue retirées de {f}", "ReaCue actions removed from {f}"),
    "ask_mcp": ("Déclarer ReaCue dans Claude Desktop (mode optionnel, pilotage par Claude) ? [o/N] ",
                "Register ReaCue in Claude Desktop (optional mode, control with Claude)? [y/N] "),
    "mcp_added": ("Serveur « reacue » déclaré dans {f} (sauvegarde : {b})",
                  "“reacue” server registered in {f} (backup: {b})"),
    "mcp_skipped": ("Claude Desktop : non configuré (relance avec --mcp yes pour le faire plus tard).",
                    "Claude Desktop: not configured (run again with --mcp yes to do it later)."),
    "mcp_removed": ("Serveur « reacue » retiré de {f}", "“reacue” server removed from {f}"),
    "mcp_bad_json": ("Configuration Claude illisible ({f}) : non modifiée.",
                     "Unreadable Claude configuration ({f}): left unchanged."),
    "web_found": ("Interface web de REAPER : active (port {port}). Adresse du prompteur : "
                  "http://<IP de cet ordinateur>:{port}/prompteur.html",
                  "REAPER web interface: enabled (port {port}). Prompter address: "
                  "http://<this computer's IP>:{port}/prompteur.html"),
    "web_missing": (
        "Interface web de REAPER : à activer une fois (nécessaire au prompteur) :\n"
        "      REAPER > Préférences (Options > Preferences) > Control/OSC/web > Add >\n"
        "      « Web browser interface », port 8080, OK.\n"
        "      Puis, sur les téléphones : http://<IP de cet ordinateur>:8080/prompteur.html",
        "REAPER web interface: enable it once (needed by the prompter):\n"
        "      REAPER > Options > Preferences > Control/OSC/web > Add >\n"
        "      “Web browser interface”, port 8080, OK.\n"
        "      Then, on the phones: http://<this computer's IP>:8080/prompteur.html"),
    "ip": ("Adresse(s) IP probable(s) de cet ordinateur : {ips}", "Likely IP address(es) of this computer: {ips}"),
    "done": ("Installation terminée. Redémarre REAPER : le pont se lance tout seul, et l'action « ReaCue »\n"
             "(fenêtre en 4 onglets : Morceau, Concert, Scène, Réglages) est dans la liste des actions — mets-la\n"
             "dans la barre d'outils. Restent aussi, pour les raccourcis : « ReaCue - Préparer le morceau »,\n"
             "« ReaCue - Republier le prompteur », « ReaCue - Séparer les stems », « ReaCue - Concert »\n"
             "(+ Morceau suivant / précédent).",
             "Installation complete. Restart REAPER: the bridge starts by itself, and the “ReaCue” action\n"
             "(4-tab window: Song, Concert, Stage, Settings) is in the action list — put it in the toolbar.\n"
             "Also there, for shortcuts: “ReaCue - Prepare the song”, “ReaCue - Republish the prompter”,\n"
             "“ReaCue - Separate stems”, “ReaCue - Concert” (+ Next / Previous song)."),
    "uninstalled": ("Désinstallation terminée. Données conservées (réglages, dernier morceau) : {d}\n"
                    "(--purge pour les supprimer). Le dossier de ReaCue lui-même peut être supprimé à la main.",
                    "Uninstall complete. Data kept (settings, last song): {d}\n"
                    "(--purge to delete it). The ReaCue folder itself can be deleted by hand."),
    "purged": ("Données supprimées : {d}", "Data deleted: {d}"),
    "removed": ("Supprimé : {p}", "Removed: {p}"),
    "stems_kept": ("Séparation de stems conservée : {d} (--purge pour la supprimer ; modèles Demucs dans le "
                   "cache de PyTorch : {c})",
                   "Stem separation kept: {d} (--purge to delete it; Demucs models in the PyTorch cache: {c})"),
}

LANG = "fr"


def msg(key: str, **kw) -> str:
    fr, en = MSG[key]
    return (en if LANG == "en" else fr).format(**kw)


def say(key: str, **kw):
    print("  " + msg(key, **kw), flush=True)


# --------------------------------------------------------------------------- #
# Emplacements
# --------------------------------------------------------------------------- #
def reaper_resource_dir(platform: str | None = None, env: dict | None = None, home: Path | None = None) -> Path:
    platform = platform or sys.platform
    env = os.environ if env is None else env
    home = home or Path.home()
    if env.get("REAPER_RESOURCE_PATH"):
        return Path(env["REAPER_RESOURCE_PATH"]).expanduser()
    if platform == "darwin":
        return home / "Library" / "Application Support" / "REAPER"
    if platform.startswith("win"):
        appdata = env.get("APPDATA") or str(home / "AppData" / "Roaming")
        return Path(appdata) / "REAPER"
    return home / ".config" / "REAPER"


def claude_config_path(platform: str | None = None, env: dict | None = None, home: Path | None = None) -> Path:
    platform = platform or sys.platform
    env = os.environ if env is None else env
    home = home or Path.home()
    if platform == "darwin":
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if platform.startswith("win"):
        appdata = env.get("APPDATA") or str(home / "AppData" / "Roaming")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    return home / ".config" / "Claude" / "claude_desktop_config.json"


def venv_python(install_dir: Path, platform: str | None = None, windowed: bool = False) -> Path:
    platform = platform or sys.platform
    if platform.startswith("win"):
        return Path(install_dir) / ".venv" / "Scripts" / ("pythonw.exe" if windowed else "python.exe")
    return Path(install_dir) / ".venv" / "bin" / "python"


def torch_hub_dir(env: dict | None = None, home: Path | None = None) -> Path:
    """Cache des modèles Demucs (PyTorch Hub) : $TORCH_HOME/hub, sinon ~/.cache/torch/hub."""
    env = os.environ if env is None else env
    home = home or Path.home()
    if env.get("TORCH_HOME"):
        return Path(env["TORCH_HOME"]) / "hub"
    return Path(env.get("XDG_CACHE_HOME") or home / ".cache") / "torch" / "hub"


def stems_python(install_dir: Path, platform: str | None = None, windowed: bool = False) -> Path:
    platform = platform or sys.platform
    if platform.startswith("win"):
        return Path(install_dir) / ".venv-demucs" / "Scripts" / ("pythonw.exe" if windowed else "python.exe")
    return Path(install_dir) / ".venv-demucs" / "bin" / "python"


def reaper_running(platform: str | None = None, run=subprocess.run) -> bool:
    platform = platform or sys.platform
    try:
        if platform.startswith("win"):
            r = run(["tasklist", "/FI", "IMAGENAME eq reaper.exe", "/NH"], capture_output=True, text=True,
                    creationflags=0x08000000)
            return "reaper.exe" in (r.stdout or "").lower()
        r = run(["pgrep", "-ix", "reaper(64)?"], capture_output=True, text=True)
        return r.returncode == 0 and bool((r.stdout or "").strip())
    except (OSError, subprocess.SubprocessError):
        return False


# --------------------------------------------------------------------------- #
# Fichiers texte (fins de ligne conservées)
# --------------------------------------------------------------------------- #
def _read_text(p: Path) -> tuple[str, str]:
    raw = p.read_bytes() if p.exists() else b""
    text = raw.decode("utf-8", errors="surrogateescape")
    nl = "\r\n" if "\r\n" in text else ("\r\n" if (not text and sys.platform.startswith("win")) else "\n")
    return text, nl


def _write_text(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".reacue-tmp")
    tmp.write_bytes(text.encode("utf-8", errors="surrogateescape"))
    os.replace(tmp, p)


def _backup(p: Path) -> Path | None:
    if not p.exists():
        return None
    b = p.with_name(p.name + ".bak-reacue")
    shutil.copy2(p, b)
    return b


# --------------------------------------------------------------------------- #
# Scripts REAPER
# --------------------------------------------------------------------------- #
def copy_scripts(src: Path, scripts_dir: Path) -> list[Path]:
    scripts_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for name in SCRIPT_FILES:
        shutil.copyfile(src / name, scripts_dir / name)
        out.append(scripts_dir / name)
    return out


def add_startup(startup: Path) -> bool:
    """Ajoute le lancement du pont à __startup.lua ; False s'il y était déjà."""
    text, nl = _read_text(startup)
    if STARTUP_MARK.strip("- ") in text and "ReaCue_Bridge.lua" in text:
        return False
    if text and not text.endswith(("\n", "\r")):
        text += nl
    _write_text(startup, text + STARTUP_LINE + nl)
    return True


def remove_startup(startup: Path) -> bool:
    if not startup.exists():
        return False
    text, nl = _read_text(startup)
    lines = text.splitlines(keepends=True)
    keep = [ln for ln in lines if not ("ReaCue_Bridge.lua" in ln and "ReaCue" in ln)]
    if len(keep) == len(lines):
        return False
    _write_text(startup, "".join(keep))
    return True


_SCR = re.compile(r'^SCR\s+\d+\s+\d+\s+(\S+)\s+"([^"]*)"\s+(.+?)\s*$')


def kb_line(cmd_id: str, name: str, rel_path: str) -> str:
    # section 0 = actions principales (« Main ») ; chemin relatif au dossier Scripts de REAPER
    return f'SCR 4 0 {cmd_id} "Custom: {name}" "{rel_path}"'


def register_actions(kb: Path, lang: str) -> list[tuple[str, str]]:
    """Enregistre les deux actions dans reaper-kb.ini (REAPER fermé). Renvoie [(statut, détail)] :
    statut = added | present | other (déjà chargée depuis un autre dossier : gardée telle quelle)."""
    text, nl = _read_text(kb)
    lines = text.splitlines()
    report = []
    for cmd_id, fname, fr, en in ACTIONS:
        name = en if lang == "en" else fr
        want = kb_line(cmd_id, name, "ReaCue/" + fname)
        idx = [i for i, ln in enumerate(lines) if (m := _SCR.match(ln)) and m.group(1) == cmd_id]
        if idx:
            if lines[idx[0]] == want and len(idx) == 1:
                report.append(("present", name))
                continue
            for i in reversed(idx[1:]):
                del lines[i]
            lines[idx[0]] = want
            report.append(("added", name))
            continue
        other = [m.group(3).strip('"') for ln in lines if (m := _SCR.match(ln))
                 and re.search(re.escape(fname) + r'"?$', ln)]
        if other:
            report.append(("other", other[0]))
            continue
        lines.append(want)
        report.append(("added", name))
    _write_text(kb, nl.join(lines) + nl)
    return report


def unregister_actions(kb: Path) -> bool:
    if not kb.exists():
        return False
    text, nl = _read_text(kb)
    lines = text.splitlines()
    ids = {a[0] for a in ACTIONS}
    keep = [ln for ln in lines if not ((m := _SCR.match(ln)) and m.group(1) in ids)]
    if len(keep) == len(lines):
        return False
    _write_text(kb, nl.join(keep) + (nl if keep else ""))
    return True


# --------------------------------------------------------------------------- #
# Réglages, chemin d'installation
# --------------------------------------------------------------------------- #
def write_settings(path: Path, lang: str) -> bool:
    """Crée reacue_settings.json (défauts) ou met seulement à jour la langue. True si créé."""
    if path.exists():
        try:
            d = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(d, dict):
                raise ValueError
        except (OSError, ValueError):
            _backup(path)
            d = dict(SETTINGS_DEFAULTS)
        d["language"] = lang
        for k, v in SETTINGS_DEFAULTS.items():
            d.setdefault(k, v)
        _write_text(path, json.dumps(d, indent=2, ensure_ascii=False) + "\n")
        return False
    d = dict(SETTINGS_DEFAULTS, language=lang)
    _write_text(path, json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    return True


def write_install_path(path: Path, install_dir: Path):
    _write_text(path, str(install_dir) + "\n")


# --------------------------------------------------------------------------- #
# Claude Desktop
# --------------------------------------------------------------------------- #
def mcp_entry(install_dir: Path, platform: str | None = None, reaper_dir: Path | None = None,
              default_reaper_dir: Path | None = None) -> dict:
    e = {"command": str(venv_python(install_dir, platform)), "args": [str(Path(install_dir) / "run_server.py")]}
    if reaper_dir and default_reaper_dir and Path(reaper_dir) != Path(default_reaper_dir):
        e["env"] = {"REAPER_RESOURCE_PATH": str(reaper_dir)}       # REAPER portable / non standard
    return e


def add_mcp(cfg_path: Path, entry: dict) -> Path | None:
    """Ajoute/remplace mcpServers.reacue ; renvoie la sauvegarde. ValueError si JSON illisible."""
    cfg = {}
    if cfg_path.exists() and cfg_path.read_text(encoding="utf-8-sig").strip():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
        if not isinstance(cfg, dict):
            raise ValueError("not an object")
    b = _backup(cfg_path)
    cfg.setdefault("mcpServers", {})["reacue"] = entry
    _write_text(cfg_path, json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    return b


def remove_mcp(cfg_path: Path) -> bool:
    if not cfg_path.exists():
        return False
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig") or "{}")
    except ValueError:
        return False
    if not isinstance(cfg, dict) or "reacue" not in (cfg.get("mcpServers") or {}):
        return False
    _backup(cfg_path)
    del cfg["mcpServers"]["reacue"]
    _write_text(cfg_path, json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    return True


# --------------------------------------------------------------------------- #
# Interface web de REAPER (lecture seule)
# --------------------------------------------------------------------------- #
def web_ports(reaper_ini: Path) -> list[int]:
    """Ports des interfaces web déjà configurées (lignes csurf_N=HTTP … de reaper.ini)."""
    try:
        text = reaper_ini.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out = []
    for m in re.finditer(r"^csurf_\d+=HTTP\s+\S+\s+(\d+)", text, re.M):
        port = int(m.group(1))
        if 0 < port < 65536:
            out.append(port)
    return out


def local_ips() -> list[str]:
    import socket
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.0.2.1", 9))           # aucune donnée envoyée : choix de l'interface par défaut
        ips.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    return [ip for ip in dict.fromkeys(ips) if not ip.startswith("127.")]


# --------------------------------------------------------------------------- #
# Commandes
# --------------------------------------------------------------------------- #
def _ask_yes(prompt: str) -> bool:
    try:
        ans = input("  " + prompt).strip().lower()
    except EOFError:
        return False
    return ans[:1] in ("o", "y")


def do_install(args) -> int:
    install_dir = Path(args.install_dir or ROOT).resolve()
    rdir = Path(args.reaper_dir).expanduser() if args.reaper_dir else reaper_resource_dir()
    say("reaper_dir", d=rdir)
    if not rdir.is_dir():
        say("no_reaper_dir", d=rdir)
        return 2
    scripts = rdir / "Scripts" / "ReaCue"
    copy_scripts(install_dir / "reaper", scripts)
    say("scripts", d=scripts)
    startup = rdir / "Scripts" / "__startup.lua"
    say("startup_added", f=startup) if add_startup(startup) else say("startup_present")
    data = rdir / "ReaCueMCP"
    data.mkdir(parents=True, exist_ok=True)
    sp = data / "reacue_settings.json"
    if write_settings(sp, LANG):
        say("settings_new", f=sp)
    else:
        say("settings_kept", lang=LANG, f=sp)
    write_install_path(data / "reacue_install.txt", install_dir)
    say("install_path", d=install_dir)
    # actions
    kb = rdir / "reaper-kb.ini"
    running = reaper_running() if args.reaper_running is None else args.reaper_running == "yes"
    if running:
        say("reaper_running")
        say("actions_manual", d=scripts, sep=os.sep)
    else:
        _backup(kb)
        for status, detail in register_actions(kb, LANG):
            say({"added": "action_added", "present": "action_present"}.get(status, "action_other"),
                name=detail, path=detail)
    # Claude Desktop
    want = args.mcp
    if want == "ask":
        want = "yes" if _ask_yes(msg("ask_mcp")) else "no"
    if want == "yes":
        cfg = claude_config_path()
        try:
            b = add_mcp(cfg, mcp_entry(install_dir, reaper_dir=rdir, default_reaper_dir=reaper_resource_dir(
                env={k: v for k, v in os.environ.items() if k != "REAPER_RESOURCE_PATH"})))
            say("mcp_added", f=cfg, b=b or "-")
        except ValueError:
            say("mcp_bad_json", f=cfg)
    else:
        say("mcp_skipped")
    # interface web
    ports = web_ports(rdir / "reaper.ini")
    say("web_found", port=ports[0]) if ports else say("web_missing")
    ips = local_ips()
    if ips:
        say("ip", ips=", ".join(ips))
    print()
    print(msg("done"))
    return 0


def do_uninstall(args) -> int:
    rdir = Path(args.reaper_dir).expanduser() if args.reaper_dir else reaper_resource_dir()
    scripts = rdir / "Scripts" / "ReaCue"
    if scripts.exists():
        shutil.rmtree(scripts, ignore_errors=True)
        say("removed", p=scripts)
    startup = rdir / "Scripts" / "__startup.lua"
    if remove_startup(startup):
        say("startup_removed", f=startup)
    kb = rdir / "reaper-kb.ini"
    running = reaper_running() if args.reaper_running is None else args.reaper_running == "yes"
    if running:
        say("reaper_running")
    elif kb.exists():
        _backup(kb)
        if unregister_actions(kb):
            say("actions_removed", f=kb)
    cfg = claude_config_path()
    if remove_mcp(cfg):
        say("mcp_removed", f=cfg)
    stems_env = None
    try:
        inst = (rdir / "ReaCueMCP" / "reacue_install.txt").read_text(encoding="utf-8").strip()
        if inst and (Path(inst) / ".venv-demucs").is_dir():
            stems_env = Path(inst) / ".venv-demucs"
    except OSError:
        pass
    for p in (rdir / "ReaCueMCP" / "reacue_install.txt", rdir / "reaper_www_root" / "prompteur.html",
              rdir / "reaper_www_root" / "reacue_song.json"):
        if p.exists():
            p.unlink()
            say("removed", p=p)
    data = rdir / "ReaCueMCP"
    if args.purge and data.exists():
        shutil.rmtree(data, ignore_errors=True)
        say("purged", d=data)
    if stems_env is not None:
        if args.purge:
            shutil.rmtree(stems_env, ignore_errors=True)
            say("purged", d=stems_env)
        else:
            say("stems_kept", d=stems_env, c=torch_hub_dir())
    print()
    print(msg("uninstalled", d=data))
    return 0


def do_status(args) -> int:
    rdir = Path(args.reaper_dir).expanduser() if args.reaper_dir else reaper_resource_dir()
    data = rdir / "ReaCueMCP"
    info = {
        "reaper_dir": str(rdir), "reaper_dir_exists": rdir.is_dir(),
        "scripts": (rdir / "Scripts" / "ReaCue" / "ReaCue_Bridge.lua").exists(),
        "startup": "ReaCue_Bridge.lua" in _read_text(rdir / "Scripts" / "__startup.lua")[0],
        "install_dir": (data / "reacue_install.txt").read_text(encoding="utf-8").strip()
        if (data / "reacue_install.txt").exists() else None,
        "heartbeat_age_s": round(time.time() - (data / "heartbeat.txt").stat().st_mtime, 1)
        if (data / "heartbeat.txt").exists() else None,
        "web_ports": web_ports(rdir / "reaper.ini"),
    }
    info["stems"] = bool(info["install_dir"]) and stems_python(Path(info["install_dir"])).exists()
    print(json.dumps(info, indent=2, ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    global LANG
    ap = argparse.ArgumentParser(prog="reacue_setup")
    ap.add_argument("cmd", choices=["install", "uninstall", "status"])
    ap.add_argument("--lang", default=None, choices=["fr", "en"])
    ap.add_argument("--install-dir")
    ap.add_argument("--reaper-dir")
    ap.add_argument("--mcp", default="ask", choices=["yes", "no", "ask"])
    ap.add_argument("--reaper-running", choices=["yes", "no"], help=argparse.SUPPRESS)   # tests
    ap.add_argument("--purge", action="store_true")
    args = ap.parse_args(argv)
    if args.lang is None:
        try:
            rdir = Path(args.reaper_dir).expanduser() if args.reaper_dir else reaper_resource_dir()
            args.lang = json.loads((rdir / "ReaCueMCP" / "reacue_settings.json").read_text(
                encoding="utf-8-sig")).get("language", "fr")
        except (OSError, ValueError, AttributeError):
            args.lang = "fr"
    LANG = args.lang if args.lang in ("fr", "en") else "fr"
    try:
        sys.stdout.reconfigure(encoding="utf-8")       # accents dans la console Windows
    except (AttributeError, ValueError):
        pass
    return {"install": do_install, "uninstall": do_uninstall, "status": do_status}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
