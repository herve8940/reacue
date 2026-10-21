"""Lanceur de la CLI ReaCue (boutons REAPER), indépendant du dossier courant.

Utilisé sous Windows par ReaCue_run.lua (pythonw.exe : pas de fenêtre console) ; marche aussi ailleurs :
    <python du venv> reacue_cli.py prepare|publish [--resource-dir <ressources REAPER>]
Sans console (pythonw), la sortie standard et les erreurs vont dans <ReaCueMCP>/cli.log.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _redirect_output(argv):
    if sys.stdout is not None and sys.stderr is not None:
        return
    res = None
    if "--resource-dir" in argv:
        i = argv.index("--resource-dir")
        if i + 1 < len(argv):
            res = argv[i + 1]
    if res:
        os.environ["REAPER_RESOURCE_PATH"] = res
    from reacue_mcp.bridge import BRIDGE_DIR  # noqa: E402
    BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    f = open(BRIDGE_DIR / "cli.log", "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or f
    sys.stderr = sys.stderr or f


if __name__ == "__main__":
    _redirect_output(sys.argv[1:])
    from reacue_mcp.cli import main  # noqa: E402
    sys.exit(main())
