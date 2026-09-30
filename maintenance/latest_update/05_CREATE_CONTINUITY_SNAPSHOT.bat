@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp005_CREATE_CONTINUITY_SNAPSHOT.ps1"
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo Continuity Snapshot completed successfully.
) else (
  echo Continuity Snapshot FAILED. See the messages above.
)
pause
exit /b %RC%
