param(
    [string]$TargetDir = 'C:\Docker-Projects\PON_Bikes_Automation'
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_support\PON.Update.Common.ps1')

Assert-PonStableTarget -TargetDir $TargetDir
Get-PonPreUpdateCommit -TargetDir $TargetDir | Out-Null

$release = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'RELEASE_VERSION.txt') -Raw).Trim()
$statePath = Join-Path $TargetDir '.update_state\last_update.json'

Write-Host ''
Write-Host 'PON Bikes Automation - 02 APPLY UPDATE' -ForegroundColor Cyan
Write-Host "Release: $release" -ForegroundColor DarkGray
Write-Host "Target:  $TargetDir" -ForegroundColor DarkGray
Write-Host ''

if (-not (Test-Path -LiteralPath (Join-Path $TargetDir 'compose.yaml'))) { throw "01 has not prepared the target folder: $TargetDir" }
if (-not (Test-Path -LiteralPath (Join-Path $TargetDir '.env'))) { throw '.env is missing. Run 01 or restore your previous .env first.' }
if (-not (Test-Path -LiteralPath $statePath)) { throw 'Update state is missing. Run 01_PREPARE_INSTALL.ps1 first.' }

$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
if ($state.release_version -ne $release) { throw "Prepared release $($state.release_version) does not match package release $release." }

if ($state.status -notin @('prepared','applied')) { throw 'Preparation did not complete. Finish 01 or use 03_ROLLBACK.' }

Push-Location $TargetDir
try {
    Write-Host 'Building and recreating web container...' -ForegroundColor Cyan
    & docker compose up -d --build --force-recreate web
    if ($LASTEXITCODE -ne 0) { Write-PonFail 'Docker build/recreate failed.'; throw 'docker compose up failed.' } else { Write-PonPass 'Docker web build/recreate completed.' }

    Write-Host 'Applying Django migrations...' -ForegroundColor Cyan
    & docker compose exec -T web python manage.py migrate
    if ($LASTEXITCODE -ne 0) { Write-PonFail 'Django migrate failed.'; throw 'Django migrate failed.' } else { Write-PonPass 'Django migrations applied.' }

    Write-Host 'Running Django system check...' -ForegroundColor Cyan
    & docker compose exec -T web python manage.py check
    if ($LASTEXITCODE -ne 0) { Write-PonFail 'Django system check failed.'; throw 'Django check failed.' } else { Write-PonPass 'Django system check passed.' }

    Write-Host 'Migration status:' -ForegroundColor Cyan
    & docker compose exec -T web python manage.py showmigrations receiving
    if ($LASTEXITCODE -ne 0) { throw 'Could not read receiving migration status.' }

    & docker compose ps
}
finally {
    Pop-Location
}

$state.status = 'applied'
$state | Add-Member -NotePropertyName applied_at -NotePropertyValue ((Get-Date).ToString('o')) -Force
$state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statePath -Encoding UTF8

Write-Host ''
Write-PonPass '02 completed successfully.'
Write-Host 'The stable app folder is now updated.' -ForegroundColor Green
Write-Host 'NEXT: run 04_VALIDATE.ps1.' -ForegroundColor Cyan
Write-Host 'If anything is wrong, run 03_ROLLBACK.ps1.' -ForegroundColor Yellow
