param(
    [string]$TargetDir = 'C:\Docker-Projects\PON_Bikes_Automation'
)

$ErrorActionPreference = 'Continue'
. (Join-Path $PSScriptRoot '_support\PON.Update.Common.ps1')

Assert-PonStableTarget -TargetDir $TargetDir
if (-not (Test-Path -LiteralPath $TargetDir -PathType Container)) { throw 'Active installation is missing.' }

$logDir = Join-Path $TargetDir 'logs'
if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logPath = Join-Path $logDir ("Validation_{0}.txt" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
$failures = 0
$warnings = 0

function Write-Result {
    param([string]$Level,[string]$Message)
    $line = "[{0}] {1}" -f $Level, $Message
    Write-Host $line -ForegroundColor $(if ($Level -eq 'PASS') {'Green'} elseif ($Level -eq 'WARN') {'Yellow'} else {'Red'})
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
    if ($Level -eq 'FAIL') { $script:failures++ }
    if ($Level -eq 'WARN') { $script:warnings++ }
}

Write-Host ''
Write-Host 'PON Bikes Automation - 04 VALIDATE' -ForegroundColor Cyan
Write-Host "Target: $TargetDir" -ForegroundColor DarkGray
Write-Host ''
Set-Content -LiteralPath $logPath -Value ("PON validation started {0}" -f (Get-Date).ToString('o')) -Encoding UTF8

if (Test-Path -LiteralPath (Join-Path $TargetDir 'compose.yaml')) { Write-Result PASS 'compose.yaml exists.' } else { Write-Result FAIL 'compose.yaml is missing.' }
if (Test-Path -LiteralPath (Join-Path $TargetDir '.env')) { Write-Result PASS '.env exists.' } else { Write-Result FAIL '.env is missing.' }

try {
    Assert-PonStableTarget -TargetDir $TargetDir
    Get-PonPreUpdateCommit -TargetDir $TargetDir | Out-Null
    Write-Result PASS '.git exists and git status works in the active repository.'
    $updateStatePath = Join-Path $TargetDir '.update_state\last_update.json'
    $updateState = Get-Content -LiteralPath $updateStatePath -Raw | ConvertFrom-Json
    $commitPath = Join-Path $updateState.backup_dir 'PRE_UPDATE_COMMIT.txt'
    $dbBackup = Join-Path $updateState.backup_dir 'database_before_update.sql'
    if (-not (Test-Path -LiteralPath $commitPath)) { throw 'PRE_UPDATE_COMMIT.txt is missing.' }
    $commit = (Get-Content -LiteralPath $commitPath -Raw).Trim()
    if ($commit -notmatch '^[a-fA-F0-9]{40,64}$') { throw 'Invalid pre-update commit record.' }
    & git -C $TargetDir cat-file -e "${commit}^{commit}"
    if ($LASTEXITCODE -ne 0) { throw 'Pre-update commit is no longer accessible.' }
    if (-not (Test-Path -LiteralPath $dbBackup) -or (Get-Item -LiteralPath $dbBackup).Length -eq 0) { throw 'PostgreSQL backup is missing or empty.' }
    if (Test-Path -LiteralPath (Join-Path $updateState.backup_dir 'app')) { throw 'Unexpected full app backup.' }
    Write-Result PASS 'Pre-update commit and PostgreSQL backup exist; no full app backup.'
} catch { Write-Result FAIL $_.Exception.Message }

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Result FAIL 'Docker CLI is not available.'
} else {
    Write-Result PASS 'Docker CLI is available.'
}

