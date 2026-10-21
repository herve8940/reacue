# Séparation de stems pour ReaCue (Demucs, en local) — Windows / Stem separation for ReaCue — Windows.
# Lancé par install_windows.ps1 (si tu réponds oui) ou par « Install ReaCue Stems.bat » ; ou :
#   powershell -ExecutionPolicy Bypass -File install\install_stems_windows.ps1 [-Lang fr|en]
# Environnement séparé .venv-demucs (n'abîme pas le .venv de ReaCue). Relançable sans risque.
# Internet nécessaire : environ 1 Go (PyTorch + 2 modèles Demucs), 5 à 15 minutes.
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

$env:Path = (Join-Path $env:USERPROFILE ".local\bin") + ";" + (Join-Path $env:USERPROFILE ".cargo\bin") + ";" + $env:Path
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Fail "uv introuvable : installe d'abord ReaCue (Install ReaCue.bat)." "uv not found: install ReaCue first (Install ReaCue.bat)."
}
Write-Host (T "  Séparation de stems (Demucs) dans $Here\.venv-demucs" "  Stem separation (Demucs) in $Here\.venv-demucs")
$Py = Join-Path $Here ".venv-demucs\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Py)) {
  & uv venv .venv-demucs --python 3.12
  if ($LASTEXITCODE -ne 0) { Fail "création de .venv-demucs impossible." "could not create .venv-demucs." }
}
Write-Host (T "  téléchargement et installation de PyTorch et Demucs (plusieurs minutes)…" "  downloading and installing PyTorch and Demucs (several minutes)…")
& uv pip install --python $Py --only-binary ":all:" --no-binary demucs -r requirements-stems.txt
if ($LASTEXITCODE -ne 0) { Fail "installation de Demucs impossible (voir ci-dessus)." "could not install Demucs (see above)." }
Write-Host (T "  téléchargement des modèles et test de vitesse…" "  downloading the models and measuring the speed…")
& $Py (Join-Path $Here "reacue_stems.py") check --lang $L
if ($LASTEXITCODE -ne 0) { Fail "Demucs ne fonctionne pas (voir ci-dessus)." "Demucs does not work (see above)." }
Write-Host (T "  Séparation de stems installée : action « ReaCue - Séparer les stems » dans REAPER." "  Stem separation installed: “ReaCue - Separate stems” action in REAPER.")
exit 0
