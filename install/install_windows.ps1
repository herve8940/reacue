# Installation de ReaCue sous Windows / ReaCue installer for Windows.
# Lancé par « Install ReaCue.bat » (double-clic) ; ou :
#   powershell -ExecutionPolicy Bypass -File install\install_windows.ps1 [-Lang fr|en] [-Mcp yes|no|ask] [-Stems yes|no|ask] [-Structure yes|no|ask]
# Relançable sans risque (idempotent). Internet n'est nécessaire que pendant l'installation.
# Fichier enregistré en UTF-8 avec BOM (sinon Windows PowerShell 5.1 lit les accents en ANSI).
param(
  [string]$Lang = "",
  [ValidateSet("yes", "no", "ask")][string]$Mcp = "ask",
  [ValidateSet("yes", "no", "ask")][string]$Stems = "ask",
  [ValidateSet("yes", "no", "ask")][string]$Structure = "ask",
  [string]$ReaperDir = ""
)
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
Write-Host (T "== 1/6 Vérifications et analyse du matériel" "== 1/6 Checks and hardware analysis")
if (-not (Test-Path -LiteralPath $ReaperDir -PathType Container)) {
  Fail "dossier REAPER introuvable ($ReaperDir). Lance REAPER une fois, ferme-le, puis relance l'installation (REAPER portable : -ReaperDir <dossier>)." `
       "REAPER folder not found ($ReaperDir). Start REAPER once, close it, then run the installer again (portable REAPER: -ReaperDir <folder>)."
}
Write-Host "  REAPER : $ReaperDir"
Write-Host "  ReaCue : $Here"

$GpuInfo = $null
$GpuExtraIndex = ""
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
  try {
    $out = & nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>$null
    if ($LASTEXITCODE -eq 0 -and $out) {
      $parts = $out.Split(",")
      $name = $parts[0].Trim()
      $vram = [int]$parts[1].Trim()
      $GpuInfo = @{ Vendor = "nvidia"; Name = $name; VramMB = $vram; Dedicated = $true; Backend = "cuda" }
    }
  } catch { }
}
if (-not $GpuInfo) {
  try {
    $adapters = Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0*" -ErrorAction SilentlyContinue | Where-Object { $_.DriverDesc }
    foreach ($a in $adapters) {
      $vram = if ($a.'HardwareInformation.qwMemorySize') { [int64]$a.'HardwareInformation.qwMemorySize' } elseif ($a.'HardwareInformation.MemorySize') { [int64]$a.'HardwareInformation.MemorySize' } else { 0 }
      $prov = [string]$a.ProviderName
      $desc = [string]$a.DriverDesc
      $vramMB = [math]::Round($vram / 1MB)
      if ($vram -ge 2147483648) {
        if ($prov -match "NVIDIA" -or $desc -match "GeForce|RTX|GTX|Quadro") {
          $GpuInfo = @{ Vendor = "nvidia"; Name = $desc; VramMB = $vramMB; Dedicated = $true; Backend = "cuda" }
          break
        } elseif ($prov -match "Advanced Micro Devices|AMD|ATI" -or $desc -match "Radeon") {
          $GpuInfo = @{ Vendor = "amd"; Name = $desc; VramMB = $vramMB; Dedicated = $true; Backend = "rocm" }
          break
        }
      }
    }
  } catch { }
}
if ($GpuInfo -and $GpuInfo.Vendor -eq "nvidia") {
  $vramGb = [math]::Round($GpuInfo.VramMB / 1024)
  $GpuExtraIndex = "https://download.pytorch.org/whl/cu124"
  if ($GpuInfo.Name -match "RTX 50|5070|5080|5090|Blackwell") {
    $GpuExtraIndex = "https://download.pytorch.org/whl/cu128"
  }
  Write-Host (T "  GPU dédié : $($GpuInfo.Name) ($vramGb Go VRAM) : Accélération NVIDIA CUDA activée" `
                "  Dedicated GPU: $($GpuInfo.Name) ($vramGb GB VRAM) : NVIDIA CUDA acceleration enabled") -ForegroundColor Green
} elseif ($GpuInfo -and $GpuInfo.Vendor -eq "amd") {
  $vramGb = [math]::Round($GpuInfo.VramMB / 1024)
  Write-Host (T "  GPU dédié : $($GpuInfo.Name) ($vramGb Go VRAM) : Accélération AMD détectée" `
                "  Dedicated GPU: $($GpuInfo.Name) ($vramGb GB VRAM) : AMD acceleration detected") -ForegroundColor Green
} else {
  Write-Host (T "  Accélération : Processeur standard (CPU)" `
                "  Acceleration: Standard processor (CPU)")
}

