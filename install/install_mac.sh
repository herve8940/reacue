#!/bin/bash
# Installation de ReaCue sur macOS / ReaCue installer for macOS.
# Lancé par « Install ReaCue.command » (double-clic) ; ou : bash install/install_mac.sh [fr|en]
# Relançable sans risque (idempotent). Internet n'est nécessaire que pendant l'installation.
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
t "== 1/4 Vérifications" "== 1/4 Checks"
[ "$(uname -s)" = "Darwin" ] || fail "ce script est pour macOS." "this script is for macOS."
if [ ! -d "$REAPER_DIR" ]; then
  fail "dossier REAPER introuvable ($REAPER_DIR). Lance REAPER une fois, ferme-le, puis relance l'installation." \
       "REAPER folder not found ($REAPER_DIR). Start REAPER once, close it, then run the installer again."
fi
echo "  REAPER : $REAPER_DIR"
echo "  ReaCue : $HERE"

echo
t "== 2/4 uv (gestionnaire Python d'Astral)" "== 2/4 uv (Astral's Python manager)"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  t "  installation de uv (https://astral.sh/uv)…" "  installing uv (https://astral.sh/uv)…"
  curl -LsSf https://astral.sh/uv/install.sh | sh || fail "installation de uv impossible (internet ?)." "could not install uv (internet?)."
  command -v uv >/dev/null 2>&1 || fail "uv introuvable après installation." "uv not found after installation."
fi
echo "  $(uv --version)"

echo
t "== 3/4 Environnement Python 3.12 (.venv) et dépendances" "== 3/4 Python 3.12 environment (.venv) and dependencies"
rm -rf .venv
uv venv .venv --python 3.12 || fail "création du .venv impossible." "could not create .venv."
# --no-build : paquets précompilés uniquement (pas de compilateur nécessaire)
uv pip install --no-build --python .venv/bin/python -r requirements.txt \
  || fail "installation des dépendances impossible (voir ci-dessus)." "could not install dependencies (see above)."
.venv/bin/python -c "import librosa, soundfile, mcp; print('  librosa', librosa.__version__, 'OK')" \
  || fail "dépendances incomplètes." "incomplete dependencies."
command -v say >/dev/null 2>&1 || t "  ! commande say absente : pas d'annonces vocales." "  ! say command missing: no spoken cues."

echo
t "== 4/4 Configuration de REAPER" "== 4/4 REAPER configuration"
REAPER_RESOURCE_PATH="$REAPER_DIR" .venv/bin/python install/reacue_setup.py install --lang "$L" --install-dir "$HERE" \
  --reaper-dir "$REAPER_DIR" ${REACUE_MCP:+--mcp "$REACUE_MCP"} || fail "configuration incomplète." "configuration incomplete."
