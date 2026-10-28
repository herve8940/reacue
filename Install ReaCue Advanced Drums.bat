@echo off
cd /d "%~dp0"
uv run --no-project --python 3.12 python install/install_drums_advanced.py
if errorlevel 1 (pause & exit /b 1)
pause
