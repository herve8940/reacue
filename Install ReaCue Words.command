#!/bin/bash
# Double-clic : installe les paroles calées mot par mot (wav2vec2) et les paroles automatiques (Whisper) pour ReaCue (macOS).
# Double-click: installs word-by-word lyrics timing (wav2vec2) and automatic lyrics (Whisper) for ReaCue (macOS).
cd "$(dirname "$0")" || exit 1
read -r -p "Langue / Language [fr/en] (fr) : " L || true
bash install/install_words_mac.sh "${L:-fr}"
status=$?
echo
read -r -p "Appuie sur Entrée pour fermer / Press Enter to close… " _ || true
exit $status
