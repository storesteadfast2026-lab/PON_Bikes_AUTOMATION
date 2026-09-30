param(
    [string]$TargetDir = 'C:\Docker-Projects\PON_Bikes_Automation',
    [string]$CurrentInstallDir = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_support\PON.Update.Common.ps1')

$release = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'RELEASE_VERSION.txt') -Raw).Trim()
$payload = Join-Path $PSScriptRoot 'payload'
$backupRoot = 'C:\Docker-Projects\PON_Bikes_Automation_Backups'
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupDir = Join-Path $backupRoot ("{0}_before_{1}" -f $timestamp, $release)

Write-Host ''
Write-Host "PON Bikes Automation - 01 PREPARE INSTALL" -ForegroundColor Cyan
Write-Host "Release: $release" -ForegroundColor DarkGray
Write-Host "Stable installation: $TargetDir" -ForegroundColor DarkGray
Write-Host ''

if (-not (Test-Path -LiteralPath $payload)) { throw "Payload folder not found: $payload" }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker CLI was not found. Start Docker Desktop first.' }

$manifestPath = Join-Path $PSScriptRoot 'PACKAGE_MANIFEST_SHA256.txt'
if (Test-Path -LiteralPath $manifestPath) {
    Write-Host 'Verifying update package integrity...' -ForegroundColor Cyan
    foreach ($line in Get-Content -LiteralPath $manifestPath) {
        if (-not $line.Trim()) { continue }
        $parts = $line -split "`t", 2
        if ($parts.Count -ne 2) { throw "Invalid manifest line: $line" }
        $expected = $parts[0].Trim().ToLowerInvariant()
        $relative = $parts[1].Trim()
        $filePath = Join-Path $PSScriptRoot $relative
        if (-not (Test-Path -LiteralPath $filePath)) { throw "Package file missing: $relative" }
        $actual = (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $expected) { throw "Package integrity check failed: $relative" }
    }
    Write-PonPass 'Package integrity: OK'
}

# No writes to the installation or backup area before Git and source checks pass.
Assert-PonStableTarget -TargetDir $TargetDir
if ($CurrentInstallDir -and [IO.Path]::GetFullPath($CurrentInstallDir).TrimEnd('\') -ine [IO.Path]::GetFullPath($TargetDir).TrimEnd('\')) {
    throw 'Only the stable active installation is supported.'
}
$preCommit = Get-PonPreUpdateCommit -TargetDir $TargetDir
if (-not (Test-Path -LiteralPath (Join-Path $TargetDir 'compose.yaml'))) { throw 'Active installation not found.' }
if (-not (Test-Path -LiteralPath (Join-Path $TargetDir '.env'))) { throw 'Existing .env is required.' }
if (Test-Path -LiteralPath (Join-Path $payload '.git')) { throw 'Payload must not contain .git.' }
$updateFiles = @(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'UPDATE_FILES.txt') | Where-Object { $_.Trim() })
if ($updateFiles.Count -eq 0) { throw 'Empty update file list.' }
foreach ($relative in $updateFiles) {
    if ($relative -match '(^[\\/]|:|(^|[\\/])\.\.([\\/]|$)|(^|[\\/])\.git([\\/]|$))') { throw 'Unsafe update path.' }
    if (-not (Test-Path -LiteralPath (Join-Path $payload $relative) -PathType Leaf)) { throw "Missing payload: $relative" }
    & git -C $TargetDir ls-files --error-unmatch -- $relative | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Commit the current application file before updating: $relative" }
}
& git -C $TargetDir diff --quiet HEAD -- @updateFiles
if ($LASTEXITCODE -ne 0) { throw 'Update files differ from HEAD. Commit the current validated application before updating; no files changed.' }
foreach ($line in Get-Content -LiteralPath (Join-Path $PSScriptRoot 'BASE_FILES_SHA256.txt')) {
    $parts = $line -split "`t", 2
    $actual = (Get-FileHash -LiteralPath (Join-Path $TargetDir $parts[1]) -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $parts[0]) { throw "Base file differs from validated 1001.0832: $($parts[1])" }
}

New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Set-Content -LiteralPath (Join-Path $backupDir 'PRE_UPDATE_COMMIT.txt') -Value $preCommit -Encoding ASCII
Copy-Item -LiteralPath (Join-Path $TargetDir '.env') -Destination (Join-Path $backupDir '.env') -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'UPDATE_FILES.txt') -Destination (Join-Path $backupDir 'UPDATE_FILES.txt') -Force
$dbBackup = Join-Path $backupDir 'database_before_update.sql'
Backup-PonDatabase -InstallDir $TargetDir -OutputFile $dbBackup
if (-not (Test-Path -LiteralPath $dbBackup) -or (Get-Item -LiteralPath $dbBackup).Length -eq 0) { throw 'PostgreSQL backup is empty or missing.' }
Write-PonPass "PostgreSQL backup: $dbBackup"
Write-PonPass "Pre-update commit: $preCommit"

