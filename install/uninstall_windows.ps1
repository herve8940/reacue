# Désinstallation de ReaCue (Windows) / ReaCue uninstaller (Windows).
# Retire les scripts REAPER, la ligne de démarrage du pont, les actions et l'entrée Claude Desktop.
#   powershell -ExecutionPolicy Bypass -File install\uninstall_windows.ps1 [-Purge]
param([switch]$Purge, [string]$ReaperDir = "")
$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$env:PYTHONUTF8 = "1"
$Here = Split-Path -Parent $PSScriptRoot
if (-not $ReaperDir) {
  $ReaperDir = if ($env:REAPER_RESOURCE_PATH) { $env:REAPER_RESOURCE_PATH } else { Join-Path $env:APPDATA "REAPER" }
}
$Py = Join-Path $Here ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Py)) { $Py = "python" }
$a = @((Join-Path $Here "install\reacue_setup.py"), "uninstall", "--reaper-dir", $ReaperDir)
if ($Purge) { $a += "--purge" }
& $Py @a
exit $LASTEXITCODE
