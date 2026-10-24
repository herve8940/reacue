#!/bin/bash
# Reconnaissance d'accords pour ReaCue (modèle entraîné, en local) — macOS / Chord recognition for ReaCue — macOS.
# Lancé par « Install ReaCue Chords.command » ; ou :
#   bash install/install_chords_mac.sh [fr|en]
# Environnement séparé .venv-chords + modèle figé dans chords/model (n'abîme pas le .venv de ReaCue).
# Internet nécessaire : environ 800 Mo (PyTorch, déjà en cache si les stems sont installés) + 60 Mo (modèle),
# 2 à 10 minutes. Relançable sans risque.
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
case "$(echo "${1:-fr}" | tr '[:upper:]' '[:lower:]')" in
  en*) L=en ;;
  *) L=fr ;;
esac
t() { if [ "$L" = en ]; then echo "$2"; else echo "$1"; fi; }
fail() { echo; t "ÉCHEC : $1" "FAILED: $2"; exit 1; }

# révision figée (même valeur que reacue_mcp/chord_model.py)
MODEL_REPO=music-x-lab/ISMIR2019-Large-Vocabulary-Chord-Recognition
MODEL_REV=481f4ce703f8822b99f4037e9104ba1760e21ea3

[ "$(uname -s)" = "Darwin" ] || fail "ce script est pour macOS." "this script is for macOS."
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
command -v uv >/dev/null 2>&1 || fail "uv introuvable : installe d'abord ReaCue (Install ReaCue.command)." \
                                      "uv not found: install ReaCue first (Install ReaCue.command)."
t "  Machine : $(uname -m) — reconnaissance d'accords dans $HERE/.venv-chords" \
  "  Machine: $(uname -m) — chord recognition in $HERE/.venv-chords"
t "  Licence : modèle de Junyan Jiang, Ke Chen, Wei Li et Gus Xia (ISMIR 2019, Music X Lab), code et poids" \
  "  Licence: model by Junyan Jiang, Ke Chen, Wei Li and Gus Xia (ISMIR 2019, Music X Lab), code and weights"
t "  sous licence MIT, téléchargés depuis GitHub. Détails : THIRD_PARTY_NOTICES.md" \
  "  under the MIT licence, downloaded from GitHub. Details: THIRD_PARTY_NOTICES.md"

fetch() {  # fetch <owner/repo> <révision> <dossier cible>
  local repo="$1" rev="$2" dest="$3"
  if [ -f "$dest/.reacue_rev" ] && [ "$(cat "$dest/.reacue_rev")" = "$rev" ]; then return 0; fi
  rm -rf "$dest" "$dest.tmp"
  mkdir -p "$dest.tmp"
  if ! curl -LsSf "https://codeload.github.com/$repo/tar.gz/$rev" | tar -xz -C "$dest.tmp" --strip-components 1; then
    # secours : git (révision exacte)
    rm -rf "$dest.tmp"
    command -v git >/dev/null 2>&1 || return 1
    git init -q "$dest.tmp" && git -C "$dest.tmp" fetch -q --depth 1 "https://github.com/$repo" "$rev" \
      && git -C "$dest.tmp" checkout -q FETCH_HEAD && rm -rf "$dest.tmp/.git" || { rm -rf "$dest.tmp"; return 1; }
  fi
  mv "$dest.tmp" "$dest"
  echo "$rev" > "$dest/.reacue_rev"
}
t "  téléchargement du modèle d'accords (version figée, environ 60 Mo)…" \
  "  downloading the chord model (pinned version, about 60 MB)…"
mkdir -p chords
fetch "$MODEL_REPO" "$MODEL_REV" chords/model || fail "téléchargement du modèle d'accords impossible." \
                                                    "could not download the chord model."

if [ ! -x .venv-chords/bin/python ]; then
  uv venv .venv-chords --python 3.12 || fail "création de .venv-chords impossible." "could not create .venv-chords."
fi
t "  installation de PyTorch et de librosa (plusieurs minutes la première fois)…" \
  "  installing PyTorch and librosa (several minutes the first time)…"
uv pip install --python .venv-chords/bin/python --only-binary :all: -r requirements-chords.txt \
  || fail "installation des dépendances impossible (voir ci-dessus)." "could not install the dependencies (see above)."
t "  test du modèle sur un audio synthétique…" "  testing the model on synthetic audio…"
.venv-chords/bin/python reacue_chords.py check --lang "$L" || fail "le modèle d'accords ne fonctionne pas (voir ci-dessus)." \
                                                                   "the chord model does not work (see above)."
t "  Reconnaissance d'accords installée : utilisée automatiquement pour le prompteur et la grille PDF (réglage « chords_engine »)." \
  "  Chord recognition installed: used automatically for the prompter and the PDF chart (“chords_engine” setting)."
