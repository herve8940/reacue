# Installation de ReaCue sous Windows / ReaCue installer for Windows.
# Lancé par « Install ReaCue.bat » (double-clic) ; ou :
#   powershell -ExecutionPolicy Bypass -File install\install_windows.ps1 [-Lang fr|en] [-Mcp yes|no|ask] [-Stems yes|no|ask]
# Relançable sans risque (idempotent). Internet n'est nécessaire que pendant l'installation.
# Fichier enregistré en UTF-8 avec BOM (sinon Windows PowerShell 5.1 lit les accents en ANSI).
param(
  [string]$Lang = "",
  [ValidateSet("yes", "no", "ask")][string]$Mcp = "ask",
  [ValidateSet("yes", "no", "ask")][string]$Stems = "ask",
  [string]$ReaperDir = ""
)
$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$Here = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Here

if (-not $Lang) {
  Write-Host "ReaCue - installation"
  $Lang = Read-Host "Langue / Language [fr/en] (fr)"
}
$L = if ($Lang -and $Lang.ToLower().StartsWith("en")) { "en" } else { "fr" }
function T([string]$fr, [string]$en) { if ($L -eq "en") { $en } else { $fr } }
function Fail([string]$fr, [string]$en) {
  Write-Host ""
  Write-Host (T "ÉCHEC : $fr" "FAILED: $en") -ForegroundColor Red
  exit 1
}

if (-not $ReaperDir) {
  $ReaperDir = if ($env:REAPER_RESOURCE_PATH) { $env:REAPER_RESOURCE_PATH } else { Join-Path $env:APPDATA "REAPER" }
}

Write-Host ""
Write-Host (T "== 1/5 Vérifications" "== 1/5 Checks")
if (-not (Test-Path -LiteralPath $ReaperDir -PathType Container)) {
  Fail "dossier REAPER introuvable ($ReaperDir). Lance REAPER une fois, ferme-le, puis relance l'installation (REAPER portable : -ReaperDir <dossier>)." `
       "REAPER folder not found ($ReaperDir). Start REAPER once, close it, then run the installer again (portable REAPER: -ReaperDir <folder>)."
}
Write-Host "  REAPER : $ReaperDir"
Write-Host "  ReaCue : $Here"

Write-Host ""
Write-Host (T "== 2/5 uv (gestionnaire Python d'Astral)" "== 2/5 uv (Astral's Python manager)")
$env:Path = (Join-Path $env:USERPROFILE ".local\bin") + ";" + (Join-Path $env:USERPROFILE ".cargo\bin") + ";" + $env:Path
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Write-Host (T "  installation de uv (https://astral.sh/uv)…" "  installing uv (https://astral.sh/uv)…")
  try {
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
  } catch { Fail "installation de uv impossible (internet ?)." "could not install uv (internet?)." }
  if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Fail "uv introuvable après installation." "uv not found after installation."
  }
}
Write-Host ("  " + (uv --version))

Write-Host ""
Write-Host (T "== 3/5 Environnement Python 3.12 (.venv) et dépendances" "== 3/5 Python 3.12 environment (.venv) and dependencies")
if (Test-Path -LiteralPath ".venv") { Remove-Item -LiteralPath ".venv" -Recurse -Force }
& uv venv .venv --python 3.12
if ($LASTEXITCODE -ne 0) { Fail "création du .venv impossible." "could not create .venv." }
$Py = Join-Path $Here ".venv\Scripts\python.exe"
# --no-build : paquets précompilés uniquement (pas de compilateur nécessaire)
& uv pip install --no-build --python $Py -r requirements.txt
if ($LASTEXITCODE -ne 0) { Fail "installation des dépendances impossible (voir ci-dessus)." "could not install dependencies (see above)." }
& $Py -c "import librosa, soundfile, mcp; print('  librosa', librosa.__version__, 'OK')"
if ($LASTEXITCODE -ne 0) { Fail "dépendances incomplètes." "incomplete dependencies." }

Write-Host ""
Write-Host (T "== 4/5 Configuration de REAPER" "== 4/5 REAPER configuration")
$env:REAPER_RESOURCE_PATH = $ReaperDir
& $Py (Join-Path $Here "install\reacue_setup.py") install --lang $L --install-dir $Here --reaper-dir $ReaperDir --mcp $Mcp
if ($LASTEXITCODE -ne 0) { Fail "configuration incomplète." "configuration incomplete." }

Write-Host ""
Write-Host (T "== 5/5 Séparation de stems (optionnel)" "== 5/5 Stem separation (optional)")
if ($Stems -eq "ask" -and (Test-Path -LiteralPath (Join-Path $Here ".venv-demucs\Scripts\python.exe"))) {
  $Stems = "yes"   # déjà installée : mise à jour
}
if ($Stems -eq "ask") {
  Write-Host (T "  Sépare un MP3 en stems (voix, batterie, basse, guitare, piano, autres) dans REAPER, en local, sans abonnement." "  Splits an MP3 into stems (vocals, drums, bass, guitar, piano, other) inside REAPER, locally, no subscription.")
  $A = Read-Host (T "  Installer la séparation de stems (Demucs, environ 1 Go à télécharger, 5 à 15 min) ? [o/N]" "  Install stem separation (Demucs, about 1 GB to download, 5 to 15 min)? [y/N]")
  $Stems = if ($A -and ($A.ToLower().StartsWith("o") -or $A.ToLower().StartsWith("y"))) { "yes" } else { "no" }
}
if ($Stems -eq "yes") {
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Here "install\install_stems_windows.ps1") -Lang $L
  if ($LASTEXITCODE -ne 0) {
    Write-Host (T "  ! séparation de stems non installée (le reste de ReaCue fonctionne). Réessaie avec « Install ReaCue Stems.bat »." "  ! stem separation not installed (the rest of ReaCue works). Try again with “Install ReaCue Stems.bat”.") -ForegroundColor Yellow
  }
} else {
  Write-Host (T "  Non installée. Plus tard : double-clic sur « Install ReaCue Stems.bat »." "  Not installed. Later: double-click “Install ReaCue Stems.bat”.")
}
exit 0
