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

Assert-PonStableTarget -TargetDir $TargetDir
Get-PonPreUpdateCommit -TargetDir $TargetDir | Out-Null
$commitPath = Join-Path $backupDir 'PRE_UPDATE_COMMIT.txt'
$filesPath = Join-Path $backupDir 'UPDATE_FILES.txt'
$dbBackup = Join-Path $backupDir 'database_before_update.sql'
if (-not (Test-Path -LiteralPath $commitPath) -or -not (Test-Path -LiteralPath $filesPath)) { throw 'Git rollback metadata is missing. No files changed.' }
$preCommit = (Get-Content -LiteralPath $commitPath -Raw).Trim()
if ($preCommit -notmatch '^[a-fA-F0-9]{40,64}$') { throw 'Invalid pre-update commit.' }
& git -C $TargetDir cat-file -e "${preCommit}^{commit}"
if ($LASTEXITCODE -ne 0) { throw 'Pre-update commit is inaccessible. No files changed.' }
$updateFiles = @(Get-Content -LiteralPath $filesPath | Where-Object { $_.Trim() })
if ($updateFiles.Count -eq 0) { throw 'Rollback file list is empty.' }
foreach ($relative in $updateFiles) {
    if ($relative -match '(^[\\/]|:|(^|[\\/])\.\.([\\/]|$)|(^|[\\/])\.git([\\/]|$))') { throw 'Unsafe rollback path.' }
}
if (-not (Test-Path -LiteralPath $dbBackup) -or (Get-Item -LiteralPath $dbBackup).Length -eq 0) { throw 'PostgreSQL backup is missing or empty.' }
Write-Host "Pre-update commit: $preCommit" -ForegroundColor Yellow
Write-Host 'Rollback restores the update files from Git and the previous PostgreSQL snapshot.' -ForegroundColor Yellow
if (-not $Force) {
    $answer = Read-Host 'Type ROLLBACK to continue'
    if ($answer -ne 'ROLLBACK') { Write-Host 'Rollback cancelled.'; exit 0 }
}
Push-Location $TargetDir
try {
    & docker compose stop web
    if ($LASTEXITCODE -ne 0) { throw 'Could not stop web before rollback.' }
} finally { Pop-Location }
& git -C $TargetDir restore --source=$preCommit --staged --worktree -- @updateFiles
if ($LASTEXITCODE -ne 0) { throw 'Git code restore failed.' }
$envBackup = Join-Path $backupDir '.env'
if (Test-Path -LiteralPath $envBackup) { Copy-Item -LiteralPath $envBackup -Destination (Join-Path $TargetDir '.env') -Force }
Restore-PonDatabase -InstallDir $TargetDir -InputFile $dbBackup
Get-PonPreUpdateCommit -TargetDir $TargetDir | Out-Null

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
