# Analyse de structure pour ReaCue (SongFormer, en local) — Windows / Structure analysis for ReaCue — Windows.
# Lancé par install_windows.ps1 (si tu réponds oui) ou par « Install ReaCue Structure.bat » ; ou :
#   powershell -ExecutionPolicy Bypass -File install\install_structure_windows.ps1 [-Lang fr|en]
# Environnement séparé .venv-structure + sources figées dans structure\ (n'abîme pas le .venv de ReaCue).
# Internet nécessaire : environ 3 Go (PyTorch, SongFormer, MuQ, MusicFM), 10 à 40 minutes. Relançable.
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

# révisions figées (mêmes valeurs que reacue_mcp/structure.py)
$SongFormerRev = "139b2aa3b14bd1c6d961d0994e9fc975f1ef7fd5"
$MuQRev = "28847ea50cd31ac4b8b6a7dacc051ad7d1c7606a"
$MusicFMRev = "b83ebedb401bcef639b26b05c0c8bee1dc2dfe71"

$env:Path = (Join-Path $env:USERPROFILE ".local\bin") + ";" + (Join-Path $env:USERPROFILE ".cargo\bin") + ";" + $env:Path
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Fail "uv introuvable : installe d'abord ReaCue (Install ReaCue.bat)." "uv not found: install ReaCue first (Install ReaCue.bat)."
}
Write-Host (T "  Analyse de structure (SongFormer) dans $Here\.venv-structure" "  Structure analysis (SongFormer) in $Here\.venv-structure")

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
& uv pip install --python $Py --only-binary ":all:" --no-binary "nnaudio,easydict,antlr4-python3-runtime" -r requirements-structure.txt
if ($LASTEXITCODE -ne 0) { Fail "installation des dépendances impossible (voir ci-dessus)." "could not install the dependencies (see above)." }
& uv pip install --python $Py --no-deps (Join-Path $TP "MuQ")
if ($LASTEXITCODE -ne 0) { Fail "installation de MuQ impossible." "could not install MuQ." }
Write-Host (T "  téléchargement des modèles (environ 2 Go) et test…" "  downloading the models (about 2 GB) and testing…")
& $Py (Join-Path $Here "reacue_structure.py") check --lang $L
if ($LASTEXITCODE -ne 0) { Fail "SongFormer ne fonctionne pas (voir ci-dessus)." "SongFormer does not work (see above)." }
Write-Host (T "  Analyse de structure installée : utilisée automatiquement par « Préparer » (réglage « Détection de structure »)." "  Structure analysis installed: used automatically by “Prepare” (“Structure detection” setting).")
exit 0