# Record recovery metadata before the first application-file replacement so a
# failed prepare can also use 03_ROLLBACK.
$stateDir = Join-Path $TargetDir '.update_state'
New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
$pendingState = [ordered]@{
    release_version = $release
    prepared_at = (Get-Date).ToString('o')
    target_dir = $TargetDir
    previous_install_dir = $TargetDir
    backup_dir = $backupDir
    database_backup = $dbBackup
    first_stable_install = $false
    git_existed_before = $true
    pre_update_commit = $preCommit
    status = 'preparing'
}
$pendingState | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $stateDir 'last_update.json') -Encoding UTF8
Set-Content -LiteralPath (Join-Path $backupRoot 'LAST_BACKUP.txt') -Value $backupDir -Encoding UTF8

# Update only the listed application files in place. No tree clearing, app snapshot,
# active-folder recreation, .git copy, .env overwrite or continuity relocation.
foreach ($relative in $updateFiles) {
    $destination = Join-Path $TargetDir $relative
    Copy-Item -LiteralPath (Join-Path $payload $relative) -Destination $destination -Force
}
if ((Get-PonPreUpdateCommit -TargetDir $TargetDir) -ne $preCommit) { throw 'Git HEAD changed during preparation.' }
$previous = $TargetDir
$firstInstall = $false
$gitExisted = $true

$activeEnv = Join-Path $TargetDir '.env'
foreach ($key in @('PON_MOVES_HOST_DIR','PON_IMPORT_HOST_DIR','PON_REPORT_HOST_DIR')) {
    $pathValue = Get-PonEnvValue -EnvPath $activeEnv -Key $key -Default ''
    if ($pathValue -and $pathValue -match '^[Cc]:[\/]') {
        if (-not (Test-Path -LiteralPath $pathValue)) {
            New-Item -ItemType Directory -Path $pathValue -Force | Out-Null
            Write-Host "Created local working folder for ${key}: $pathValue" -ForegroundColor Green
        }
    }
}

# Inspect the real Translogic paths before enabling any direct integration.
# Existing local bridge folders remain the fallback unless Docker can mount the real source/destination safely.
Write-Host ''
Write-Host 'Inspecting current Translogic paths...' -ForegroundColor Cyan

$translogicPreflight = [ordered]@{
    inspected_at = (Get-Date).ToString('o')
    import_display_file = ''
    import_display_dir = ''
    import_host_accessible = $false
    import_pattern = ''
    import_pattern_extension = ''
    import_oldest_file = ''
    import_oldest_time = ''
    import_pattern_reason = ''
    import_docker_direct = $false
    import_docker_host_dir = ''
    product_moves_display_file = ''
    product_moves_display_dir = ''
    product_moves_host_accessible = $false
    product_moves_docker_direct = $false
    product_moves_docker_host_dir = ''
}

$upstockDisplay = Get-PonEnvValue -EnvPath $activeEnv -Key 'PON_UPSTOCK_FINAL_DISPLAY' -Default ''
if (-not $upstockDisplay) { $upstockDisplay = Get-PonEnvValue -EnvPath $activeEnv -Key 'PON_UPSTOCKSERIAL_PATH' -Default '' }
$translogicPreflight.import_display_file = $upstockDisplay
$importDisplayDir = ''
if ($upstockDisplay) {
    try { $importDisplayDir = Split-Path -Parent $upstockDisplay } catch { $importDisplayDir = '' }
}
$translogicPreflight.import_display_dir = $importDisplayDir

if ($importDisplayDir -and (Test-Path -LiteralPath $importDisplayDir -PathType Container)) {
    $translogicPreflight.import_host_accessible = $true
    $patternInfo = Get-PonNumberedImportPattern -Directory $importDisplayDir
    $translogicPreflight.import_pattern = $patternInfo.pattern
    $translogicPreflight.import_pattern_extension = $patternInfo.extension
    $translogicPreflight.import_oldest_file = $patternInfo.oldest_name
    $translogicPreflight.import_oldest_time = $patternInfo.oldest_time
    $translogicPreflight.import_pattern_reason = $patternInfo.reason
    if ($patternInfo.available) {
        Write-Host ("New Product Import numbered pattern found: {0}" -f $patternInfo.pattern) -ForegroundColor Green
        Write-Host ("Oldest current file: {0}  {1}" -f $patternInfo.oldest_name, $patternInfo.oldest_time) -ForegroundColor Green
    } else {
        Write-Host ("Numbered Translogic file set not safely identified: {0}" -f $patternInfo.reason) -ForegroundColor Yellow
    }
} elseif ($importDisplayDir) {
    Write-Host "Translogic import folder is not accessible in this Windows session: $importDisplayDir" -ForegroundColor Yellow
}

