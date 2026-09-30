param(
    [string]$TargetDir = 'C:\Docker-Projects\PON_Bikes_Automation'
)

$ErrorActionPreference = 'Stop'

function Write-Info([string]$Message) { Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Pass([string]$Message) { Write-Host "[PASS] $Message" -ForegroundColor Green }
function Write-Warn([string]$Message) { Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Fail([string]$Message) { Write-Host "[FAIL] $Message" -ForegroundColor Red }

Write-Host ''
Write-Info 'PON Bikes Automation - 05 CREATE CONTINUITY SNAPSHOT'
Write-Info "Installed project: $TargetDir"
Write-Host ''

$snapshotScript = Join-Path $TargetDir 'tools\Create_Continuity_Snapshot.ps1'
if (-not (Test-Path -LiteralPath $snapshotScript -PathType Leaf)) {
    Write-Fail "Continuity Snapshot tool is missing: $snapshotScript"
    exit 1
}

$validationLog = Get-ChildItem -LiteralPath (Join-Path $TargetDir 'logs') -Filter 'Validation_*.txt' -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $validationLog) {
    Write-Fail 'No validation log was found. Run .\04_VALIDATE.ps1 successfully before creating a Continuity Snapshot.'
    exit 1
}
$validationText = Get-Content -LiteralPath $validationLog.FullName -Raw -ErrorAction SilentlyContinue
if ($null -eq $validationText) { $validationText = '' }
if ($validationText -match '(?m)^\[FAIL\]') {
    Write-Fail "The latest validation log contains failures: $($validationLog.FullName)"
    Write-Fail 'Run 04_VALIDATE.ps1 again and resolve its failures before creating a new authoritative snapshot.'
    exit 1
}

$updateStatePath = Join-Path $TargetDir '.update_state\last_update.json'
if (Test-Path -LiteralPath $updateStatePath) {
    try {
        $updateState = Get-Content -LiteralPath $updateStatePath -Raw | ConvertFrom-Json
        if ($updateState.applied_at) {
            $appliedAt = [datetimeoffset]::Parse([string]$updateState.applied_at).LocalDateTime
            if ($validationLog.LastWriteTime -lt $appliedAt) {
                Write-Fail "Latest validation predates the currently applied release $($updateState.release_version)."
                Write-Fail 'Run .\04_VALIDATE.ps1 for the current installation before creating the snapshot.'
                exit 1
            }
        }
    } catch {
        Write-Warn "Could not verify validation freshness from last_update.json: $($_.Exception.Message)"
    }
}

Write-Pass "Latest validation has no FAIL entries and is current: $($validationLog.Name)"
Write-Info 'Reading installed code, database state, workflow state and configured external-source references...'

try {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $snapshotScript -ProjectDir $TargetDir
    $snapshotCode = $LASTEXITCODE
    if ($snapshotCode -ne 0) {
        Write-Fail 'Continuity Snapshot creation failed. No incomplete snapshot was accepted as valid.'
        exit $snapshotCode
    }

    $continuityDir = Join-Path $TargetDir 'continuity'
    $latestZip = Join-Path $continuityDir 'PON_Bikes_Automation_Continuity_LATEST.zip'
    if (-not (Test-Path -LiteralPath $latestZip -PathType Leaf)) {
        Write-Fail 'Snapshot tool returned success but LATEST was not found.'
        exit 1
    }
    $latestItem = Get-Item -LiteralPath $latestZip
    Write-Pass '05 completed successfully.'
    Write-Pass "LATEST: $latestZip"
    Write-Pass ("Size: {0:N0} bytes" -f $latestItem.Length)
    exit 0
}
catch {
    Write-Fail $_.Exception.Message
    Write-Fail '05 failed. Any previous valid LATEST snapshot remains the authoritative snapshot.'
    exit 1
}
