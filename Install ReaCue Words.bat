@echo off
rem Double-clic : installe les paroles calees mot par mot (wav2vec2) et les paroles automatiques (Whisper) pour ReaCue (Windows).
rem Double-click: installs word-by-word lyrics timing (wav2vec2) and automatic lyrics (Whisper) for ReaCue (Windows).
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install\install_words_windows.ps1" %*
echo.
pause
