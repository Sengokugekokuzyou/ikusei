@echo off
rem AI Navigator - one double-click updater (ASCII-only on purpose).
rem Downloads the latest version from GitHub and copies it over the local files.
rem Your reports\ and assets\ are NOT touched (no purge).
chcp 65001 >nul
setlocal

rem Resolve the project root (the folder that contains this scripts\ folder).
pushd "%~dp0.."
set "REPO_DIR=%CD%"
popd

set "URL=https://codeload.github.com/Sengokugekokuzyou/ikusei/zip/refs/heads/claude/ai-navigator-youtube-automation-2xsygi"
set "ZIP=%TEMP%\ainav_update.zip"
set "EXDIR=%TEMP%\ainav_update"

echo ============================================
echo    AI Navigator - update to latest
echo ============================================
echo.

echo [1/3] Downloading the latest version...
if exist "%ZIP%" del /q "%ZIP%"
curl -L -f -o "%ZIP%" "%URL%"
if errorlevel 1 (
  echo [!] Download failed. Check your internet connection and try again.
  pause
  exit /b 1
)

echo [2/3] Extracting...
if exist "%EXDIR%" rmdir /s /q "%EXDIR%"
mkdir "%EXDIR%"
tar -xf "%ZIP%" -C "%EXDIR%"
set "SRC="
for /d %%D in ("%EXDIR%\*") do set "SRC=%%D"
if not defined SRC (
  echo [!] Extract failed.
  pause
  exit /b 1
)

echo [3/3] Updating files (your videos and assets are kept)...
robocopy "%SRC%" "%REPO_DIR%" /E /IS /IT /NFL /NDL /NJH /NJS /NP >nul

del /q "%ZIP%" >nul 2>nul
rmdir /s /q "%EXDIR%" >nul 2>nul

echo.
echo ============================================
echo    Update complete. Now run make_video.bat.
echo ============================================
echo.
pause
