@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0_internal\Run.ps1" -Action shell
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo [FAIL] shell failed. Check OUTPUT\ for the run log.
exit /b %RESULT%