$importCandidates = @()
if ($importDisplayDir -and (Test-Path -LiteralPath $importDisplayDir -PathType Container)) { $importCandidates += $importDisplayDir }
if ($importDisplayDir) {
    $importUnc = Resolve-PonMappedDrivePath -Path $importDisplayDir
    if ($importUnc -and (Test-Path -LiteralPath $importUnc -PathType Container)) { $importCandidates += $importUnc }
}
$existingImportEnabled = Get-PonEnvValue -EnvPath $activeEnv -Key 'PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED' -Default '0'
$existingImportDirect = Get-PonEnvValue -EnvPath $activeEnv -Key 'PON_TRANSLOGIC_IMPORT_HOST_DIR' -Default ''
if ($existingImportEnabled -eq '1' -and $existingImportDirect -and (Test-Path -LiteralPath $existingImportDirect -PathType Container)) {
    $importCandidates += $existingImportDirect
}
$importCandidates = @($importCandidates | Select-Object -Unique)
$verifiedImportHost = ''
foreach ($candidate in $importCandidates) {
    if (Test-PonDockerBind -HostPath $candidate -RequireWrite) {
        $verifiedImportHost = $candidate
        break
    }
}
if ($verifiedImportHost) {
    Set-PonEnvValue -EnvPath $activeEnv -Key 'PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED' -Value '1'
    Set-PonEnvValue -EnvPath $activeEnv -Key 'PON_TRANSLOGIC_IMPORT_HOST_DIR' -Value $verifiedImportHost
    $translogicPreflight.import_docker_direct = $true
    $translogicPreflight.import_docker_host_dir = $verifiedImportHost
    Write-Host "Docker direct Translogic import mount: READ/WRITE VERIFIED ($verifiedImportHost)" -ForegroundColor Green

    # If the mapped-drive spelling was not visible but its resolved UNC path is,
    # inspect that same verified real folder for the numbered 1-5 files.
    if (-not $translogicPreflight.import_pattern) {
        $verifiedPatternInfo = Get-PonNumberedImportPattern -Directory $verifiedImportHost
        $translogicPreflight.import_pattern = $verifiedPatternInfo.pattern
        $translogicPreflight.import_pattern_extension = $verifiedPatternInfo.extension
        $translogicPreflight.import_oldest_file = $verifiedPatternInfo.oldest_name
        $translogicPreflight.import_oldest_time = $verifiedPatternInfo.oldest_time
        $translogicPreflight.import_pattern_reason = $verifiedPatternInfo.reason
        if ($verifiedPatternInfo.available) {
            Write-Host ("New Product Import numbered pattern found on verified path: {0}" -f $verifiedPatternInfo.pattern) -ForegroundColor Green
            Write-Host ("Oldest current file: {0}  {1}" -f $verifiedPatternInfo.oldest_name, $verifiedPatternInfo.oldest_time) -ForegroundColor Green
        }
    }
} else {
    $safeImportFallback = (Join-Path $TargetDir 'sample_translogic_import_direct').Replace('\','/')
    Set-PonEnvValue -EnvPath $activeEnv -Key 'PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED' -Value '0'
    Set-PonEnvValue -EnvPath $activeEnv -Key 'PON_TRANSLOGIC_IMPORT_HOST_DIR' -Value $safeImportFallback
    Write-PonWarn 'Docker direct Translogic import mount: NOT READ/WRITE VERIFIED. Download/manual transfer remains active.'
}

$movesDisplay = Get-PonEnvValue -EnvPath $activeEnv -Key 'PON_PRODUCT_MOVES_SOURCE_DISPLAY' -Default ''
if (-not $movesDisplay) { $movesDisplay = Get-PonEnvValue -EnvPath $activeEnv -Key 'PON_PRODUCT_MOVES_PATH' -Default '' }
$translogicPreflight.product_moves_display_file = $movesDisplay
$movesDisplayDir = ''
if ($movesDisplay) {
    try { $movesDisplayDir = Split-Path -Parent $movesDisplay } catch { $movesDisplayDir = '' }
}
$translogicPreflight.product_moves_display_dir = $movesDisplayDir
if ($movesDisplay -and (Test-Path -LiteralPath $movesDisplay -PathType Leaf)) {
    $translogicPreflight.product_moves_host_accessible = $true
    Write-Host "PRODUCT_MOVES host source exists: $movesDisplay" -ForegroundColor Green
} elseif ($movesDisplay) {
    Write-Host "PRODUCT_MOVES host source is not accessible in this Windows session: $movesDisplay" -ForegroundColor Yellow
}

$movesCandidates = @()
if ($movesDisplayDir -and (Test-Path -LiteralPath $movesDisplayDir -PathType Container)) { $movesCandidates += $movesDisplayDir }
if ($movesDisplayDir) {
    $movesUnc = Resolve-PonMappedDrivePath -Path $movesDisplayDir
    if ($movesUnc -and (Test-Path -LiteralPath $movesUnc -PathType Container)) { $movesCandidates += $movesUnc }
}
$existingMovesEnabled = Get-PonEnvValue -EnvPath $activeEnv -Key 'PON_PRODUCT_MOVES_DIRECT_ENABLED' -Default '0'
$existingMovesDirect = Get-PonEnvValue -EnvPath $activeEnv -Key 'PON_PRODUCT_MOVES_DIRECT_HOST_DIR' -Default ''
if ($existingMovesEnabled -eq '1' -and $existingMovesDirect -and (Test-Path -LiteralPath $existingMovesDirect -PathType Container)) {
    $movesCandidates += $existingMovesDirect
}
$movesCandidates = @($movesCandidates | Select-Object -Unique)
$verifiedMovesHost = ''
foreach ($candidate in $movesCandidates) {
    $candidateFile = Join-Path $candidate 'PRODUCT_MOVES.CSV'
    if ((Test-Path -LiteralPath $candidateFile -PathType Leaf) -and (Test-PonDockerBind -HostPath $candidate)) {
        $verifiedMovesHost = $candidate
        break
    }
}
if ($verifiedMovesHost) {
    Set-PonEnvValue -EnvPath $activeEnv -Key 'PON_PRODUCT_MOVES_DIRECT_ENABLED' -Value '1'
    Set-PonEnvValue -EnvPath $activeEnv -Key 'PON_PRODUCT_MOVES_DIRECT_HOST_DIR' -Value $verifiedMovesHost
    $translogicPreflight.product_moves_docker_direct = $true
    $translogicPreflight.product_moves_docker_host_dir = $verifiedMovesHost
    Write-Host "Docker direct PRODUCT_MOVES source: VERIFIED ($verifiedMovesHost)" -ForegroundColor Green
} else {
    $safeMovesFallback = (Join-Path $TargetDir 'sample_translogic_moves_direct').Replace('\','/')
    Set-PonEnvValue -EnvPath $activeEnv -Key 'PON_PRODUCT_MOVES_DIRECT_ENABLED' -Value '0'
    Set-PonEnvValue -EnvPath $activeEnv -Key 'PON_PRODUCT_MOVES_DIRECT_HOST_DIR' -Value $safeMovesFallback
    Write-PonWarn 'Docker direct PRODUCT_MOVES source: NOT VERIFIED. Existing local working-copy/manual-upload flow remains active.'
}

$stateDir = Join-Path $TargetDir '.update_state'
New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
$state = [ordered]@{
    release_version = $release
    prepared_at = (Get-Date).ToString('o')
    target_dir = $TargetDir
    previous_install_dir = $previous
    backup_dir = $backupDir
    database_backup = $dbBackup
    first_stable_install = $firstInstall
    git_existed_before = $gitExisted
    pre_update_commit = $preCommit
    status = 'prepared'
}
$state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $stateDir 'last_update.json') -Encoding UTF8
$translogicPreflight | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $stateDir 'translogic_preflight.json') -Encoding UTF8
Set-Content -LiteralPath (Join-Path $backupRoot 'LAST_BACKUP.txt') -Value $backupDir -Encoding UTF8

$maintenance = Join-Path $TargetDir 'maintenance\latest_update'
New-Item -ItemType Directory -Path $maintenance -Force | Out-Null
@('00_OPEN_POWERSHELL_HERE.bat','01_PREPARE_INSTALL.ps1','02_APPLY_UPDATE.ps1','03_ROLLBACK.ps1','04_VALIDATE.ps1','05_CREATE_CONTINUITY_SNAPSHOT.ps1','05_CREATE_CONTINUITY_SNAPSHOT.bat','README_INSTALL.md','RELEASE_VERSION.txt') | ForEach-Object {
    $source = Join-Path $PSScriptRoot $_
    if (Test-Path -LiteralPath $source) { Copy-Item -LiteralPath $source -Destination $maintenance -Force }
}
Copy-PonTree -Source (Join-Path $PSScriptRoot '_support') -Destination (Join-Path $maintenance '_support')

Write-Host ''
Write-PonPass '01 completed successfully.'
Write-PonPass "Active folder prepared: $TargetDir"
Write-Host "Rollback snapshot:      $backupDir" -ForegroundColor Green
Write-Host ''
Write-Host 'NEXT: run 02_APPLY_UPDATE.ps1 from this Downloads/extracted folder.' -ForegroundColor Cyan
