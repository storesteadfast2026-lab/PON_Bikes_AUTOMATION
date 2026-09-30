@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Create_Continuity_Snapshot.ps1" -ProjectDir "%CD%"
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo Continuity Snapshot completed successfully.
) else (
  echo Continuity Snapshot FAILED. See the messages above.
)
pause
exit /b %RC%
