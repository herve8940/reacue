# Reconnaissance d'accords pour ReaCue (modèle entraîné, en local) — Windows / Chord recognition for ReaCue — Windows.
# Lancé par « Install ReaCue Chords.bat » ; ou :
#   powershell -ExecutionPolicy Bypass -File install\install_chords_windows.ps1 [-Lang fr|en]
# Environnement séparé .venv-chords + modèle figé dans chords\model (n'abîme pas le .venv de ReaCue).
# Internet nécessaire : environ 800 Mo (PyTorch, déjà en cache si les stems sont installés) + 60 Mo (modèle),
# 2 à 10 minutes. Relançable sans risque.
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

# révision figée (même valeur que reacue_mcp/chord_model.py)
$ModelRepo = "music-x-lab/ISMIR2019-Large-Vocabulary-Chord-Recognition"
$ModelRev = "481f4ce703f8822b99f4037e9104ba1760e21ea3"

$env:Path = (Join-Path $env:USERPROFILE ".local\bin") + ";" + (Join-Path $env:USERPROFILE ".cargo\bin") + ";" + $env:Path
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Fail "uv introuvable : installe d'abord ReaCue (Install ReaCue.bat)." "uv not found: install ReaCue first (Install ReaCue.bat)."
}
Write-Host (T "  Reconnaissance d'accords dans $Here\.venv-chords" "  Chord recognition in $Here\.venv-chords")
Write-Host (T "  Licence : modèle de Junyan Jiang, Ke Chen, Wei Li et Gus Xia (ISMIR 2019, Music X Lab), code et poids" "  Licence: model by Junyan Jiang, Ke Chen, Wei Li and Gus Xia (ISMIR 2019, Music X Lab), code and weights")
Write-Host (T "  sous licence MIT, téléchargés depuis GitHub. Détails : THIRD_PARTY_NOTICES.md" "  under the MIT licence, downloaded from GitHub. Details: THIRD_PARTY_NOTICES.md")

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
Write-Host (T "  téléchargement du modèle d'accords (version figée, environ 60 Mo)…" "  downloading the chord model (pinned version, about 60 MB)…")
New-Item -ItemType Directory -Path (Join-Path $Here "chords") -Force | Out-Null
if (-not (Fetch $ModelRepo $ModelRev (Join-Path $Here "chords\model"))) { Fail "téléchargement du modèle d'accords impossible." "could not download the chord model." }

$Py = Join-Path $Here ".venv-chords\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Py)) {
  & uv venv .venv-chords --python 3.12
  if ($LASTEXITCODE -ne 0) { Fail "création de .venv-chords impossible." "could not create .venv-chords." }
}
Write-Host (T "  installation de PyTorch et de librosa (plusieurs minutes la première fois)…" "  installing PyTorch and librosa (several minutes the first time)…")
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
& uv pip install --python $Py @indexArgs --only-binary ":all:" -r requirements-chords.txt
if ($LASTEXITCODE -ne 0) { Fail "installation des dépendances impossible (voir ci-dessus)." "could not install the dependencies (see above)." }
Write-Host (T "  test du modèle sur un audio synthétique…" "  testing the model on synthetic audio…")
& $Py (Join-Path $Here "reacue_chords.py") check --lang $L
if ($LASTEXITCODE -ne 0) { Fail "le modèle d'accords ne fonctionne pas (voir ci-dessus)." "the chord model does not work (see above)." }
Write-Host (T "  Reconnaissance d'accords installée : utilisée automatiquement pour le prompteur et la grille PDF (réglage « chords_engine »)." "  Chord recognition installed: used automatically for the prompter and the PDF chart ('chords_engine' setting).")
exit 0