if ($failures -eq 0) {
    Push-Location $TargetDir
    try {
        $psOutput = (& docker compose ps 2>&1 | Out-String)
        Add-Content -LiteralPath $logPath -Value "`n--- docker compose ps ---`n$psOutput" -Encoding UTF8
        $webId = (& docker compose ps -q web 2>$null | Select-Object -First 1)
        $dbId = (& docker compose ps -q db 2>$null | Select-Object -First 1)
        if ($webId) { Write-Result PASS 'Web container exists.' } else { Write-Result FAIL 'Web container is not running.' }
        if ($dbId) { Write-Result PASS 'Database container exists.' } else { Write-Result FAIL 'Database container is not running.' }

        if ($webId) {
            $checkOutput = (& docker compose exec -T web python manage.py check 2>&1 | Out-String)
            $checkCode = $LASTEXITCODE
            Add-Content -LiteralPath $logPath -Value "`n--- django check ---`n$checkOutput" -Encoding UTF8
            Write-Host $checkOutput
            if ($checkCode -eq 0) { Write-Result PASS 'Django system check passed.' } else { Write-Result FAIL 'Django system check failed.' }

            $migrations = (& docker compose exec -T web python manage.py showmigrations receiving 2>&1 | Out-String)
            Add-Content -LiteralPath $logPath -Value "`n--- receiving migrations ---`n$migrations" -Encoding UTF8
            if ($LASTEXITCODE -ne 0) {
                Write-Result FAIL 'Could not read migration status.'
            } elseif ($migrations -match '\[ \]') {
                Write-Result FAIL 'There are unapplied receiving migrations.'
            } else {
                Write-Result PASS 'All receiving migrations are applied.'
            }

            $modelState = (& docker compose exec -T web python manage.py makemigrations receiving --check --dry-run --verbosity 2 2>&1 | Out-String)
            $modelStateCode = $LASTEXITCODE
            Add-Content -LiteralPath $logPath -Value "`n--- model / migration state check ---`n$modelState" -Encoding UTF8
            if ($modelStateCode -eq 0) {
                Write-Result PASS 'Receiving models match migration state.'
            } else {
                Write-Host $modelState
                Write-Result FAIL 'Receiving models contain changes not represented by migrations.'
            }

            $counts = (& docker compose exec -T web python manage.py shell -c "from receiving.models import Container,Customer; print('Containers=',Container.objects.count()); print('Customers=',Customer.objects.count())" 2>&1 | Out-String)
            Add-Content -LiteralPath $logPath -Value "`n--- database counts ---`n$counts" -Encoding UTF8
            if ($LASTEXITCODE -eq 0) { Write-Result PASS 'Django can read the PostgreSQL database.' } else { Write-Result FAIL 'Django could not read the PostgreSQL database.' }

            $jobOrderCheck = (& docker compose exec -T web python manage.py shell -c "from django.db.models import Count; from receiving.models import Container; d=list(Container.objects.exclude(job_order='').values('job_order').annotate(n=Count('id')).filter(n__gt=1)); print(d); raise SystemExit(1 if d else 0)" 2>&1 | Out-String)
            Add-Content -LiteralPath $logPath -Value "`n--- Job Order uniqueness ---`n$jobOrderCheck" -Encoding UTF8
            if ($LASTEXITCODE -eq 0) { Write-Result PASS 'No duplicate non-blank Job Orders were found.' } else { Write-Result FAIL 'Duplicate Job Orders exist. Each Job Order must belong to only one container.' }

            $testCommand = 'docker compose exec -T web python manage.py test --verbosity 1 2>&1'
            $receivingTests = (& cmd.exe /d /s /c $testCommand | Out-String)
            $receivingTestCode = $LASTEXITCODE
            Add-Content -LiteralPath $logPath -Value "`n--- complete receiving test suite ---`n$receivingTests" -Encoding UTF8
            Write-Host $receivingTests
            if ($receivingTestCode -eq 0 -and $receivingTests -match 'Ran 68 tests' -and $receivingTests -match '(?m)^OK\s*$') { Write-Result PASS 'Complete 68-test suite passed.' } else { Write-Result FAIL 'Expected complete suite: 68 tests OK.' }
        }
    }
    finally {
        Pop-Location
    }
}

