#!/bin/bash
# Paroles calées mot par mot pour ReaCue (alignement forcé wav2vec2, en local) — macOS.
# Word-by-word lyrics timing for ReaCue (wav2vec2 forced alignment, local) — macOS.
# Lancé par « Install ReaCue Words.command » ; ou :
#   bash install/install_words_mac.sh [fr|en]
# Langues des modèles : français et anglais (≈ 1,3 Go chacun) ; une seule : REACUE_WORDS_LANGS=fr (ou en).
# Environnement séparé .venv-words (n'abîme pas le .venv de ReaCue). Relançable sans risque.
# Internet nécessaire : environ 1 Go pour PyTorch (rien si la séparation de stems est déjà installée) + les modèles.
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
case "$(echo "${1:-fr}" | tr '[:upper:]' '[:lower:]')" in
  en*) L=en ;;
  *) L=fr ;;
esac
t() { if [ "$L" = en ]; then echo "$2"; else echo "$1"; fi; }
fail() { echo; t "ÉCHEC : $1" "FAILED: $2"; exit 1; }
LANGS="${REACUE_WORDS_LANGS:-fr,en}"

[ "$(uname -s)" = "Darwin" ] || fail "ce script est pour macOS." "this script is for macOS."
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
command -v uv >/dev/null 2>&1 || fail "uv introuvable : installe d'abord ReaCue (Install ReaCue.command)." \
                                      "uv not found: install ReaCue first (Install ReaCue.command)."
t "  Machine : $(uname -m) — paroles mot par mot (wav2vec2) dans $HERE/.venv-words" \
  "  Machine: $(uname -m) — word-by-word lyrics (wav2vec2) in $HERE/.venv-words"
t "  Licence : modèles wav2vec2 XLSR-53 de J. Grosman (Apache-2.0), base Meta XLSR-53 (Apache-2.0) ; téléchargés depuis Hugging Face. Détails : THIRD_PARTY_NOTICES.md" \
  "  Licence: J. Grosman's wav2vec2 XLSR-53 models (Apache-2.0), Meta XLSR-53 base (Apache-2.0); downloaded from Hugging Face. Details: THIRD_PARTY_NOTICES.md"
if [ ! -x .venv-words/bin/python ]; then
  uv venv .venv-words --python 3.12 || fail "création de .venv-words impossible." "could not create .venv-words."
fi
t "  installation de PyTorch et des dépendances (plusieurs minutes)…" \
  "  installing PyTorch and the dependencies (several minutes)…"
uv pip install --python .venv-words/bin/python --only-binary :all: -r requirements-words.txt \
  || fail "installation des dépendances impossible (voir ci-dessus)." "could not install the dependencies (see above)."
t "  téléchargement des modèles ($LANGS, environ 1,3 Go chacun) et test…" \
  "  downloading the models ($LANGS, about 1.3 GB each) and testing…"
.venv-words/bin/python reacue_words.py check --lang "$L" --langs "$LANGS" \
  || fail "le calage mot par mot ne fonctionne pas (voir ci-dessus)." "word-by-word timing does not work (see above)."
t "  Paroles mot par mot installées : utilisées automatiquement à la prochaine publication du prompteur (réglage « words_engine »)." \
  "  Word-by-word lyrics installed: used automatically at the next prompter update (“words_engine” setting)."
