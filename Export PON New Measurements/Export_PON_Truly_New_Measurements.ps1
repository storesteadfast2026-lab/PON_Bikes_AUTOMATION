# PON Truly New Measurements - original Excel layout, one-step auto-open.
# Lookup by Container ID or Translogic Job Order; database READ-ONLY.
param(
    [string]$SearchValue = '',
    [switch]$NoOpen
)

$ErrorActionPreference = 'Stop'
$AppDir = 'C:\Docker-Projects\PON_Bikes_Automation'
$ComposeFile = Join-Path $AppDir 'compose.yaml'
$PythonFile = Join-Path $PSScriptRoot 'PON_Truly_New_Measurements.py'
$LogDir = Join-Path $PSScriptRoot 'OUTPUT'
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$RemotePython = "/tmp/pon_new_measure_${Stamp}.py"
$RemoteExcel = "/tmp/pon_new_measure_${Stamp}.xlsx"
$TranscriptStarted = $false

function Assert-DockerExit([string]$Label) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed (docker exit code $LASTEXITCODE)."
    }
}

try {
    New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
    $LogFile = Join-Path $LogDir "00_Export_Truly_New_${Stamp}.txt"
    Start-Transcript -Path $LogFile -ErrorAction Stop | Out-Null
    $TranscriptStarted = $true

    if ([string]::IsNullOrWhiteSpace($SearchValue)) {
        $SearchValue = Read-Host 'Enter Container ID or Job Order (e.g. ONEU6047465 or 1773600)'
    }
    $SearchValue = $SearchValue.Trim().ToUpperInvariant()
    if ($SearchValue -cnotmatch '^[A-Z0-9_-]{1,40}$') {
        throw "Invalid Container ID / Job Order: $SearchValue. Use letters, digits, '-' or '_'."
    }
    if (-not (Test-Path -LiteralPath $ComposeFile -PathType Leaf)) {
        throw "PON Docker Compose file was not found: $ComposeFile"
    }
    if (-not (Test-Path -LiteralPath $PythonFile -PathType Leaf)) {
        throw "Missing Python companion script: $PythonFile. Extract all ZIP files together."
    }
    if (-not (Get-Command docker.exe -ErrorAction SilentlyContinue)) {
        throw 'Docker CLI is not available.'
    }

    $PythonBytes = [System.IO.File]::ReadAllBytes($PythonFile)
    if ($PythonBytes.Length -lt 100) {
        throw "Python companion file is empty or incomplete: $PythonFile"
    }
    if ($PythonBytes[0] -eq 239 -and $PythonBytes[1] -eq 187 -and $PythonBytes[2] -eq 191) {
        throw 'The Python source has an unexpected BOM. Re-extract the original ZIP.'
    }

    Write-Host '============================================================'
    Write-Host 'PON - EXPORT TRULY NEW PRODUCT MEASUREMENTS'
    Write-Host "Search          : $SearchValue"
    Write-Host 'Classification  : Historical NEW only (PBP_TO_PON excluded)'
    Write-Host 'Excel layout    : Original 14-column New Products, one sheet'
    Write-Host 'Execution       : One step, open in Excel automatically'
    Write-Host 'Production data : READ ONLY'
    Write-Host '============================================================'

    # Transfer Python source as raw bytes. Never pipe a PowerShell string to Python stdin;
    # Windows PowerShell 5.1 can add a BOM (U+FEFF) on redirected stdin.
    & docker.exe compose --project-directory $AppDir -f $ComposeFile cp $PythonFile "web:$RemotePython"
    Assert-DockerExit 'Copy of export source to Docker'

    $Runner = "exec(compile(__import__('pathlib').Path('$RemotePython').read_text(encoding='utf-8-sig'), '$RemotePython', 'exec'))"
    $Command = "SEARCH_VALUE='$SearchValue'; OUTPUT='$RemoteExcel'; $Runner"
    Write-Host '[INFO] Resolving Container / Job Order and generating the original Excel layout...'
    $Lines = @(& docker.exe compose --project-directory $AppDir -f $ComposeFile exec -T web python manage.py shell -c $Command)
    $ExportExitCode = $LASTEXITCODE
    foreach ($Line in $Lines) { Write-Host $Line }
    if ($ExportExitCode -ne 0) {
        throw "Django export failed (exit code $ExportExitCode). No Excel was copied to Windows."
    }

    $Markers = @($Lines | Where-Object { [string]$_ -cmatch '^PON_EXPORT_CONTAINER_ID=[A-Z0-9_-]{1,30}$' })
    if ($Markers.Count -ne 1) {
        throw 'Export succeeded but returned no unique container ID. Local Excel copy blocked.'
    }
    $ResolvedContainer = ([string]$Markers[0]).Substring('PON_EXPORT_CONTAINER_ID='.Length)

    # Original exporter name and location: next to the script, not a second worksheet.
    $Filename = "${ResolvedContainer}_New_Products_Measurements.xlsx"
    $OutputFile = Join-Path $PSScriptRoot $Filename
    if (Test-Path -LiteralPath $OutputFile) {
        # Protect any previous Excel, including edits manually made after export.
        $OutputFile = Join-Path $PSScriptRoot "${ResolvedContainer}_New_Products_Measurements_${Stamp}.xlsx"
    }

    & docker.exe compose --project-directory $AppDir -f $ComposeFile cp "web:$RemoteExcel" $OutputFile
    Assert-DockerExit 'Copy of Excel workbook to Windows'
    if (-not (Test-Path -LiteralPath $OutputFile -PathType Leaf)) {
        throw "Generated Excel is missing: $OutputFile"
    }
    $SavedFile = Get-Item -LiteralPath $OutputFile
    if ($SavedFile.Length -lt 1000) {
        throw "Generated Excel is unexpectedly small: $($SavedFile.Length) bytes"
    }
    $Hash = (Get-FileHash -LiteralPath $OutputFile -Algorithm SHA256).Hash
    Write-Host "[PASS] Container: $ResolvedContainer" -ForegroundColor Green
    Write-Host "[PASS] Excel saved: $OutputFile" -ForegroundColor Green
    Write-Host "[PASS] SHA256: $Hash" -ForegroundColor Green

    if (-not $NoOpen) {
        # Same behaviour as the user's original TGBU exporter: open with associated Excel.
        Start-Process -FilePath $OutputFile -ErrorAction Stop
        Write-Host '[PASS] Excel opened using the default spreadsheet application.' -ForegroundColor Green
    }
}
catch {
    Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red
    throw
}
finally {
    # Only temporary /tmp files; never delete app files or database records.
    if (Get-Command docker.exe -ErrorAction SilentlyContinue) {
        try {
            & docker.exe compose --project-directory $AppDir -f $ComposeFile exec -T web rm -f $RemotePython $RemoteExcel 1>$null 2>$null
        } catch { }
    }
    if ($TranscriptStarted) { Stop-Transcript | Out-Null }
}
