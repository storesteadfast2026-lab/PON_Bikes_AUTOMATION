param(
    [string]$TargetDir = 'C:\Docker-Projects\PON_Bikes_Automation',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_support\PON.Update.Common.ps1')

$backupRoot = 'C:\Docker-Projects\PON_Bikes_Automation_Backups'
$statePath = Join-Path $TargetDir '.update_state\last_update.json'

Write-Host ''
Write-Host 'PON Bikes Automation - 03 ROLLBACK LAST UPDATE' -ForegroundColor Yellow
Write-Host ''

$state = $null
if (Test-Path -LiteralPath $statePath) {
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
}

$backupDir = ''
if ($state -and $state.backup_dir) {
    $backupDir = [string]$state.backup_dir
} elseif (Test-Path -LiteralPath (Join-Path $backupRoot 'LAST_BACKUP.txt')) {
    $backupDir = (Get-Content -LiteralPath (Join-Path $backupRoot 'LAST_BACKUP.txt') -Raw).Trim()
}

if (-not $backupDir -or -not (Test-Path -LiteralPath $backupDir)) {
    throw 'No rollback snapshot was found.'
}

$appBackup = Join-Path $backupDir 'app'
$dbBackup = Join-Path $backupDir 'database_before_update.sql'
if (-not (Test-Path -LiteralPath $appBackup)) { throw "Application backup not found: $appBackup" }

Write-Host "Rollback snapshot: $backupDir" -ForegroundColor Yellow
Write-Host 'This will restore the previous application files and database snapshot.' -ForegroundColor Yellow
if (-not $Force) {
    $answer = Read-Host 'Type ROLLBACK to continue'
    if ($answer -ne 'ROLLBACK') {
        Write-Host 'Rollback cancelled.' -ForegroundColor Cyan
        exit 0
    }
}

if (Test-Path -LiteralPath (Join-Path $TargetDir 'compose.yaml')) {
    Push-Location $TargetDir
    try { & docker compose stop web | Out-Host } finally { Pop-Location }
}

if (Test-Path -LiteralPath (Join-Path $backupDir 'GIT_EXISTED.txt')) {
    if (-not (Test-Path -LiteralPath (Join-Path $TargetDir '.git'))) { throw 'Existing Git repository is missing; rollback will not recreate it.' }
    & git -C $TargetDir status
    if ($LASTEXITCODE -ne 0) { throw 'Existing Git repository is inaccessible; rollback stopped.' }
}

Write-Host 'Restoring previous application files...' -ForegroundColor Cyan
if (-not (Test-Path -LiteralPath $TargetDir)) { New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null }
Clear-PonDirectory -Path $TargetDir
Copy-PonTree -Source $appBackup -Destination $TargetDir

if (Test-Path -LiteralPath $dbBackup) {
    Write-Host 'Restoring previous PostgreSQL snapshot...' -ForegroundColor Cyan
    Restore-PonDatabase -InstallDir $TargetDir -InputFile $dbBackup
} else {
    Write-PonWarn 'No database snapshot exists; only application files will be restored.'
}

Push-Location $TargetDir
try {
    Write-Host 'Rebuilding previous web version...' -ForegroundColor Cyan
    & docker compose up -d --build --force-recreate web
    if ($LASTEXITCODE -ne 0) { throw 'Could not restart previous web version.' }
    & docker compose exec -T web python manage.py check
    if ($LASTEXITCODE -ne 0) { throw 'Restored version failed Django check.' }
    & docker compose ps
}
finally {
    Pop-Location
}

$marker = Join-Path $backupDir ("ROLLBACK_COMPLETED_{0}.txt" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
Set-Content -LiteralPath $marker -Value ("Rollback completed at {0}" -f (Get-Date).ToString('o')) -Encoding UTF8

Write-Host ''
Write-PonPass '03 rollback completed successfully.'
Write-Host "Restored from: $backupDir" -ForegroundColor Green
