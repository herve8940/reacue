# Paroles calées mot par mot pour ReaCue (alignement forcé wav2vec2, en local) — Windows.
# Word-by-word lyrics timing for ReaCue (wav2vec2 forced alignment, local) — Windows.
# Lancé par « Install ReaCue Words.bat » ; ou :
#   powershell -ExecutionPolicy Bypass -File install\install_words_windows.ps1 [-Lang fr|en]
# Langues des modèles : français et anglais (≈ 1,3 Go chacun) ; une seule : $env:REACUE_WORDS_LANGS = "fr" (ou "en").
# Environnement séparé .venv-words (n'abîme pas le .venv de ReaCue). Relançable sans risque.
# Fichier enregistré en UTF-8 avec BOM (sinon Windows PowerShell 5.1 lit les accents en ANSI).
param([string]$Lang = "")
$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$Here = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Here
if (-not $Lang) { $Lang = Read-Host "Langue / Language [fr/en] (fr)" }
$L = if ($Lang -and $Lang.ToLower().StartsWith("en")) { "en" } else { "fr" }
function T([string]$fr, [string]$en) { if ($L -eq "en") { $en } else { $fr } }
function Fail([string]$fr, [string]$en) {
  Write-Host ""
  Write-Host (T "ÉCHEC : $fr" "FAILED: $en") -ForegroundColor Red
  exit 1
}
$Langs = if ($env:REACUE_WORDS_LANGS) { $env:REACUE_WORDS_LANGS } else { "fr,en" }

$env:Path = (Join-Path $env:USERPROFILE ".local\bin") + ";" + (Join-Path $env:USERPROFILE ".cargo\bin") + ";" + $env:Path
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Fail "uv introuvable : installe d'abord ReaCue (Install ReaCue.bat)." "uv not found: install ReaCue first (Install ReaCue.bat)."
}
Write-Host (T "  Paroles mot par mot (wav2vec2) dans $Here\.venv-words" "  Word-by-word lyrics (wav2vec2) in $Here\.venv-words")
Write-Host (T "  Licence : modèles wav2vec2 XLSR-53 de J. Grosman (Apache-2.0), base Meta XLSR-53 (Apache-2.0) ; téléchargés depuis Hugging Face. Détails : THIRD_PARTY_NOTICES.md" "  Licence: J. Grosman's wav2vec2 XLSR-53 models (Apache-2.0), Meta XLSR-53 base (Apache-2.0); downloaded from Hugging Face. Details: THIRD_PARTY_NOTICES.md")
$Py = Join-Path $Here ".venv-words\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Py)) {
  & uv venv .venv-words --python 3.12
  if ($LASTEXITCODE -ne 0) { Fail "création de .venv-words impossible." "could not create .venv-words." }
}
Write-Host (T "  installation de PyTorch et des dépendances (plusieurs minutes)…" "  installing PyTorch and the dependencies (several minutes)…")
& uv pip install --python $Py --only-binary ":all:" -r requirements-words.txt
if ($LASTEXITCODE -ne 0) { Fail "installation des dépendances impossible (voir ci-dessus)." "could not install the dependencies (see above)." }
Write-Host (T "  téléchargement des modèles ($Langs, environ 1,3 Go chacun) et test…" "  downloading the models ($Langs, about 1.3 GB each) and testing…")
& $Py (Join-Path $Here "reacue_words.py") check --lang $L --langs $Langs
if ($LASTEXITCODE -ne 0) { Fail "le calage mot par mot ne fonctionne pas (voir ci-dessus)." "word-by-word timing does not work (see above)." }
Write-Host (T "  Paroles mot par mot installées : utilisées automatiquement à la prochaine publication du prompteur (réglage « words_engine »)." "  Word-by-word lyrics installed: used automatically at the next prompter update (“words_engine” setting).")
exit 0
