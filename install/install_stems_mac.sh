#!/bin/bash
# Séparation de stems pour ReaCue (Demucs, en local) — macOS / Stem separation for ReaCue — macOS.
# Lancé par install_mac.sh (si tu réponds oui) ou par « Install ReaCue Stems.command » ; ou :
#   bash install/install_stems_mac.sh [fr|en]
# Environnement séparé .venv-demucs (n'abîme pas le .venv de ReaCue). Relançable sans risque.
# Internet nécessaire : environ 1 Go (PyTorch + 2 modèles Demucs), 5 à 15 minutes.
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
case "$(echo "${1:-fr}" | tr '[:upper:]' '[:lower:]')" in
  en*) L=en ;;
  *) L=fr ;;
esac
t() { if [ "$L" = en ]; then echo "$2"; else echo "$1"; fi; }
fail() { echo; t "ÉCHEC : $1" "FAILED: $2"; exit 1; }

[ "$(uname -s)" = "Darwin" ] || fail "ce script est pour macOS." "this script is for macOS."
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
command -v uv >/dev/null 2>&1 || fail "uv introuvable : installe d'abord ReaCue (Install ReaCue.command)." \
                                      "uv not found: install ReaCue first (Install ReaCue.command)."
t "  Machine : $(uname -m) — séparation de stems (Demucs) dans $HERE/.venv-demucs" \
  "  Machine: $(uname -m) — stem separation (Demucs) in $HERE/.venv-demucs"

t "  Licence : Demucs (Meta / A. Défossez) est sous licence MIT ; ses modèles sont téléchargés depuis Meta. Détails : THIRD_PARTY_NOTICES.md" \
  "  Licence: Demucs (Meta / A. Défossez) is MIT-licensed; its models are downloaded from Meta. Details: THIRD_PARTY_NOTICES.md"
if [ ! -x .venv-demucs/bin/python ]; then
  uv venv .venv-demucs --python 3.12 || fail "création de .venv-demucs impossible." "could not create .venv-demucs."
fi
t "  téléchargement et installation de PyTorch et Demucs (plusieurs minutes)…" \
  "  downloading and installing PyTorch and Demucs (several minutes)…"
uv pip install --python .venv-demucs/bin/python --only-binary :all: --no-binary demucs -r requirements-stems.txt \
  || fail "installation de Demucs impossible (voir ci-dessus)." "could not install Demucs (see above)."
t "  téléchargement des modèles et test de vitesse…" "  downloading the models and measuring the speed…"
.venv-demucs/bin/python reacue_stems.py check --lang "$L" || fail "Demucs ne fonctionne pas (voir ci-dessus)." \
                                                                  "Demucs does not work (see above)."
t "  Séparation de stems installée : action « ReaCue - Séparer les stems » dans REAPER." \
  "  Stem separation installed: “ReaCue - Separate stems” action in REAPER."
