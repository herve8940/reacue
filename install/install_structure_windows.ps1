# Analyse de structure pour ReaCue (SongFormer, en local) — Windows / Structure analysis for ReaCue — Windows.
# Lancé par install_windows.ps1 (si tu réponds oui) ou par « Install ReaCue Structure.bat » ; ou :
#   powershell -ExecutionPolicy Bypass -File install\install_structure_windows.ps1 [-Lang fr|en]
# Environnement séparé .venv-structure + sources figées dans structure\ (n'abîme pas le .venv de ReaCue).
# Internet nécessaire : environ 3 Go (PyTorch, SongFormer, MuQ, MusicFM), 10 à 40 minutes. Relançable.
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

# révisions figées (mêmes valeurs que reacue_mcp/structure.py)
$SongFormerRev = "139b2aa3b14bd1c6d961d0994e9fc975f1ef7fd5"
$MuQRev = "28847ea50cd31ac4b8b6a7dacc051ad7d1c7606a"
$MusicFMRev = "b83ebedb401bcef639b26b05c0c8bee1dc2dfe71"

$env:Path = (Join-Path $env:USERPROFILE ".local\bin") + ";" + (Join-Path $env:USERPROFILE ".cargo\bin") + ";" + $env:Path
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Fail "uv introuvable : installe d'abord ReaCue (Install ReaCue.bat)." "uv not found: install ReaCue first (Install ReaCue.bat)."
}
Write-Host (T "  Analyse de structure (SongFormer) dans $Here\.venv-structure" "  Structure analysis (SongFormer) in $Here\.venv-structure")

