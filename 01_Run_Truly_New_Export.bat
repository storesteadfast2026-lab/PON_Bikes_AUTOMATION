@echo off
setlocal EnableExtensions
chcp 65001 >nul
title PON - Truly New Measurements
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Export_PON_Truly_New_Measurements.ps1"
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
    echo [FAIL] Export did not complete successfully. Check OUTPUT\ logs.
) else (
    echo [OK] Script completed. Review the Excel and log in OUTPUT\.
)
echo.
pause
exit /b %EXITCODE%
