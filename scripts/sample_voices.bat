@echo off
rem AI Navigator - make short voice samples to compare (ASCII-only).
rem VOICEVOX (desktop app) must be running.
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0.."

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY (
  echo [!] Python not found. Install from https://www.python.org/downloads/
  pause
  exit /b 1
)

echo Making voice samples... (VOICEVOX must be running)
echo.
%PY% -m ai_navigator voice-sample --open
echo.
echo Listen to the .wav files in the voice_samples folder,
echo then set the number you like as SPEAKER in make_video.bat.
echo.
pause
