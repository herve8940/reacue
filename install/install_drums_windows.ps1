# Transcription de batterie pour ReaCue (ADTOF, en local) — Windows / Drum transcription for ReaCue — Windows.
# Lancé par « Install ReaCue Drums.bat » ; ou :
#   powershell -ExecutionPolicy Bypass -File install\install_drums_windows.ps1 [-Lang fr|en]
# Environnement séparé .venv-drums + code et poids figés dans drums\ (n'abîme pas le .venv de ReaCue).
# Internet nécessaire : environ 300 Mo (PyTorch, déjà en cache si Demucs est installé) + 16 Mo (ADTOF),
# 3 à 10 minutes. Relançable.
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

# révision figée (même valeur que reacue_mcp/drums.py)
$AdtofRev = "85c192e78f716ea0b111cc8a5ee4a8f6a3a4f8a9"

$env:Path = (Join-Path $env:USERPROFILE ".local\bin") + ";" + (Join-Path $env:USERPROFILE ".cargo\bin") + ";" + $env:Path
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Fail "uv introuvable : installe d'abord ReaCue (Install ReaCue.bat)." "uv not found: install ReaCue first (Install ReaCue.bat)."
}
Write-Host (T "  Transcription de batterie (ADTOF) dans $Here\.venv-drums" "  Drum transcription (ADTOF) in $Here\.venv-drums")

