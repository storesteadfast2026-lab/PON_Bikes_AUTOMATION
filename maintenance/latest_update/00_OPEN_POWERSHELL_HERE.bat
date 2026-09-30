@echo off
setlocal
set "PON_UPDATE_DIR=%~dp0"
start "PON Bikes Automation Update" powershell.exe -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath $env:PON_UPDATE_DIR; Clear-Host; Write-Host 'PON Bikes Automation - Update Console' -ForegroundColor Cyan; Write-Host ''; Write-Host ('Current folder: ' + (Get-Location).Path) -ForegroundColor DarkGray; Write-Host ''; Write-Host 'Normal sequence:' -ForegroundColor White; Write-Host '  .\01_PREPARE_INSTALL.ps1' -ForegroundColor Yellow; Write-Host '  .\02_APPLY_UPDATE.ps1' -ForegroundColor Yellow; Write-Host '  .\04_VALIDATE.ps1' -ForegroundColor Yellow; Write-Host '  .\05_CREATE_CONTINUITY_SNAPSHOT.ps1' -ForegroundColor Yellow; Write-Host ''; Write-Host 'Rollback if required:' -ForegroundColor White; Write-Host '  .\03_ROLLBACK.ps1' -ForegroundColor Yellow; Write-Host ''"
endlocal
