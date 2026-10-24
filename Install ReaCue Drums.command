#!/bin/bash
# Double-clic : installe la transcription de batterie (ADTOF) pour ReaCue (macOS).
# Double-click: installs drum transcription (ADTOF) for ReaCue (macOS).
cd "$(dirname "$0")" || exit 1
read -r -p "Langue / Language [fr/en] (fr) : " L || true
bash install/install_drums_mac.sh "${L:-fr}"
status=$?
echo
read -r -p "Appuie sur Entrée pour fermer / Press Enter to close… " _ || true
exit $status