# Licences : accord explicite AVANT tout téléchargement (voir THIRD_PARTY_NOTICES.md).
# Installation non interactive : variable d'environnement REACUE_DRUMS_ACCEPT=yes.
# Accord mémorisé dans drums\.licenses_accepted.
$LicId = "adtof-weights-ccbyncsa4+adtof-pytorch-unstated/v1"
$AcceptFile = Join-Path $Here "drums\.licenses_accepted"
$accepted = (Test-Path -LiteralPath $AcceptFile) -and (((Get-Content -LiteralPath $AcceptFile -TotalCount 1) -as [string]) -eq $LicId)
if (-not $accepted) {
  Write-Host ""
  Write-Host (T "  ┌─ Licences de la transcription de batterie ───────────────────────────────────" "  ┌─ Drum transcription licences ────────────────────────────────────────────────")
  Write-Host (T "  │ ADTOF (M. Zehren et al.) : code et modèle CC BY-NC-SA 4.0 → USAGE NON COMMERCIAL UNIQUEMENT." "  │ ADTOF (M. Zehren et al.): code and model CC BY-NC-SA 4.0 → NON-COMMERCIAL USE ONLY.") -ForegroundColor Yellow
  Write-Host (T "  │ ADTOF-pytorch (X. Riley, portage PyTorch des poids d'ADTOF) : licence non précisée par son auteur." "  │ ADTOF-pytorch (X. Riley, PyTorch port of the ADTOF weights): licence not stated by its author.")
  Write-Host (T "  │ Le code et les poids sont téléchargés depuis GitHub ; tu es responsable du respect" "  │ The code and weights are downloaded from GitHub; you are responsible for complying")
  Write-Host (T "  │ de leurs licences. Détails : THIRD_PARTY_NOTICES.md (ceci n'est pas un avis juridique)." "  │ with their licences. Details: THIRD_PARTY_NOTICES.md (this is not legal advice).")
  Write-Host "  └──────────────────────────────────────────────────────────────────────────────"
  $Want = T "J'accepte" "I accept"
  if ($env:REACUE_DRUMS_ACCEPT -eq "yes") {
    Write-Host (T "  Licences acceptées (REACUE_DRUMS_ACCEPT=yes)." "  Licences accepted (REACUE_DRUMS_ACCEPT=yes).")
  } else {
    $Ans = ""
    if (-not [Console]::IsInputRedirected) {
      $Ans = Read-Host (T "  Pour installer, tape exactement « J'accepte » (sinon Entrée)" "  To install, type exactly 'I accept' (otherwise Enter)")
    }
    if ($Ans) { $Ans = $Ans.Replace([string][char]0x2019, "'").Trim() }
    if ($Ans -cne $Want) {
      Write-Host (T "  Licences non acceptées : rien n'a été installé ni téléchargé." "  Licences not accepted: nothing was installed or downloaded.") -ForegroundColor Yellow
      exit 3
    }
  }
  New-Item -ItemType Directory -Path (Join-Path $Here "drums") -Force | Out-Null
  Set-Content -LiteralPath $AcceptFile -Value @($LicId, (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) -Encoding UTF8
}

function Fetch([string]$Repo, [string]$Rev, [string]$Dest) {
  $mark = Join-Path $Dest ".reacue_rev"
  if ((Test-Path -LiteralPath $mark) -and ((Get-Content -LiteralPath $mark -Raw).Trim() -eq $Rev)) { return $true }
  if (Test-Path -LiteralPath $Dest) { Remove-Item -LiteralPath $Dest -Recurse -Force }
  $tmp = "$Dest.tmp"
  if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
  New-Item -ItemType Directory -Path $tmp -Force | Out-Null
  $tgz = Join-Path $env:TEMP ("reacue_" + $Rev + ".tar.gz")
  & curl.exe -LsSf -o $tgz ("https://codeload.github.com/" + $Repo + "/tar.gz/" + $Rev)
  $ok = ($LASTEXITCODE -eq 0)
  if ($ok) { & tar.exe -xzf $tgz -C $tmp --strip-components 1; $ok = ($LASTEXITCODE -eq 0) }
  Remove-Item -LiteralPath $tgz -Force -ErrorAction SilentlyContinue
  if (-not $ok -and (Get-Command git -ErrorAction SilentlyContinue)) {
    # repli : git (même révision figée)
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    & git -C $tmp init -q
    & git -C $tmp fetch -q --depth 1 ("https://github.com/" + $Repo + ".git") $Rev
    if ($LASTEXITCODE -eq 0) { & git -C $tmp checkout -q FETCH_HEAD; $ok = ($LASTEXITCODE -eq 0) }
    Remove-Item -LiteralPath (Join-Path $tmp ".git") -Recurse -Force -ErrorAction SilentlyContinue
  }
  if (-not $ok) { return $false }
  Move-Item -LiteralPath $tmp -Destination $Dest
  Set-Content -LiteralPath $mark -Value $Rev -Encoding ASCII
  return $true
}
Write-Host (T "  téléchargement d'ADTOF-pytorch (code + poids, 16 Mo, version figée)…" "  downloading ADTOF-pytorch (code + weights, 16 MB, pinned version)…")
New-Item -ItemType Directory -Path (Join-Path $Here "drums") -Force | Out-Null
if (-not (Fetch "xavriley/ADTOF-pytorch" $AdtofRev (Join-Path $Here "drums\ADTOF-pytorch"))) {
  Fail "téléchargement d'ADTOF-pytorch impossible." "could not download ADTOF-pytorch."
}

$Py = Join-Path $Here ".venv-drums\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Py)) {
  & uv venv .venv-drums --python 3.12
  if ($LASTEXITCODE -ne 0) { Fail "création de .venv-drums impossible." "could not create .venv-drums." }
}
Write-Host (T "  installation de PyTorch et des dépendances (plusieurs minutes)…" "  installing PyTorch and the dependencies (several minutes)…")
if (-not $ExtraIndexUrl) {
  if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $ExtraIndexUrl = "https://download.pytorch.org/whl/cu124"
  } else {
    try {
      $adapters = Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0*" -ErrorAction SilentlyContinue
      foreach ($a in $adapters) {
        $vram = if ($a.'HardwareInformation.qwMemorySize') { [int64]$a.'HardwareInformation.qwMemorySize' } elseif ($a.'HardwareInformation.MemorySize') { [int64]$a.'HardwareInformation.MemorySize' } else { 0 }
        $prov = [string]$a.ProviderName
        $desc = [string]$a.DriverDesc
        if ($vram -ge 2147483648 -and ($prov -match "NVIDIA" -or $desc -match "GeForce|RTX|GTX")) {
          $ExtraIndexUrl = "https://download.pytorch.org/whl/cu124"
          break
        }
      }
    } catch { }
  }
}
$indexArgs = @()
if ($ExtraIndexUrl) {
  Write-Host (T "  accélération matérielle : index PyTorch GPU ($ExtraIndexUrl)" "  hardware acceleration: PyTorch GPU index ($ExtraIndexUrl)")
  $indexArgs = @("--extra-index-url", $ExtraIndexUrl)
}
& uv pip install --python $Py @indexArgs --only-binary ":all:" -r requirements-drums.txt
if ($LASTEXITCODE -ne 0) { Fail "installation des dépendances impossible (voir ci-dessus)." "could not install the dependencies (see above)." }
Write-Host (T "  test sur une batterie synthétique…" "  testing on synthetic drums…")
& $Py (Join-Path $Here "reacue_drums.py") check --lang $L
if ($LASTEXITCODE -ne 0) { Fail "ADTOF ne fonctionne pas (voir ci-dessus)." "ADTOF does not work (see above)." }
Write-Host (T "  Transcription de batterie installée : utilisée automatiquement pour le prompteur (vue Batterie) quand un stem batterie existe." "  Drum transcription installed: used automatically for the prompter (Drums view) when a drum stem exists.")
exit 0
