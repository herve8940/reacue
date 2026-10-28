# Séparation de stems pour ReaCue (Demucs, en local) - Windows / Stem separation for ReaCue - Windows.
# Lancé par install_windows.ps1 (si tu réponds oui) ou par « Install ReaCue Stems.bat » ; ou :
#   powershell -ExecutionPolicy Bypass -File install\install_stems_windows.ps1 [-Lang fr|en] [-ExtraIndexUrl <url>]
# Environnement séparé .venv-demucs (n'abîme pas le .venv de ReaCue). Relançable sans risque.
# Internet nécessaire : environ 1 Go (PyTorch + modèles Demucs), 5 à 15 minutes.
# Fichier enregistré en UTF-8 avec BOM (sinon Windows PowerShell 5.1 lit les accents en ANSI).
param([string]$Lang = "", [string]$ExtraIndexUrl = "")
$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$Here = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Here

# Cache localisé : évite de remplir le disque système (C:)
if (-not $env:UV_CACHE_DIR) {
  $c = [System.Environment]::GetEnvironmentVariable("UV_CACHE_DIR", "User")
  if ($c) { $env:UV_CACHE_DIR = $c } else { $env:UV_CACHE_DIR = Join-Path $Here ".uv_cache" }
}
if (-not $env:TORCH_HOME) {
  $c = [System.Environment]::GetEnvironmentVariable("TORCH_HOME", "User")
  if ($c) { $env:TORCH_HOME = $c }
}
if (-not $env:HF_HOME) {
  $c = [System.Environment]::GetEnvironmentVariable("HF_HOME", "User")
  if ($c) { $env:HF_HOME = $c }
}
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
Write-Host (T "  Licence : Demucs (Meta / A. Défossez) est sous licence MIT ; ses modèles sont téléchargés depuis Meta. Détails : THIRD_PARTY_NOTICES.md" "  Licence: Demucs (Meta / A. Défossez) is MIT-licensed; its models are downloaded from Meta. Details: THIRD_PARTY_NOTICES.md")
$Py = Join-Path $Here ".venv-demucs\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Py)) {
  & uv venv .venv-demucs --python 3.12
  if ($LASTEXITCODE -ne 0) { Fail "création de .venv-demucs impossible." "could not create .venv-demucs." }
}

Write-Host (T "  analyse du matériel et audit de l'environnement…" "  hardware analysis and environment audit…")
$audit = $null
try {
  $auditRaw = & $Py (Join-Path $Here "reacue_gpu.py") audit $Py 2>$null
  if ($LASTEXITCODE -eq 0 -and $auditRaw) {
    $audit = $auditRaw | ConvertFrom-Json
  }
} catch { }

if (-not $ExtraIndexUrl -and $audit -and $audit.target_index) {
  $ExtraIndexUrl = $audit.target_index
}

if ($audit -and $audit.action -eq "reinstall") {
  Write-Host (T "  configuration matérielle non optimale : $($audit.reason_fr)" `
                "  hardware configuration not optimal: $($audit.reason)") -ForegroundColor Yellow
  if ($audit.installed) {
    Write-Host (T "  désinstallation des paquets PyTorch non adaptés ($($audit.torch_version))…" `
                  "  uninstalling mismatched PyTorch packages ($($audit.torch_version))…")
    & uv pip uninstall --python $Py torch torchaudio
  }
  $torchVer = $audit.target_version
  Write-Host (T "  installation de PyTorch $torchVer avec accélération ($ExtraIndexUrl)…" `
                "  installing PyTorch $torchVer with acceleration ($ExtraIndexUrl)…")
  & uv pip install --python $Py "torch==$torchVer" "torchaudio==$torchVer" --index $ExtraIndexUrl --reinstall
  if ($LASTEXITCODE -ne 0) {
    Write-Host (T "  ! repli sur le mode standard" "  ! fallback to standard mode") -ForegroundColor Yellow
  }
} elseif ($audit -and $audit.action -eq "install") {
  $torchVer = $audit.target_version
  Write-Host (T "  installation de PyTorch $torchVer ($ExtraIndexUrl)…" `
                "  installing PyTorch $torchVer ($ExtraIndexUrl)…")
  if ($ExtraIndexUrl) {
    & uv pip install --python $Py "torch==$torchVer" "torchaudio==$torchVer" --index $ExtraIndexUrl --reinstall
  }
} elseif ($audit -and $audit.status -eq "optimal") {
  Write-Host (T "  accélération matérielle déjà optimale ($($audit.torch_version)) : aucun téléchargement nécessaire." `
                "  hardware acceleration already optimal ($($audit.torch_version)): no download needed.") -ForegroundColor Green
}

$indexArgs = @()
if ($ExtraIndexUrl) {
  $indexArgs = @("--extra-index-url", $ExtraIndexUrl)
}
& uv pip install --python $Py @indexArgs --only-binary ":all:" --no-binary demucs -r requirements-stems.txt
if ($LASTEXITCODE -ne 0) { Fail "installation de Demucs impossible (voir ci-dessus)." "could not install Demucs (see above)." }

try {
  $reaperDir = if ($env:REAPER_RESOURCE_PATH) { $env:REAPER_RESOURCE_PATH } else { Join-Path $env:APPDATA "REAPER" }
  $settingsFile = Join-Path $reaperDir "ReaCueMCP\reacue_settings.json"
  if (Test-Path -LiteralPath (Split-Path -Parent $settingsFile)) {
    & $Py (Join-Path $Here "reacue_gpu.py") sync-settings $settingsFile 2>$null | Out-Null
  }
} catch { }

Write-Host (T "  vérification des modèles et test de vitesse…" "  verifying models and measuring speed…")
& $Py (Join-Path $Here "reacue_stems.py") check --lang $L
if ($LASTEXITCODE -ne 0) { Fail "Demucs ne fonctionne pas (voir ci-dessus)." "Demucs does not work (see above)." }
Write-Host (T "  Séparation de stems installée : action « ReaCue - Séparer les stems » dans REAPER." "  Stem separation installed: 'ReaCue - Separate stems' action in REAPER.")
exit 0
