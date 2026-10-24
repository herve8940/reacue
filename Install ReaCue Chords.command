#!/bin/bash
# Double-clic : installe la reconnaissance d'accords (modèle entraîné) pour ReaCue (macOS).
# Double-click: installs chord recognition (trained model) for ReaCue (macOS).
cd "$(dirname "$0")" || exit 1
read -r -p "Langue / Language [fr/en] (fr) : " L || true
bash install/install_chords_mac.sh "${L:-fr}"
status=$?
echo
read -r -p "Appuie sur Entrée pour fermer / Press Enter to close… " _ || true
exit $status
