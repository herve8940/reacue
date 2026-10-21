#!/bin/bash
# Double-clic pour installer ReaCue (macOS). / Double-click to install ReaCue (macOS).
cd "$(dirname "$0")" || exit 1
bash install/install_mac.sh
status=$?
echo
read -r -p "Appuie sur Entrée pour fermer / Press Enter to close… " _ || true
exit $status
