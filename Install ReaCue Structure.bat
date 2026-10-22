@echo off
rem Double-clic : installe l'analyse de structure (SongFormer) pour ReaCue (Windows).
rem Double-click: installs structure analysis (SongFormer) for ReaCue (Windows).
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install\install_structure_windows.ps1" %*
echo.
pause