$envPath = Join-Path $TargetDir '.env'
if (Test-Path -LiteralPath $envPath) {
    $hostChecks = @(
        @{Key='PON_PRODUCT_HOST_DIR'; Required=$true},
        @{Key='PON_MOVES_HOST_DIR'; Required=$true},
        @{Key='PON_IMPORT_HOST_DIR'; Required=$true},
        @{Key='PON_REPORT_HOST_DIR'; Required=$true},
        @{Key='PON_HOST_PATH'; Required=$false}
    )
    foreach ($item in $hostChecks) {
        $value = Get-PonEnvValue -EnvPath $envPath -Key $item.Key -Default ''
        if (-not $value) {
            if ($item.Required) { Write-Result FAIL "$($item.Key) is not configured." } else { Write-Result WARN "$($item.Key) is not configured." }
        } elseif (Test-Path -LiteralPath $value) {
            Write-Result PASS "$($item.Key) exists: $value"
        } else {
            if ($item.Required) { Write-Result FAIL "$($item.Key) path is unavailable: $value" } else { Write-Result WARN "$($item.Key) path is currently unavailable: $value" }
        }
    }

    $productDir = Get-PonEnvValue -EnvPath $envPath -Key 'PON_PRODUCT_HOST_DIR' -Default ''
    if ($productDir) {
        $master = Join-Path $productDir 'products_pon_pbp_auto.xls'
        if (Test-Path -LiteralPath $master) { Write-Result PASS "Product master found: $master" } else { Write-Result WARN "Default product master was not found: $master" }
    }

    $preflightPath = Join-Path $TargetDir '.update_state\translogic_preflight.json'
    if (Test-Path -LiteralPath $preflightPath) {
        try {
            $preflight = Get-Content -LiteralPath $preflightPath -Raw | ConvertFrom-Json
            Add-Content -LiteralPath $logPath -Value ("`n--- Translogic preflight ---`n" + ($preflight | ConvertTo-Json -Depth 6)) -Encoding UTF8
            if ($preflight.import_pattern) {
                Write-Result PASS ("Real numbered Translogic pattern inspected on Windows: {0}; oldest: {1} {2}" -f $preflight.import_pattern, $preflight.import_oldest_file, $preflight.import_oldest_time)
            } elseif ($preflight.import_pattern_reason) {
                Write-Result WARN ("Numbered Translogic 1-5 pattern was not safely identified on Windows: {0}" -f $preflight.import_pattern_reason)
            }
        } catch {
            Write-Result WARN "Could not read Translogic preflight report: $($_.Exception.Message)"
        }
    } else {
        Write-Result WARN 'Translogic preflight report is missing.'
    }

    $directImportEnabled = Get-PonEnvValue -EnvPath $envPath -Key 'PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED' -Default '0'
    $directImportHost = Get-PonEnvValue -EnvPath $envPath -Key 'PON_TRANSLOGIC_IMPORT_HOST_DIR' -Default ''
    if ($directImportEnabled -eq '1') {
        if ($directImportHost -and (Test-Path -LiteralPath $directImportHost -PathType Container) -and (Test-PonDockerBind -HostPath $directImportHost -RequireWrite)) {
            Write-Result PASS "Direct Translogic import host folder remains read/write accessible to Docker: $directImportHost"
        } else {
            Write-Result FAIL "Direct Translogic import was enabled but read/write Docker access can no longer be verified: $directImportHost"
        }
    } else {
        Write-Result WARN 'Direct Translogic import mount is not enabled; Download/manual transfer remains the safe fallback.'
    }

    $directMovesEnabled = Get-PonEnvValue -EnvPath $envPath -Key 'PON_PRODUCT_MOVES_DIRECT_ENABLED' -Default '0'
    $directMovesHost = Get-PonEnvValue -EnvPath $envPath -Key 'PON_PRODUCT_MOVES_DIRECT_HOST_DIR' -Default ''
    if ($directMovesEnabled -eq '1') {
        $directMovesFile = Join-Path $directMovesHost 'PRODUCT_MOVES.CSV'
        if ($directMovesHost -and (Test-Path -LiteralPath $directMovesFile -PathType Leaf)) {
            Write-Result PASS "Direct PRODUCT_MOVES source remains accessible: $directMovesFile"
        } else {
            Write-Result WARN "Direct PRODUCT_MOVES was enabled during prepare but the file is not currently available; the app will fall back to the existing working-copy/manual-upload flow."
        }
    } else {
        Write-Result WARN 'Direct PRODUCT_MOVES mount is not enabled; existing working-copy/manual-upload flow remains active.'
    }

    Push-Location $TargetDir
    try {
        $masterCheck = (& docker compose exec -T web python manage.py shell -c "from pathlib import Path; from receiving.models import Customer; from receiving.views import _customer_catalog_paths; c=Customer.objects.get(code__iexact='PON'); p=Path(_customer_catalog_paths(c)['app_path']); f=p.open('rb'); assert f.read(1), 'Empty Product Master'; f.close(); print('Readable Product Master:', p)" 2>&1 | Out-String)
        $masterCheckCode = $LASTEXITCODE
        Add-Content -LiteralPath $logPath -Value "`n--- Product Master accessibility ---`n$masterCheck" -Encoding UTF8
        if ($masterCheckCode -eq 0) { Write-Result PASS 'Configured PON Product Master is readable in Docker.' }
        else { Write-Result FAIL 'Configured PON Product Master is inaccessible in Docker.' }

        $transferRuntime = (& docker compose exec -T web python manage.py shell -c "import json; from pathlib import Path; from django.conf import settings; from receiving.translogic_transfer import discover_numbered_import_set; d=Path(settings.PON_TRANSLOGIC_IMPORT_DIRECT_PATH); print(json.dumps(discover_numbered_import_set(d) if settings.PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED else {'available':False,'reason':'direct disabled'}, default=str))" 2>&1 | Out-String).Trim()
        $transferRuntimeCode = $LASTEXITCODE
        Add-Content -LiteralPath $logPath -Value "`n--- Translogic runtime discovery ---`n$transferRuntime" -Encoding UTF8
        if ($transferRuntimeCode -eq 0 -and $transferRuntime) {
            try {
                $runtimeDiscovery = $transferRuntime | ConvertFrom-Json
                if ($runtimeDiscovery.available) {
                    Write-Result PASS ("Docker sees the real numbered Translogic set: {0}; oldest: {1}" -f $runtimeDiscovery.pattern, $runtimeDiscovery.oldest.name)
                } elseif ($directImportEnabled -eq '1') {
                    Write-Result WARN ("Docker direct import is mounted, but the numbered 1-5 set is not safely usable: {0}" -f $runtimeDiscovery.reason)
                }
            } catch {
                Write-Result WARN 'Could not parse Docker Translogic discovery output.'
            }
        }

        $movesRuntime = (& docker compose exec -T web python manage.py shell -c "from pathlib import Path; from receiving.views import _configured_product_moves_path, _direct_product_moves_path; p=Path(_configured_product_moves_path()); print('mode=' + ('direct' if _direct_product_moves_path() else 'fallback')); print('path=' + str(p)); print('exists=' + str(p.is_file()))" 2>&1 | Out-String)
        $movesRuntimeCode = $LASTEXITCODE
        Add-Content -LiteralPath $logPath -Value "`n--- PRODUCT_MOVES runtime source ---`n$movesRuntime" -Encoding UTF8
        if ($movesRuntimeCode -eq 0 -and $movesRuntime -match 'exists=True') {
            Write-Result PASS 'PRODUCT_MOVES Refresh can currently read its configured runtime source.'
        } else {
            Write-Result WARN 'PRODUCT_MOVES source file is not currently visible; existing manual-upload/local bridge fallback is preserved.'
        }
    } finally {
        Pop-Location
    }

    $port = Get-PonEnvValue -EnvPath $envPath -Key 'PON_WEB_PORT' -Default '8001'
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri ("http://localhost:{0}/" -f $port) -TimeoutSec 10
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) { Write-Result PASS "HTTP application responded on port $port." } else { Write-Result WARN "HTTP application returned status $($response.StatusCode)." }
    } catch {
        Write-Result FAIL "Could not reach http://localhost:$port/ - $($_.Exception.Message)"
    }
}

# Continuity Snapshot is intentionally MANUAL from release 0930.1047 onward.
# 04 validates only; 05 creates the snapshot after the operator reviews this result.

Write-Host ''
Write-Host "Validation log: $logPath" -ForegroundColor Cyan
Write-Host "Failures: $failures   Warnings: $warnings" -ForegroundColor $(if ($failures -eq 0) {'Green'} else {'Red'})
if ($failures -gt 0) { exit 1 }
Write-Host ''
Write-Host '[PASS] Validation completed with zero failures.' -ForegroundColor Green
Write-Host 'NEXT:' -ForegroundColor Green
Write-Host '.\05_CREATE_CONTINUITY_SNAPSHOT.ps1' -ForegroundColor Green
exit 0
