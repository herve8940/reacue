@echo off
rem Double-clic : installe la reconnaissance d'accords (modele entraine) pour ReaCue (Windows).
rem Double-click: installs chord recognition (trained model) for ReaCue (Windows).
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install\install_chords_windows.ps1" %*
echo.
pause
