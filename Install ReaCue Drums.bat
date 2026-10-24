@echo off
rem Double-clic : installe la transcription de batterie (ADTOF) pour ReaCue (Windows).
rem Double-click: installs drum transcription (ADTOF) for ReaCue (Windows).
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install\install_drums_windows.ps1" %*
echo.
pause
