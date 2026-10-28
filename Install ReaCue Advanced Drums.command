#!/bin/bash
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
uv run --no-project --python 3.12 python install/install_drums_advanced.py
status=$?
read -r -p 'Appuie sur Entrée pour fermer / Press Enter to close… ' _ || true
exit "$status"
