@echo off
rem Double-clic : installe la separation de stems (Demucs) pour ReaCue (Windows).
rem Double-click: installs stem separation (Demucs) for ReaCue (Windows).
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install\install_stems_windows.ps1" %*
echo.
pause
