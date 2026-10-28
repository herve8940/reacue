#!/bin/bash
# Calibrate SongFormer CPU inference without changing the selected quality profile.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv-structure/bin/python ]; then
  echo "Installe d'abord l'analyse de structure / Install structure analysis first."
else
  .venv-structure/bin/python reacue_structure.py benchmark --save || echo "Étalonnage échoué / Calibration failed."
fi
read -r -p "Appuie sur Entrée pour fermer / Press Enter to close…" _answer || true