# Licences : accord explicite AVANT tout téléchargement (voir THIRD_PARTY_NOTICES.md).
# Installation non interactive : variable d'environnement REACUE_STRUCTURE_ACCEPT=yes.
# Accord mémorisé dans structure\.licenses_accepted.
$LicId = "songformer-ccby4+muq-weights-ccbync4+musicfm-unclear/v1"
$AcceptFile = Join-Path $Here "structure\.licenses_accepted"
$accepted = (Test-Path -LiteralPath $AcceptFile) -and (((Get-Content -LiteralPath $AcceptFile -TotalCount 1) -as [string]) -eq $LicId)
if (-not $accepted) {
  Write-Host ""
  Write-Host (T "  ┌─ Licences de l'analyse de structure ─────────────────────────────────────────" "  ┌─ Structure analysis licences ────────────────────────────────────────────────")
  Write-Host (T "  │ SongFormer (ASLP-lab) : CC BY 4.0." "  │ SongFormer (ASLP-lab): CC BY 4.0.")
  Write-Host (T "  │ MuQ (Tencent) : code MIT, poids CC BY-NC 4.0 → USAGE NON COMMERCIAL UNIQUEMENT." "  │ MuQ (Tencent): code MIT, weights CC BY-NC 4.0 → NON-COMMERCIAL USE ONLY.") -ForegroundColor Yellow
  Write-Host (T "  │ MusicFM (ByteDance) : code MIT ; licence du modèle MSD non précisée par ses auteurs." "  │ MusicFM (ByteDance): code MIT; licence of the MSD checkpoint not stated by its authors.")
  Write-Host (T "  │ Les modèles sont téléchargés depuis leurs auteurs ; tu es responsable du respect" "  │ The models are downloaded from their authors; you are responsible for complying")
  Write-Host (T "  │ de leurs licences. Détails : THIRD_PARTY_NOTICES.md (ceci n'est pas un avis juridique)." "  │ with their licences. Details: THIRD_PARTY_NOTICES.md (this is not legal advice).")
  Write-Host "  └──────────────────────────────────────────────────────────────────────────────"
  $Want = T "J'accepte" "I accept"
  if ($env:REACUE_STRUCTURE_ACCEPT -eq "yes") {
    Write-Host (T "  Licences acceptées (REACUE_STRUCTURE_ACCEPT=yes)." "  Licences accepted (REACUE_STRUCTURE_ACCEPT=yes).")
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
  New-Item -ItemType Directory -Path (Join-Path $Here "structure") -Force | Out-Null
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
Write-Host (T "  téléchargement de SongFormer, MuQ et MusicFM (versions figées)…" "  downloading SongFormer, MuQ and MusicFM (pinned versions)…")
New-Item -ItemType Directory -Path (Join-Path $Here "structure") -Force | Out-Null
$SF = Join-Path $Here "structure\SongFormer"
if (-not (Fetch "ASLP-lab/SongFormer" $SongFormerRev $SF)) { Fail "téléchargement de SongFormer impossible." "could not download SongFormer." }
$TP = Join-Path $SF "src\third_party"
if (-not (Fetch "tencent-ailab/MuQ" $MuQRev (Join-Path $TP "MuQ"))) { Fail "téléchargement de MuQ impossible." "could not download MuQ." }
if (-not (Fetch "minzwon/musicfm" $MusicFMRev (Join-Path $TP "musicfm"))) { Fail "téléchargement de MusicFM impossible." "could not download MusicFM." }

$Py = Join-Path $Here ".venv-structure\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Py)) {
  & uv venv .venv-structure --python 3.11
  if ($LASTEXITCODE -ne 0) { Fail "création de .venv-structure impossible." "could not create .venv-structure." }
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
# Audit matériel de l'environnement virtuel .venv-structure
$audit = $null
$mainPy = Join-Path $Here ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $mainPy) {
  try {
    $auditJson = & $mainPy (Join-Path $Here "reacue_gpu.py") audit $Py 2>$null
    if ($LASTEXITCODE -eq 0 -and $auditJson) {
      $audit = $auditJson | ConvertFrom-Json
    }
  } catch { }
}

if ($audit -and $audit.action -eq "reinstall") {
  Write-Host (T "  ! Réalignement matériel requis dans .venv-structure : $($audit.reason_fr)" `
                "  ! Hardware realignment needed in .venv-structure: $($audit.reason)") -ForegroundColor Yellow
  & uv pip uninstall --python $Py torch torchaudio torchvision 2>$null | Out-Null
  $torchVer = if ($audit.target_version) { $audit.target_version } else { if ($ExtraIndexUrl -match "cu128") { "2.8.0" } else { "2.4.1" } }
  $visionVer = if ($audit.target_vision_version) { $audit.target_vision_version } else { if ($torchVer -eq "2.8.0") { "0.23.0" } else { "0.19.1" } }
  Write-Host (T "  installation de PyTorch $torchVer avec accélération matérielle ($ExtraIndexUrl)…" `
                "  installing PyTorch $torchVer with hardware acceleration ($ExtraIndexUrl)…")
  if ($ExtraIndexUrl) {
    & uv pip install --python $Py "torch==$torchVer" "torchaudio==$torchVer" "torchvision==$visionVer" --index $ExtraIndexUrl --reinstall
    if ($LASTEXITCODE -ne 0) {
      Write-Host (T "  ! repli sur le mode standard" "  ! fallback to standard mode") -ForegroundColor Yellow
    }
  }
} elseif ($audit -and $audit.status -eq "optimal") {
  Write-Host (T "  accélération matérielle déjà optimale ($($audit.torch_version)) : aucun téléchargement nécessaire." `
                "  hardware acceleration already optimal ($($audit.torch_version)): no download needed.") -ForegroundColor Green
} else {
  # Premier install ou audit non disponible
  $torchVer = if ($ExtraIndexUrl -match "cu128") { "2.8.0" } else { "2.4.1" }
  $visionVer = if ($ExtraIndexUrl -match "cu128") { "0.23.0" } else { "0.19.1" }
  if ($ExtraIndexUrl) {
    Write-Host (T "  installation de PyTorch $torchVer avec accélération NVIDIA CUDA ($ExtraIndexUrl)…" `
                  "  installing PyTorch $torchVer with NVIDIA CUDA acceleration ($ExtraIndexUrl)…")
    & uv pip install --python $Py "torch==$torchVer" "torchaudio==$torchVer" "torchvision==$visionVer" --index $ExtraIndexUrl --reinstall
    if ($LASTEXITCODE -ne 0) {
      Write-Host (T "  ! repli sur le mode standard" "  ! fallback to standard mode") -ForegroundColor Yellow
    }
  }
}
$indexArgs = @()
if ($ExtraIndexUrl) {
  $indexArgs = @("--extra-index-url", $ExtraIndexUrl)
}
& uv pip install --python $Py @indexArgs --only-binary ":all:" --no-binary "nnaudio,easydict,antlr4-python3-runtime" -r requirements-structure.txt
if ($LASTEXITCODE -ne 0) { Fail "installation des dépendances impossible (voir ci-dessus)." "could not install the dependencies (see above)." }
& uv pip install --python $Py --no-deps (Join-Path $TP "MuQ")
if ($LASTEXITCODE -ne 0) { Fail "installation de MuQ impossible." "could not install MuQ." }
Write-Host (T "  recherche de modèles déjà téléchargés (ReaCue-labo, cache Hugging Face)…" "  looking for already-downloaded models (ReaCue-labo, Hugging Face cache)…")
& $Py (Join-Path $Here "reacue_structure.py") reuse --lang $L
Write-Host (T "  téléchargement des modèles manquants (jusqu'à 2 Go) et test…" "  downloading the missing models (up to 2 GB) and testing…")
& $Py (Join-Path $Here "reacue_structure.py") check --lang $L
if ($LASTEXITCODE -ne 0) { Fail "SongFormer ne fonctionne pas (voir ci-dessus)." "SongFormer does not work (see above)." }
Write-Host (T "  Analyse de structure installée : utilisée automatiquement par « Analyser et préparer » (réglage « Détection de structure »)." "  Structure analysis installed: used automatically by 'Analyse and prepare' ('Structure detection' setting).")
exit 0
