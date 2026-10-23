#!/bin/bash
# Transcription de batterie pour ReaCue (ADTOF, en local) — macOS / Drum transcription for ReaCue — macOS.
# Lancé par « Install ReaCue Drums.command » ; ou :
#   bash install/install_drums_mac.sh [fr|en]
# Environnement séparé .venv-drums + code et poids figés dans drums/ (n'abîme pas le .venv de ReaCue).
# Internet nécessaire : environ 300 Mo (PyTorch, déjà en cache si Demucs est installé) + 16 Mo (ADTOF),
# 3 à 10 minutes. Relançable.
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
case "$(echo "${1:-fr}" | tr '[:upper:]' '[:lower:]')" in
  en*) L=en ;;
  *) L=fr ;;
esac
t() { if [ "$L" = en ]; then echo "$2"; else echo "$1"; fi; }
fail() { echo; t "ÉCHEC : $1" "FAILED: $2"; exit 1; }

# révision figée (même valeur que reacue_mcp/drums.py)
ADTOF_REV=85c192e78f716ea0b111cc8a5ee4a8f6a3a4f8a9

[ "$(uname -s)" = "Darwin" ] || fail "ce script est pour macOS." "this script is for macOS."
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
command -v uv >/dev/null 2>&1 || fail "uv introuvable : installe d'abord ReaCue (Install ReaCue.command)." \
                                      "uv not found: install ReaCue first (Install ReaCue.command)."
t "  Machine : $(uname -m) — transcription de batterie (ADTOF) dans $HERE/.venv-drums" \
  "  Machine: $(uname -m) — drum transcription (ADTOF) in $HERE/.venv-drums"

# Licences : accord explicite AVANT tout téléchargement (voir THIRD_PARTY_NOTICES.md).
# Installation non interactive : REACUE_DRUMS_ACCEPT=yes. Accord mémorisé dans drums/.licenses_accepted.
LIC_ID="adtof-weights-ccbyncsa4+adtof-pytorch-unstated/v1"
ACCEPT_FILE=drums/.licenses_accepted
if [ ! -f "$ACCEPT_FILE" ] || [ "$(head -n 1 "$ACCEPT_FILE")" != "$LIC_ID" ]; then
  echo
  t "  ┌─ Licences de la transcription de batterie ───────────────────────────────────" \
    "  ┌─ Drum transcription licences ────────────────────────────────────────────────"
  t "  │ ADTOF (M. Zehren et al.) : code et modèle CC BY-NC-SA 4.0 → USAGE NON COMMERCIAL UNIQUEMENT." \
    "  │ ADTOF (M. Zehren et al.): code and model CC BY-NC-SA 4.0 → NON-COMMERCIAL USE ONLY."
  t "  │ ADTOF-pytorch (X. Riley, portage PyTorch des poids d'ADTOF) : licence non précisée par son auteur." \
    "  │ ADTOF-pytorch (X. Riley, PyTorch port of the ADTOF weights): licence not stated by its author."
  t "  │ Le code et les poids sont téléchargés depuis GitHub ; tu es responsable du respect" \
    "  │ The code and weights are downloaded from GitHub; you are responsible for complying"
  t "  │ de leurs licences. Détails : THIRD_PARTY_NOTICES.md (ceci n'est pas un avis juridique)." \
    "  │ with their licences. Details: THIRD_PARTY_NOTICES.md (this is not legal advice)."
  t "  └──────────────────────────────────────────────────────────────────────────────" \
    "  └──────────────────────────────────────────────────────────────────────────────"
  WANT="$(t "J'accepte" "I accept")"
  if [ "${REACUE_DRUMS_ACCEPT:-}" = yes ]; then
    t "  Licences acceptées (REACUE_DRUMS_ACCEPT=yes)." "  Licences accepted (REACUE_DRUMS_ACCEPT=yes)."
  else
    ANS=""
    if [ -t 0 ]; then
      read -r -p "$(t "  Pour installer, tape exactement « J'accepte » (sinon Entrée) : " \
                      "  To install, type exactly “I accept” (otherwise Enter): ")" ANS || true
    fi
    Q="'"; ANS="${ANS//’/$Q}"     # apostrophe typographique acceptée / typographic apostrophe accepted
    if [ "$ANS" != "$WANT" ]; then
      t "  Licences non acceptées : rien n'a été installé ni téléchargé." \
        "  Licences not accepted: nothing was installed or downloaded."
      exit 3
    fi
  fi
  mkdir -p drums
  printf '%s\n%s\n' "$LIC_ID" "$(date '+%Y-%m-%d %H:%M:%S')" > "$ACCEPT_FILE"
fi

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
t "  téléchargement d'ADTOF-pytorch (code + poids, 16 Mo, version figée)…" \
  "  downloading ADTOF-pytorch (code + weights, 16 MB, pinned version)…"
mkdir -p drums
fetch xavriley/ADTOF-pytorch "$ADTOF_REV" drums/ADTOF-pytorch || fail "téléchargement d'ADTOF-pytorch impossible." \
                                                                     "could not download ADTOF-pytorch."

if [ ! -x .venv-drums/bin/python ]; then
  uv venv .venv-drums --python 3.12 || fail "création de .venv-drums impossible." "could not create .venv-drums."
fi
t "  installation de PyTorch et des dépendances (plusieurs minutes)…" \
  "  installing PyTorch and the dependencies (several minutes)…"
uv pip install --python .venv-drums/bin/python --only-binary :all: -r requirements-drums.txt \
  || fail "installation des dépendances impossible (voir ci-dessus)." "could not install the dependencies (see above)."
t "  test sur une batterie synthétique…" "  testing on synthetic drums…"
.venv-drums/bin/python reacue_drums.py check --lang "$L" || fail "ADTOF ne fonctionne pas (voir ci-dessus)." \
                                                              "ADTOF does not work (see above)."
t "  Transcription de batterie installée : utilisée automatiquement pour le prompteur (vue Batterie) quand un stem batterie existe." \
  "  Drum transcription installed: used automatically for the prompter (Drums view) when a drum stem exists."
