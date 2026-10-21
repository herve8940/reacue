#!/bin/bash
# Double-clic : installe la séparation de stems (Demucs) pour ReaCue (macOS).
# Double-click: installs stem separation (Demucs) for ReaCue (macOS).
cd "$(dirname "$0")" || exit 1
read -r -p "Langue / Language [fr/en] (fr) : " L || true
bash install/install_stems_mac.sh "${L:-fr}"
status=$?
echo
read -r -p "Appuie sur Entrée pour fermer / Press Enter to close… " _ || true
exit $status
