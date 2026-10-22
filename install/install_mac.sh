#!/bin/bash
# Installation de ReaCue sur macOS / ReaCue installer for macOS.
# Lancé par « Install ReaCue.command » (double-clic) ; ou : bash install/install_mac.sh [fr|en]
# Relançable sans risque (idempotent). Internet n'est nécessaire que pendant l'installation.
# REACUE_STEMS=yes|no : installer ou non la séparation de stems sans poser la question.
# REACUE_STRUCTURE=yes|no : idem pour l'analyse de structure (SongFormer).
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"

# ---------------------------------------------------------------- langue
LANG_CHOICE="${1:-}"
if [ -z "$LANG_CHOICE" ]; then
  echo "ReaCue — installation"
  read -r -p "Langue / Language [fr/en] (fr) : " LANG_CHOICE || true
fi
case "$(echo "${LANG_CHOICE:-fr}" | tr '[:upper:]' '[:lower:]')" in
  en*) L=en ;;
  *) L=fr ;;
esac

t() {  # t "texte français" "English text"
  if [ "$L" = en ]; then echo "$2"; else echo "$1"; fi
}
fail() {
  echo
  t "ÉCHEC : $1" "FAILED: $2"
  exit 1
}

REAPER_DIR="${REAPER_RESOURCE_PATH:-$HOME/Library/Application Support/REAPER}"

echo
t "== 1/6 Vérifications" "== 1/6 Checks"
[ "$(uname -s)" = "Darwin" ] || fail "ce script est pour macOS." "this script is for macOS."
if [ ! -d "$REAPER_DIR" ]; then
  fail "dossier REAPER introuvable ($REAPER_DIR). Lance REAPER une fois, ferme-le, puis relance l'installation." \
       "REAPER folder not found ($REAPER_DIR). Start REAPER once, close it, then run the installer again."
fi
echo "  REAPER : $REAPER_DIR"
echo "  ReaCue : $HERE"

echo
t "== 2/6 uv (gestionnaire Python d'Astral)" "== 2/6 uv (Astral's Python manager)"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  t "  installation de uv (https://astral.sh/uv)…" "  installing uv (https://astral.sh/uv)…"
  curl -LsSf https://astral.sh/uv/install.sh | sh || fail "installation de uv impossible (internet ?)." "could not install uv (internet?)."
  command -v uv >/dev/null 2>&1 || fail "uv introuvable après installation." "uv not found after installation."
fi
echo "  $(uv --version)"

echo
t "== 3/6 Environnement Python 3.12 (.venv) et dépendances" "== 3/6 Python 3.12 environment (.venv) and dependencies"
rm -rf .venv
uv venv .venv --python 3.12 || fail "création du .venv impossible." "could not create .venv."
# --no-build : paquets précompilés uniquement (pas de compilateur nécessaire)
uv pip install --no-build --python .venv/bin/python -r requirements.txt \
  || fail "installation des dépendances impossible (voir ci-dessus)." "could not install dependencies (see above)."
.venv/bin/python -c "import librosa, soundfile, mcp; print('  librosa', librosa.__version__, 'OK')" \
  || fail "dépendances incomplètes." "incomplete dependencies."
command -v say >/dev/null 2>&1 || t "  ! commande say absente : pas d'annonces vocales." "  ! say command missing: no spoken cues."

echo
t "== 4/6 Configuration de REAPER" "== 4/6 REAPER configuration"
REAPER_RESOURCE_PATH="$REAPER_DIR" .venv/bin/python install/reacue_setup.py install --lang "$L" --install-dir "$HERE" \
  --reaper-dir "$REAPER_DIR" ${REACUE_MCP:+--mcp "$REACUE_MCP"} || fail "configuration incomplète." "configuration incomplete."

echo
t "== 5/6 Séparation de stems (optionnel)" "== 5/6 Stem separation (optional)"
STEMS="${REACUE_STEMS:-ask}"
if [ "$STEMS" = ask ] && [ -x .venv-demucs/bin/python ]; then
  STEMS=yes     # déjà installée : mise à jour
fi
if [ "$STEMS" = ask ]; then
  t "  Sépare un MP3 en stems (voix, batterie, basse, guitare, piano, autres) dans REAPER, en local, sans abonnement." \
    "  Splits an MP3 into stems (vocals, drums, bass, guitar, piano, other) inside REAPER, locally, no subscription."
  read -r -p "$(t '  Installer la séparation de stems (Demucs, environ 1 Go à télécharger, 5 à 15 min) ? [o/N] ' \
                  '  Install stem separation (Demucs, about 1 GB to download, 5 to 15 min)? [y/N] ')" A || true
  case "$(echo "${A:-n}" | tr '[:upper:]' '[:lower:]')" in
    o*|y*) STEMS=yes ;;
    *) STEMS=no ;;
  esac
fi
if [ "$STEMS" = yes ]; then
  bash install/install_stems_mac.sh "$L" \
    || t "  ! séparation de stems non installée (le reste de ReaCue fonctionne). Réessaie avec « Install ReaCue Stems.command »." \
         "  ! stem separation not installed (the rest of ReaCue works). Try again with “Install ReaCue Stems.command”."
else
  t "  Non installée. Plus tard : double-clic sur « Install ReaCue Stems.command »." \
    "  Not installed. Later: double-click “Install ReaCue Stems.command”."
fi

echo
t "== 6/6 Analyse de structure (optionnel)" "== 6/6 Structure analysis (optional)"
STRUCT="${REACUE_STRUCTURE:-ask}"
if [ "$STRUCT" = ask ] && [ -x .venv-structure/bin/python ]; then
  STRUCT=yes    # déjà installée : mise à jour
fi
if [ "$STRUCT" = ask ]; then
  t "  Détecte couplets, refrains, ponts… avec SongFormer (IA, en local). Usage non commercial (licence des poids MuQ)." \
    "  Detects verses, choruses, bridges… with SongFormer (AI, local). Non-commercial use (MuQ weights licence)."
  read -r -p "$(t '  Installer l'"'"'analyse de structure (environ 3 Go à télécharger, 10 à 40 min, 8 Go de RAM conseillés) ? [o/N] ' \
                  '  Install structure analysis (about 3 GB to download, 10 to 40 min, 8 GB RAM recommended)? [y/N] ')" A || true
  case "$(echo "${A:-n}" | tr '[:upper:]' '[:lower:]')" in
    o*|y*) STRUCT=yes ;;
    *) STRUCT=no ;;
  esac
fi
if [ "$STRUCT" = yes ]; then
  bash install/install_structure_mac.sh "$L" \
    || t "  ! analyse de structure non installée (ReaCue garde sa détection). Réessaie avec « Install ReaCue Structure.command »." \
         "  ! structure analysis not installed (ReaCue keeps its own detection). Try again with “Install ReaCue Structure.command”."
else
  t "  Non installée. Plus tard : double-clic sur « Install ReaCue Structure.command »." \
    "  Not installed. Later: double-click “Install ReaCue Structure.command”."
fi
