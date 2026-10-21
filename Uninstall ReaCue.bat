@echo off
rem Double-clic pour desinstaller ReaCue (Windows). / Double-click to uninstall ReaCue (Windows).
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install\uninstall_windows.ps1" %*
echo.
pause