Write-Host ""
Write-Host (T "== 2/6 uv (gestionnaire Python d'Astral)" "== 2/6 uv (Astral's Python manager)")
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
Write-Host (T "== 3/6 Environnement Python 3.12 (.venv) et dépendances" "== 3/6 Python 3.12 environment (.venv) and dependencies")
$Py = Join-Path $Here ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Py)) {
  & uv venv .venv --python 3.12
  if ($LASTEXITCODE -ne 0) { Fail "création du .venv impossible." "could not create .venv." }
}
# --no-build : paquets précompilés uniquement (pas de compilateur nécessaire)
& uv pip install --no-build --python $Py -r requirements.txt
if ($LASTEXITCODE -ne 0) { Fail "installation des dépendances impossible (voir ci-dessus)." "could not install dependencies (see above)." }
& $Py -c "import librosa, soundfile, mcp; print('  librosa', librosa.__version__, 'OK')"
if ($LASTEXITCODE -ne 0) { Fail "dépendances incomplètes." "incomplete dependencies." }

Write-Host ""
Write-Host (T "== 4/6 Configuration de REAPER" "== 4/6 REAPER configuration")
$env:REAPER_RESOURCE_PATH = $ReaperDir
& $Py (Join-Path $Here "install\reacue_setup.py") install --lang $L --install-dir $Here --reaper-dir $ReaperDir --mcp $Mcp
if ($LASTEXITCODE -ne 0) { Fail "configuration incomplète." "configuration incomplete." }

Write-Host ""
Write-Host (T "== 5/6 Séparation de stems (optionnel)" "== 5/6 Stem separation (optional)")
$demucsPy = Join-Path $Here ".venv-demucs\Scripts\python.exe"
if (Test-Path -LiteralPath $demucsPy) {
  $audit = $null
  try {
    $auditRaw = & $demucsPy (Join-Path $Here "reacue_gpu.py") audit $demucsPy 2>$null
    if ($LASTEXITCODE -eq 0 -and $auditRaw) {
      $audit = $auditRaw | ConvertFrom-Json
    }
  } catch { }

  if ($audit -and $audit.action -eq "reinstall") {
    Write-Host (T "  ! Réalignement matériel requis dans .venv-demucs : $($audit.reason_fr)" `
                  "  ! Hardware realignment needed in .venv-demucs: $($audit.reason)") -ForegroundColor Yellow
    $Stems = "yes"
  } elseif ($audit -and $audit.status -eq "optimal") {
    Write-Host (T "  Accélération matérielle déjà optimale ($($audit.torch_version)) dans .venv-demucs." `
                  "  Hardware acceleration already optimal ($($audit.torch_version)) in .venv-demucs.") -ForegroundColor Green
    if ($Stems -eq "ask") { $Stems = "no" }
  } else {
    if ($Stems -eq "ask") { $Stems = "yes" }
  }
}
if ($Stems -eq "ask") {
  Write-Host (T "  Sépare un MP3 en stems (voix, batterie, basse, guitare, piano, autres) dans REAPER, en local, sans abonnement." "  Splits an MP3 into stems (vocals, drums, bass, guitar, piano, other) inside REAPER, locally, no subscription.")
  $A = Read-Host (T "  Installer la séparation de stems (Demucs, environ 1 Go à télécharger, 5 à 15 min) ? [o/N]" "  Install stem separation (Demucs, about 1 GB to download, 5 to 15 min)? [y/N]")
  $Stems = if ($A -and ($A.ToLower().StartsWith("o") -or $A.ToLower().StartsWith("y"))) { "yes" } else { "no" }
}
if ($Stems -eq "yes") {
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Here "install\install_stems_windows.ps1") -Lang $L -ExtraIndexUrl $GpuExtraIndex
  if ($LASTEXITCODE -ne 0) {
    Write-Host (T "  ! séparation de stems non installée (le reste de ReaCue fonctionne). Réessaie avec « Install ReaCue Stems.bat »." "  ! stem separation not installed (the rest of ReaCue works). Try again with “Install ReaCue Stems.bat”.") -ForegroundColor Yellow
  }
} else {
  if (-not (Test-Path -LiteralPath $demucsPy)) {
    Write-Host (T "  Non installée. Plus tard : double-clic sur « Install ReaCue Stems.bat »." "  Not installed. Later: double-click “Install ReaCue Stems.bat”.")
  }
}

