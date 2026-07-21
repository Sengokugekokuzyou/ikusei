@echo off
rem AI Navigator - Windows one-double-click video maker.
rem ASCII-only on purpose: a .bat with non-ASCII text breaks cmd parsing on
rem Japanese Windows. Japanese/emoji from Python still show via UTF-8 below.
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
setlocal EnableDelayedExpansion
cd /d "%~dp0.."

rem ==== VOICE ====  Change this number to pick the VOICEVOX voice.
rem   2 = Shikoku Metan (normal)   13 = Aoyama Ryusei   3 = Zundamon
rem   Compare voices: double-click sample_voices.bat (VOICEVOX running)
set "SPEAKER=2"

echo ============================================
echo    AI Navigator - make video (Windows)
echo ============================================
echo.

rem --- find Python (py launcher, then python) ---
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY (
  echo [!] Python not found.
  echo     Install from https://www.python.org/downloads/
  echo     and CHECK "Add python.exe to PATH", then run this again.
  echo.
  pause
  exit /b 1
)

echo [1/3] Preparing components (first run may take a moment)...
%PY% -m pip install --quiet --disable-pip-version-check imageio-ffmpeg
echo.

echo [2/3] Enter a topic, then press Enter.
echo       (Just press Enter to use "Claude Code vs Codex".)
echo       Start VOICEVOX first if you want narration voice.
set "TOPIC="
set /p "TOPIC=Topic: "
if "!TOPIC!"=="" set "TOPIC=Claude Code vs Codex"
echo.

echo [3/3] Generating... this takes a few minutes. Do NOT close this window.
echo.
%PY% -m ai_navigator run --topic "!TOPIC!" --video --voicevox --speaker !SPEAKER! --open

echo.
echo ============================================
echo    Done. The video is in the reports folder (video.mp4).
echo ============================================
echo.
pause
