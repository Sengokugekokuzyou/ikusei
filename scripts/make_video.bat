@echo off
rem AI Navigator - Windows one-double-click video maker.
rem Put VOICEVOX (desktop app) running first for real audio; otherwise silent.
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0.."

echo ============================================
echo    AI Navigator - 動画をつくる (Windows)
echo ============================================
echo.

rem --- find Python (py launcher, then python) ---
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY (
  echo [!] Python が見つかりませんでした。
  echo     https://www.python.org/downloads/ から Python をインストールし、
  echo     インストール画面の "Add python.exe to PATH" に必ずチェックしてください。
  echo     その後、このファイルをもう一度ダブルクリックしてください。
  echo.
  pause
  exit /b 1
)

echo [1/3] 必要な部品を確認しています（初回だけ少し時間がかかります）...
%PY% -m pip install --quiet --disable-pip-version-check imageio-ffmpeg
echo.

echo [2/3] 動画のテーマを決めます。
echo     ※ VOICEVOX（デスクトップ版）を起動しておくと、声が入ります。
echo       起動していないと音声なし（無音）で作られます。
echo.
set "TOPIC="
set /p "TOPIC=テーマを入力して Enter（空のまま Enter で「Claude Code vs Codex」）: "
if "!TOPIC!"=="" set "TOPIC=Claude Code vs Codex"
echo.

echo [3/3] 生成中...（数分かかります。このウィンドウは閉じないでください）
echo.
%PY% -m ai_navigator run --topic "!TOPIC!" --video --voicevox --speaker 3 --open

echo.
echo ============================================
echo    完了しました。
echo    動画は reports フォルダの中の video.mp4 です。
echo ============================================
echo.
pause