Write-Host ""
Write-Host (T "== 6/6 Analyse de structure (recommandé)" "== 6/6 Structure analysis (recommended)")
$structurePy = Join-Path $Here ".venv-structure\Scripts\python.exe"
if (Test-Path -LiteralPath $structurePy) {
  $structAudit = $null
  try {
    $structAuditJson = & $MainPy (Join-Path $Here "reacue_gpu.py") audit $structurePy 2>$null
    if ($LASTEXITCODE -eq 0 -and $structAuditJson) {
      $structAudit = $structAuditJson | ConvertFrom-Json
    }
  } catch { }

  if ($structAudit -and $structAudit.action -eq "reinstall") {
    Write-Host (T "  ! Réalignement matériel requis dans .venv-structure : $($structAudit.reason_fr)" `
                  "  ! Hardware realignment needed in .venv-structure: $($structAudit.reason)") -ForegroundColor Yellow
    $Structure = "yes"
  } elseif ($structAudit -and $structAudit.status -eq "optimal") {
    Write-Host (T "  Accélération matérielle déjà optimale ($($structAudit.torch_version)) dans .venv-structure." `
                  "  Hardware acceleration already optimal ($($structAudit.torch_version)) in .venv-structure.") -ForegroundColor Green
    if ($Structure -eq "ask") { $Structure = "no" }
  } else {
    if ($Structure -eq "ask") { $Structure = "yes" }
  }
}
if ($Structure -eq "ask") {
  Write-Host (T "  Détecte couplets, refrains, ponts… avec SongFormer (IA, en local) : c'est l'analyse par défaut de ReaCue." "  Detects verses, choruses, bridges… with SongFormer (AI, local): ReaCue's default analysis.")
  Write-Host (T "  Usage non commercial (licence des poids MuQ) : il faudra taper « J'accepte » à l'étape suivante." "  Non-commercial use (MuQ weights licence): you will have to type “I accept” at the next step.")
  $A = Read-Host (T "  Installer l'analyse de structure (environ 3 Go à télécharger, 10 à 40 min, 8 Go de RAM conseillés) ? [O/n]" "  Install structure analysis (about 3 GB to download, 10 to 40 min, 8 GB RAM recommended)? [Y/n]")
  $Structure = if ($A -and $A.ToLower().StartsWith("n")) { "no" } else { "yes" }
}
if ($Structure -eq "yes") {
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Here "install\install_structure_windows.ps1") -Lang $L -ExtraIndexUrl $GpuExtraIndex
  if ($LASTEXITCODE -ne 0) {
    Write-Host (T "  ! analyse de structure non installée (ReaCue garde sa détection). Réessaie avec « Install ReaCue Structure.bat »." "  ! structure analysis not installed (ReaCue keeps its own detection). Try again with “Install ReaCue Structure.bat”.") -ForegroundColor Yellow
  }
} else {
  if (-not (Test-Path -LiteralPath $structurePy)) {
    Write-Host (T "  Non installée. Plus tard : double-clic sur « Install ReaCue Structure.bat »." "  Not installed. Later: double-click “Install ReaCue Structure.bat”.")
  }
}
exit 0
