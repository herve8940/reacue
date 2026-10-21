#!/bin/bash
# Double-clic pour désinstaller ReaCue (macOS). / Double-click to uninstall ReaCue (macOS).
cd "$(dirname "$0")" || exit 1
bash install/uninstall_mac.sh
status=$?
echo
read -r -p "Appuie sur Entrée pour fermer / Press Enter to close… " _ || true
exit $status
