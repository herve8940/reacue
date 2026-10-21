#!/bin/bash
# Désinstallation de ReaCue (macOS) / ReaCue uninstaller (macOS).
# Retire les scripts REAPER, la ligne de démarrage du pont, les actions et l'entrée Claude Desktop.
# Usage : bash install/uninstall_mac.sh [--purge]   (--purge : supprime aussi réglages et dernier morceau)
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
REAPER_DIR="${REAPER_RESOURCE_PATH:-$HOME/Library/Application Support/REAPER}"
PY="$HERE/.venv/bin/python"
command -v "$PY" >/dev/null 2>&1 || PY="$(command -v python3)"
"$PY" "$HERE/install/reacue_setup.py" uninstall --reaper-dir "$REAPER_DIR" "$@"
