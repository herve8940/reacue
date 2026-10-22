#!/bin/bash
# Analyse de structure pour ReaCue (SongFormer, en local) — macOS / Structure analysis for ReaCue — macOS.
# Lancé par install_mac.sh (si tu réponds oui) ou par « Install ReaCue Structure.command » ; ou :
#   bash install/install_structure_mac.sh [fr|en]
# Environnement séparé .venv-structure + sources figées dans structure/ (n'abîme pas le .venv de ReaCue).
# Internet nécessaire : environ 3 Go (PyTorch, SongFormer, MuQ, MusicFM), 10 à 40 minutes. Relançable.
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
case "$(echo "${1:-fr}" | tr '[:upper:]' '[:lower:]')" in
  en*) L=en ;;
  *) L=fr ;;
esac
t() { if [ "$L" = en ]; then echo "$2"; else echo "$1"; fi; }
fail() { echo; t "ÉCHEC : $1" "FAILED: $2"; exit 1; }

# révisions figées (mêmes valeurs que reacue_mcp/structure.py)
SONGFORMER_REV=139b2aa3b14bd1c6d961d0994e9fc975f1ef7fd5
MUQ_REV=28847ea50cd31ac4b8b6a7dacc051ad7d1c7606a
MUSICFM_REV=b83ebedb401bcef639b26b05c0c8bee1dc2dfe71

[ "$(uname -s)" = "Darwin" ] || fail "ce script est pour macOS." "this script is for macOS."
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
command -v uv >/dev/null 2>&1 || fail "uv introuvable : installe d'abord ReaCue (Install ReaCue.command)." \
                                      "uv not found: install ReaCue first (Install ReaCue.command)."
t "  Machine : $(uname -m) — analyse de structure (SongFormer) dans $HERE/.venv-structure" \
  "  Machine: $(uname -m) — structure analysis (SongFormer) in $HERE/.venv-structure"

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
t "  téléchargement de SongFormer, MuQ et MusicFM (versions figées)…" \
  "  downloading SongFormer, MuQ and MusicFM (pinned versions)…"
mkdir -p structure
fetch ASLP-lab/SongFormer "$SONGFORMER_REV" structure/SongFormer || fail "téléchargement de SongFormer impossible." "could not download SongFormer."
TP=structure/SongFormer/src/third_party
fetch tencent-ailab/MuQ "$MUQ_REV" "$TP/MuQ" || fail "téléchargement de MuQ impossible." "could not download MuQ."
fetch minzwon/musicfm "$MUSICFM_REV" "$TP/musicfm" || fail "téléchargement de MusicFM impossible." "could not download MusicFM."

if [ ! -x .venv-structure/bin/python ]; then
  uv venv .venv-structure --python 3.11 || fail "création de .venv-structure impossible." "could not create .venv-structure."
fi
t "  installation de PyTorch et des dépendances (plusieurs minutes)…" \
  "  installing PyTorch and the dependencies (several minutes)…"
uv pip install --python .venv-structure/bin/python --only-binary :all: \
  --no-binary nnaudio,easydict,antlr4-python3-runtime -r requirements-structure.txt \
  || fail "installation des dépendances impossible (voir ci-dessus)." "could not install the dependencies (see above)."
uv pip install --python .venv-structure/bin/python --no-deps "./$TP/MuQ" \
  || fail "installation de MuQ impossible." "could not install MuQ."
t "  téléchargement des modèles (environ 2 Go) et test…" "  downloading the models (about 2 GB) and testing…"
.venv-structure/bin/python reacue_structure.py check --lang "$L" || fail "SongFormer ne fonctionne pas (voir ci-dessus)." \
                                                                     "SongFormer does not work (see above)."
t "  Analyse de structure installée : utilisée automatiquement par « Préparer » (réglage « Détection de structure »)." \
  "  Structure analysis installed: used automatically by “Prepare” (“Structure detection” setting)."
