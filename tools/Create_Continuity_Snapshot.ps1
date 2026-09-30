param(
    [string]$ProjectDir = 'C:\Docker-Projects\PON_Bikes_Automation'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

function Write-Info([string]$Message) { Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Pass([string]$Message) { Write-Host "[PASS] $Message" -ForegroundColor Green }
function Write-Warn([string]$Message) { Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Fail([string]$Message) { Write-Host "[FAIL] $Message" -ForegroundColor Red }

function Get-EnvValue {
    param([string]$EnvPath, [string]$Key, [string]$Default = '')
    if (-not (Test-Path -LiteralPath $EnvPath)) { return $Default }
    $line = Get-Content -LiteralPath $EnvPath | Where-Object { $_ -match ('^\s*' + [regex]::Escape($Key) + '\s*=') } | Select-Object -Last 1
    if (-not $line) { return $Default }
    return (($line -split '=', 2)[1]).Trim()
}

function Resolve-MappedDrivePath {
    param([string]$Path)
    if (-not $Path -or $Path -notmatch '^([A-Za-z]):[\\/](.*)$') { return '' }
    $drive = $matches[1] + ':'
    $rest = $matches[2]
    try {
        $mapping = Get-SmbMapping -LocalPath $drive -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($mapping -and $mapping.RemotePath) {
            if ($rest) { return (Join-Path $mapping.RemotePath $rest) }
            return $mapping.RemotePath
        }
    } catch { }
    try {
        $logical = Get-CimInstance Win32_LogicalDisk -Filter ("DeviceID='{0}'" -f $drive) -ErrorAction SilentlyContinue
        if ($logical -and $logical.ProviderName) {
            if ($rest) { return (Join-Path $logical.ProviderName $rest) }
            return $logical.ProviderName
        }
    } catch { }
    return ''
}

function Add-SourceMetadata {
    param(
        [System.Collections.Generic.List[object]]$List,
        [string]$Label,
        [string]$Path,
        [string]$LastKnown = ''
    )
    if (-not $Path) { return }
    $resolved = $Path
    $exists = Test-Path -LiteralPath $resolved
    $unc = ''
    if (-not $exists) {
        $unc = Resolve-MappedDrivePath -Path $Path
        if ($unc -and (Test-Path -LiteralPath $unc)) {
            $resolved = $unc
            $exists = $true
        }
    }
    $row = [ordered]@{
        Label = $Label
        Path = $Path
        ResolvedPath = if ($resolved -ne $Path) { $resolved } else { '' }
        Exists = $exists
        Type = 'Unavailable'
        SizeBytes = ''
        LastModified = ''
        SHA256 = ''
        Format = ''
        LastKnownApplicationRead = $LastKnown
    }
    if ($exists) {
        $item = Get-Item -LiteralPath $resolved -Force
        if ($item.PSIsContainer) {
            $row.Type = 'Directory'
            $row.Format = 'directory'
            $row.LastModified = $item.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')
        } else {
            $row.Type = 'File'
            $row.SizeBytes = $item.Length
            $row.LastModified = $item.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')
            $row.Format = [IO.Path]::GetExtension($item.Name).TrimStart('.').ToLowerInvariant()
            try { $row.SHA256 = (Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant() } catch { $row.SHA256 = 'HASH_ERROR: ' + $_.Exception.Message }
        }
    }
    $List.Add([pscustomobject]$row)
}

function Get-CodeFiles {
    param([string]$Root)
    $excludedDirs = @('.git','__pycache__','.pytest_cache','.mypy_cache','.venv','venv','node_modules','logs','continuity','maintenance','.update_state','media','staticfiles','backups')
    $excludedFileNames = @('.env','db.sqlite3')
    Get-ChildItem -LiteralPath $Root -Recurse -File -Force | Where-Object {
        $relative = $_.FullName.Substring($Root.Length) -replace '^[\\/]+',''
        $segments = @($relative -split '[\\/]')
        $parentSegments = if ($segments.Count -gt 1) { $segments[0..($segments.Count - 2)] } else { @() }
        $dirBlocked = $false
        foreach ($segment in $parentSegments) {
            if ($excludedDirs -contains $segment) { $dirBlocked = $true; break }
        }
        $nameBlocked = $excludedFileNames -contains $_.Name
        $extBlocked = $_.Extension -in @('.pyc','.pyo','.log','.tmp','.bak','.sql')
        $sensitiveName = $_.Name -match '(?i)(credentials?|oauth|access[_-]?token|refresh[_-]?token|private[_-]?key)'
        -not ($dirBlocked -or $nameBlocked -or $extBlocked -or $sensitiveName)
    }
}

function Copy-BaselineCode {
    param([string]$Root, [string]$Destination)
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    $rows = New-Object 'System.Collections.Generic.List[object]'
    foreach ($file in Get-CodeFiles -Root $Root) {
        $relative = $file.FullName.Substring($Root.Length) -replace '^[\\/]+',''
        $target = Join-Path $Destination $relative
        $targetParent = Split-Path -Parent $target
        if (-not (Test-Path -LiteralPath $targetParent)) { New-Item -ItemType Directory -Path $targetParent -Force | Out-Null }
        $sanitised = $false
        if ($file.Name -eq '.env.example') {
            $lines = Get-Content -LiteralPath $file.FullName
            $safeLines = foreach ($line in $lines) {
                if ($line -match '^\s*([^#][A-Za-z0-9_]*(PASSWORD|SECRET|TOKEN|PRIVATE_KEY)[A-Za-z0-9_]*)\s*=') {
                    "$($matches[1])=<REDACTED>"
                } else { $line }
            }
            Set-Content -LiteralPath $target -Value $safeLines -Encoding UTF8
            $sanitised = $true
        } else {
            Copy-Item -LiteralPath $file.FullName -Destination $target -Force
        }
        $copied = Get-Item -LiteralPath $target
        $rows.Add([pscustomobject]@{
            path = $relative.Replace('\','/')
            size_bytes = $copied.Length
            sha256 = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
            last_write_time = $file.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')
            sanitised = $sanitised
        })
    }
    return $rows
}

Add-Type -AssemblyName System.IO.Compression.FileSystem

Write-Host ''
Write-Info 'PON Bikes Automation - Continuity Snapshot'
Write-Info "Project: $ProjectDir"

if (-not (Test-Path -LiteralPath (Join-Path $ProjectDir 'compose.yaml'))) { Write-Fail 'compose.yaml not found.'; exit 1 }
if (-not (Test-Path -LiteralPath (Join-Path $ProjectDir '.env'))) { Write-Fail '.env not found.'; exit 1 }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Write-Fail 'Docker CLI not found.'; exit 1 }

$continuityDir = Join-Path $ProjectDir 'continuity'
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$stageDir = Join-Path $continuityDir ('.building_' + $timestamp)
$stageContent = Join-Path $stageDir 'snapshot'
$baselineRoot = Join-Path $stageDir 'baseline_code'
$candidateZip = Join-Path $continuityDir ("PON_Bikes_Automation_Continuity_{0}.zip" -f $timestamp)
$latestZip = Join-Path $continuityDir 'PON_Bikes_Automation_Continuity_LATEST.zip'

try {
    New-Item -ItemType Directory -Path $stageContent -Force | Out-Null
    Write-Info 'Reading authoritative state from the running Django/PostgreSQL installation...'
    $stateErrPath = Join-Path $stageDir 'state_export_stderr.txt'
    Push-Location $ProjectDir
    try {
        $stateJsonRaw = (& docker compose exec -T web python manage.py export_continuity_state 2> $stateErrPath | Out-String)
        $stateJson = if ($null -eq $stateJsonRaw) { '' } else { ([string]$stateJsonRaw).Trim() }
        $stateCode = $LASTEXITCODE
    } finally { Pop-Location }
    $stateErr = ''
    if (Test-Path -LiteralPath $stateErrPath) {
        $stateErrRaw = Get-Content -LiteralPath $stateErrPath -Raw -ErrorAction SilentlyContinue
        if ($null -ne $stateErrRaw) { $stateErr = ([string]$stateErrRaw).Trim() }
    }
    if ($stateCode -ne 0 -or -not $stateJson) { throw "Could not export application/database state. Output: $stateJson $stateErr" }
    try { $state = $stateJson | ConvertFrom-Json } catch { throw "Continuity state is not valid JSON: $($_.Exception.Message)" }
    $hostUpdateStatePath = Join-Path $ProjectDir '.update_state\last_update.json'
    if (Test-Path -LiteralPath $hostUpdateStatePath) {
        try {
            $hostUpdateState = Get-Content -LiteralPath $hostUpdateStatePath -Raw | ConvertFrom-Json
            if ($hostUpdateState.release_version) {
                $state.application.installed_release | Add-Member -NotePropertyName release_version -NotePropertyValue ([string]$hostUpdateState.release_version) -Force
                $state.application.installed_release | Add-Member -NotePropertyName status -NotePropertyValue ([string]$hostUpdateState.status) -Force
                if ($hostUpdateState.prepared_at) { $state.application.installed_release | Add-Member -NotePropertyName prepared_at -NotePropertyValue ([string]$hostUpdateState.prepared_at) -Force }
                if ($hostUpdateState.applied_at) { $state.application.installed_release | Add-Member -NotePropertyName applied_at -NotePropertyValue ([string]$hostUpdateState.applied_at) -Force }
            }
        } catch { Write-Warn "Could not read host update-state metadata: $($_.Exception.Message)" }
    }
    Write-Pass 'Application/database state captured read-only.'

    $dbState = [ordered]@{
        snapshot_at = $state.snapshot_at
        installed_release = $state.application.installed_release
        database = $state.database
        container_index = $state.workflow.all_containers
        product_state = $state.products
        dictionary_summary = [ordered]@{
            historical_name_matches = $state.dictionary.historical_name_matches
            active_abbreviation_rules = $state.dictionary.active_abbreviation_rules
            inactive_abbreviation_rules = $state.dictionary.inactive_abbreviation_rules
            group1_rule_count = @($state.dictionary.group1_rules).Count
        }
    }
    $dbState | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $stageContent 'DB_STATE.json') -Encoding UTF8

    Write-Info 'Creating sanitised baseline code archive from the physically installed project...'
    $hashRows = Copy-BaselineCode -Root $ProjectDir -Destination $baselineRoot
    $hashRows | Export-Csv -LiteralPath (Join-Path $stageContent 'FILE_HASHES.csv') -NoTypeInformation -Encoding UTF8
    $baselineZip = Join-Path $stageContent 'BASELINE_CODE.zip'
    [IO.Compression.ZipFile]::CreateFromDirectory($baselineRoot, $baselineZip, [IO.Compression.CompressionLevel]::Optimal, $false)
    if (-not (Test-Path -LiteralPath $baselineZip)) { throw 'BASELINE_CODE.zip was not created.' }
    Write-Pass ("Baseline code captured: {0} file(s)." -f $hashRows.Count)

    $envPath = Join-Path $ProjectDir '.env'
    $sources = New-Object 'System.Collections.Generic.List[object]'
    $latestCatalogAt = if ($state.source_references.latest_product_master_imported_at) { [string]$state.source_references.latest_product_master_imported_at } else { '' }
    $latestMovesAt = if ($state.source_references.latest_product_moves_import) { [string]$state.source_references.latest_product_moves_import.imported_at } else { '' }

    $productHostDir = Get-EnvValue -EnvPath $envPath -Key 'PON_PRODUCT_HOST_DIR' -Default ''
    if ($productHostDir) { Add-SourceMetadata -List $sources -Label 'PON/PBP Product Master' -Path (Join-Path $productHostDir 'products_pon_pbp_auto.xls') -LastKnown $latestCatalogAt }
    foreach ($customerPath in @($state.source_references.customer_product_master_paths)) {
        if ($customerPath.product_catalog_source_path) {
            Add-SourceMetadata -List $sources -Label ("Product Master source ({0})" -f $customerPath.customer) -Path ([string]$customerPath.product_catalog_source_path) -LastKnown $latestCatalogAt
        }
    }
    Add-SourceMetadata -List $sources -Label 'PRODUCT_MOVES Translogic source' -Path ([string]$state.source_references.product_moves_source_display) -LastKnown $latestMovesAt
    $containerHost = Get-EnvValue -EnvPath $envPath -Key 'PON_HOST_PATH' -Default ''
    if ($containerHost) { Add-SourceMetadata -List $sources -Label 'Container source folder (configured PON_HOST_PATH)' -Path $containerHost }
    $businessContainerPath = 'S:\FORMS\CUSTOMER\PON - Pon.Bike\2026 Containers'
    if (-not $containerHost -or $containerHost -ne $businessContainerPath) { Add-SourceMetadata -List $sources -Label 'Container source folder (business reference)' -Path $businessContainerPath }
    Add-SourceMetadata -List $sources -Label 'PRODUCT_MOVES local working copy' -Path ([string]$state.source_references.product_moves_working_display) -LastKnown $latestMovesAt
    Add-SourceMetadata -List $sources -Label 'UPStockSerial local working file' -Path ([string]$state.source_references.upstock_working_display)
    Add-SourceMetadata -List $sources -Label 'UPStockSerial Translogic destination' -Path ([string]$state.source_references.upstock_final_display)

    $sourceText = New-Object System.Text.StringBuilder
    [void]$sourceText.AppendLine('PON Bikes Automation - External Source Files')
    [void]$sourceText.AppendLine("Snapshot: $($state.snapshot_at)")
    [void]$sourceText.AppendLine('External sources are referenced only; they are not copied into this Continuity Snapshot.')
    [void]$sourceText.AppendLine('')
    foreach ($row in $sources) {
        [void]$sourceText.AppendLine("[$($row.Label)]")
        [void]$sourceText.AppendLine("Path: $($row.Path)")
        if ($row.ResolvedPath) { [void]$sourceText.AppendLine("Resolved path: $($row.ResolvedPath)") }
        [void]$sourceText.AppendLine("Exists: $($row.Exists)")
        [void]$sourceText.AppendLine("Type: $($row.Type)")
        [void]$sourceText.AppendLine("Size bytes: $($row.SizeBytes)")
        [void]$sourceText.AppendLine("Last modified: $($row.LastModified)")
        [void]$sourceText.AppendLine("SHA-256: $($row.SHA256)")
        [void]$sourceText.AppendLine("Format: $($row.Format)")
        [void]$sourceText.AppendLine("Last known application read/import: $($row.LastKnownApplicationRead)")
        [void]$sourceText.AppendLine('')
    }
    Set-Content -LiteralPath (Join-Path $stageContent 'SOURCE_FILES.txt') -Value $sourceText.ToString() -Encoding UTF8

    $workflowText = New-Object System.Text.StringBuilder
    [void]$workflowText.AppendLine('PON Bikes Automation - Workflow State')
    [void]$workflowText.AppendLine("Snapshot: $($state.snapshot_at)")
    [void]$workflowText.AppendLine("Containers registered: $($state.database.counts.containers)")
    [void]$workflowText.AppendLine("Status counts: $((($state.workflow.container_status_counts | ConvertTo-Json -Compress)))")
    if ($state.workflow.last_container_processed) {
        [void]$workflowText.AppendLine("Last container processed: $($state.workflow.last_container_processed.container_id) | Job Order: $($state.workflow.last_container_processed.job_order) | Activity: $($state.workflow.last_container_processed.last_activity_at) ($($state.workflow.last_container_processed.last_activity_kind))")
    }
    [void]$workflowText.AppendLine('')
    [void]$workflowText.AppendLine('RECENT CONTAINERS')
    foreach ($row in @($state.workflow.recent_containers)) {
        [void]$workflowText.AppendLine('---')
        [void]$workflowText.AppendLine("Container: $($row.container_id)")
        [void]$workflowText.AppendLine("Job Order: $($row.job_order)")
        [void]$workflowText.AppendLine("Customer: $($row.customer)")
        [void]$workflowText.AppendLine("Status: $($row.status) | Current step: $($row.current_step)")
        [void]$workflowText.AppendLine("First Scan: $($row.first_scan.status) | confirmed: $($row.first_scan.confirmed_at)")
        [void]$workflowText.AppendLine("Product Check: download_ready=$($row.product_check.download_ready), products_ready=$($row.product_check.products_ready), new=$($row.product_check.new_product_count), pending_new=$(@($row.product_check.pending_new_codes).Count)")
        [void]$workflowText.AppendLine("PRODUCT_MOVES: loaded=$($row.product_moves.loaded), rows=$($row.product_moves.rows), reconciliation_ready=$($row.product_moves.reconciliation_ready), refresh_mode=$($row.product_moves.refresh_mode)")
        [void]$workflowText.AppendLine("UPStockSerial: download_ready=$($row.upstockserial.download_ready), current=$($row.upstockserial.current), generated=$($row.upstockserial.last_generated_at)")
        [void]$workflowText.AppendLine("New Product Import: download_ready=$($row.new_product_import.download_ready), generated=$($row.new_product_import.last_generated_at)")
        [void]$workflowText.AppendLine("Customer Report: download_ready=$($row.customer_report.download_ready), current=$($row.customer_report.current), generated=$($row.customer_report.last_generated_at)")
        if (@($row.warnings).Count -gt 0) { [void]$workflowText.AppendLine("Warnings: $(@($row.warnings) -join ' | ')") }
    }
    Set-Content -LiteralPath (Join-Path $stageContent 'WORKFLOW_STATE.txt') -Value $workflowText.ToString() -Encoding UTF8

    $dictionaryText = New-Object System.Text.StringBuilder
    [void]$dictionaryText.AppendLine('PON Bikes Automation - Dictionary / Product Rule State')
    [void]$dictionaryText.AppendLine("Snapshot: $($state.snapshot_at)")
    [void]$dictionaryText.AppendLine("Historical name matches: $($state.dictionary.historical_name_matches)")
    [void]$dictionaryText.AppendLine("Active abbreviation rules: $($state.dictionary.active_abbreviation_rules)")
    [void]$dictionaryText.AppendLine("Inactive abbreviation rules: $($state.dictionary.inactive_abbreviation_rules)")
    [void]$dictionaryText.AppendLine("Group1 rules configured: $(@($state.dictionary.group1_rules).Count)")
    [void]$dictionaryText.AppendLine('')
    [void]$dictionaryText.AppendLine('ACTIVE PRODUCT CATALOGS')
    foreach ($catalog in @($state.dictionary.catalogs)) {
        [void]$dictionaryText.AppendLine("- $($catalog.customer): $($catalog.original_name) | rows=$($catalog.row_count) | exact_matches=$($catalog.historical_name_matches) | active_abbrev=$($catalog.configured_active_abbreviation_rules) | uploaded=$($catalog.uploaded_at) | sha256=$($catalog.sha256)")
    }
    [void]$dictionaryText.AppendLine('')
    [void]$dictionaryText.AppendLine('GROUP1 RULES')
    foreach ($rule in @($state.dictionary.group1_rules)) {
        [void]$dictionaryText.AppendLine("- $($rule.family_name) -> $($rule.suffix) | PON=$($rule.pon_group1) | PBP=$($rule.pbp_group1) | priority=$($rule.priority) | active=$($rule.active) | phrases=$($rule.match_phrase_count)")
    }
    [void]$dictionaryText.AppendLine('')
    [void]$dictionaryText.AppendLine("Pending new product codes: $(@($state.products.pending_new_codes) -join ', ')")
    [void]$dictionaryText.AppendLine("Definitions: $($state.products.product_definitions) | complete dimensions: $($state.products.definitions_with_complete_dimensions) | missing dimensions: $($state.products.definitions_with_missing_dimensions)")
    [void]$dictionaryText.AppendLine("Missing ShortName: $($state.products.definitions_missing_short_name) | Missing LongName: $($state.products.definitions_missing_long_name) | Missing Group1: $($state.products.definitions_missing_group1)")
    [void]$dictionaryText.AppendLine("Group2 rule: cubic > $($state.products.group2.threshold_cubic_m3) m3 => '$($state.products.group2.large_value)'; otherwise '$($state.products.group2.default_value)'.")
    [void]$dictionaryText.AppendLine("Group2 derived counts: above threshold=$($state.products.group2.definitions_above_threshold), at/below=$($state.products.group2.definitions_at_or_below_threshold)")
    Set-Content -LiteralPath (Join-Path $stageContent 'DICTIONARY_STATE.txt') -Value $dictionaryText.ToString() -Encoding UTF8

    Write-Info 'Capturing installed Python/Docker package versions...'
    Push-Location $ProjectDir
    try {
        $pythonVersionRaw = (& docker compose exec -T web python --version 2>&1 | Out-String)
        $pythonVersion = if ($null -eq $pythonVersionRaw) { '' } else { ([string]$pythonVersionRaw).Trim() }
        $pipFreezeRaw = (& docker compose exec -T web python -m pip freeze 2>&1 | Out-String)
        $pipFreeze = if ($null -eq $pipFreezeRaw) { '' } else { ([string]$pipFreezeRaw).Trim() }
        if ($LASTEXITCODE -ne 0) { throw 'pip freeze failed.' }
        $composeImagesRaw = (& docker compose images 2>&1 | Out-String)
        $composeImages = if ($null -eq $composeImagesRaw) { '' } else { ([string]$composeImagesRaw).Trim() }
    } finally { Pop-Location }
    $installedPackages = @(
        'PON Bikes Automation - Installed Packages',
        "Snapshot: $($state.snapshot_at)",
        "Installed release: $($state.application.installed_release.release_version)",
        '',
        'PYTHON',
        $pythonVersion,
        '',
        'PIP FREEZE',
        $pipFreeze,
        '',
        'DOCKER',
        ([string]((& docker --version 2>&1 | Out-String))).Trim(),
        ([string]((& docker compose version 2>&1 | Out-String))).Trim(),
        '',
        'COMPOSE IMAGES',
        $composeImages
    ) -join "`r`n"
    Set-Content -LiteralPath (Join-Path $stageContent 'INSTALLED_PACKAGES.txt') -Value $installedPackages -Encoding UTF8
    Write-Pass 'Installed package state captured.'

    # The manual 05 flow is intentionally based on the most recent completed validation.
    $validationDir = Join-Path $ProjectDir 'logs'
    $latestValidation = Get-ChildItem -LiteralPath $validationDir -Filter 'Validation_*.txt' -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latestValidation) { throw 'No Validation_*.txt log was found. Run 04_VALIDATE.ps1 successfully before creating the Continuity Snapshot.' }
    $validationRaw = Get-Content -LiteralPath $latestValidation.FullName -Raw -ErrorAction SilentlyContinue
    if ($null -eq $validationRaw) { $validationRaw = '' }
    $validationFailCount = ([regex]::Matches([string]$validationRaw, '(?m)^\[FAIL\]')).Count
    $validationWarnCount = ([regex]::Matches([string]$validationRaw, '(?m)^\[WARN\]')).Count
    if ($validationFailCount -gt 0) { throw "Latest validation contains $validationFailCount FAIL line(s): $($latestValidation.FullName)" }
    $validationUpdateStatePath = Join-Path $ProjectDir '.update_state\last_update.json'
    if (Test-Path -LiteralPath $validationUpdateStatePath) {
        try {
            $validationUpdateState = Get-Content -LiteralPath $validationUpdateStatePath -Raw | ConvertFrom-Json
            if ($validationUpdateState.applied_at) {
                $validationAppliedAt = [datetimeoffset]::Parse([string]$validationUpdateState.applied_at).LocalDateTime
                if ($latestValidation.LastWriteTime -lt $validationAppliedAt) {
                    throw "Latest validation predates applied release $($validationUpdateState.release_version). Run 04_VALIDATE.ps1 first."
                }
            }
        } catch {
            if ($_.Exception.Message -match '^Latest validation predates') { throw }
            Write-Warn "Could not verify validation freshness from last_update.json: $($_.Exception.Message)"
        }
    }
    Copy-Item -LiteralPath $latestValidation.FullName -Destination (Join-Path $stageContent 'LAST_VALIDATION.log') -Force

    $testCount = 'unknown'
    $testMatch = [regex]::Match([string]$validationRaw, 'Found\s+(\d+)\s+test\(s\)')
    if ($testMatch.Success) { $testCount = $testMatch.Groups[1].Value }
    $validationState = New-Object System.Text.StringBuilder
    [void]$validationState.AppendLine('PON Bikes Automation - Validation State')
    [void]$validationState.AppendLine("Snapshot: $($state.snapshot_at)")
    [void]$validationState.AppendLine("Installed release: $($state.application.installed_release.release_version)")
    [void]$validationState.AppendLine("Validation log: $($latestValidation.FullName)")
    [void]$validationState.AppendLine("Validation log timestamp: $($latestValidation.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'))")
    [void]$validationState.AppendLine("Django check: $(if ($validationRaw -match '\[PASS\] Django system check passed\.') {'PASS'} else {'NOT CONFIRMED'})")
    [void]$validationState.AppendLine("Migrations: $(if ($validationRaw -match '\[PASS\] All receiving migrations are applied\.') {'PASS'} else {'NOT CONFIRMED'})")
    [void]$validationState.AppendLine("Models/migration state: $(if ($validationRaw -match '\[PASS\] Receiving models match migration state\.') {'PASS'} else {'NOT CONFIRMED'})")
    [void]$validationState.AppendLine("Database: $(if ($validationRaw -match '\[PASS\] Django can read the PostgreSQL database\.') {'PASS'} else {'NOT CONFIRMED'})")
    [void]$validationState.AppendLine("Tests: $(if ($validationRaw -match '\[PASS\] Complete receiving test suite passed\.') {'PASS'} else {'NOT CONFIRMED'}) | Found tests: $testCount")
    [void]$validationState.AppendLine("Port $($state.application.web_port): $(if ($validationRaw -match ('\[PASS\] HTTP application responded on port ' + [regex]::Escape([string]$state.application.web_port) + '\.')) {'PASS'} else {'NOT CONFIRMED'})")
    [void]$validationState.AppendLine("FAIL lines: $validationFailCount")
    [void]$validationState.AppendLine("WARN lines: $validationWarnCount")
    [void]$validationState.AppendLine('')
    [void]$validationState.AppendLine('ACTIVE WARNINGS')
    $warningLines = @(([string]$validationRaw -split "`r?`n") | Where-Object { $_ -match '^\[WARN\]' })
    if ($warningLines.Count -eq 0) { [void]$validationState.AppendLine('- None in latest validation log.') }
    else { foreach ($line in $warningLines) { [void]$validationState.AppendLine("- $line") } }
    Set-Content -LiteralPath (Join-Path $stageContent 'VALIDATION_STATE.txt') -Value $validationState.ToString() -Encoding UTF8
    Write-Pass 'Latest validation state captured.'

    Write-Info 'Capturing non-secret environment/runtime state...'
    Push-Location $ProjectDir
    try {
        $djangoVersionRaw = (& docker compose exec -T web python -m django --version 2>&1 | Out-String)
        $djangoVersion = if ($null -eq $djangoVersionRaw) { '' } else { ([string]$djangoVersionRaw).Trim() }
        $postgresVersionRaw = (& docker compose exec -T db psql --version 2>&1 | Out-String)
        $postgresVersion = if ($null -eq $postgresVersionRaw) { '' } else { ([string]$postgresVersionRaw).Trim() }
        $webContainerId = (& docker compose ps -q web 2>$null | Select-Object -First 1)
        $dockerProject = ''
        if ($webContainerId) {
            $dockerInspectRaw = (& docker inspect $webContainerId 2>$null | Out-String)
            $dockerInspectCode = $LASTEXITCODE
            if ($dockerInspectCode -eq 0 -and $dockerInspectRaw) {
                try {
                    $dockerInspect = $dockerInspectRaw | ConvertFrom-Json
                    $dockerInspectItem = @($dockerInspect) | Select-Object -First 1
                    if ($dockerInspectItem -and $dockerInspectItem.Config -and $dockerInspectItem.Config.Labels) {
                        $projectLabel = $dockerInspectItem.Config.Labels.PSObject.Properties['com.docker.compose.project']
                        if ($projectLabel -and $projectLabel.Value) {
                            $dockerProject = ([string]$projectLabel.Value).Trim()
                        }
                    }
                } catch {
                    Write-Warn "Could not parse Docker inspect JSON while reading the Compose project label: $($_.Exception.Message)"
                }
            }
        }
    } finally { Pop-Location }
    if (-not $dockerProject) { $dockerProject = Get-EnvValue -EnvPath $envPath -Key 'COMPOSE_PROJECT_NAME' -Default 'unknown' }
    $dockerVersionRaw = (& docker --version 2>&1 | Out-String)
    $dockerVersion = if ($null -eq $dockerVersionRaw) { '' } else { ([string]$dockerVersionRaw).Trim() }
    $composeVersionRaw = (& docker compose version 2>&1 | Out-String)
    $composeVersion = if ($null -eq $composeVersionRaw) { '' } else { ([string]$composeVersionRaw).Trim() }

    $environmentText = New-Object System.Text.StringBuilder
    [void]$environmentText.AppendLine('PON Bikes Automation - Environment State (non-secret)')
    [void]$environmentText.AppendLine("Snapshot: $($state.snapshot_at)")
    [void]$environmentText.AppendLine("Installed release: $($state.application.installed_release.release_version)")
    [void]$environmentText.AppendLine("Python: $pythonVersion")
    [void]$environmentText.AppendLine("Django: $djangoVersion")
    [void]$environmentText.AppendLine("PostgreSQL: $postgresVersion")
    [void]$environmentText.AppendLine("Docker: $dockerVersion")
    [void]$environmentText.AppendLine("Docker Compose: $composeVersion")
    [void]$environmentText.AppendLine("Docker project: $dockerProject")
    [void]$environmentText.AppendLine("Web port: $($state.application.web_port)")
    [void]$environmentText.AppendLine('')
    [void]$environmentText.AppendLine('CONFIGURED PATHS / SAFE FLAGS')
    foreach ($key in @(
        'PON_CONTAINER_ROOT','PON_HOST_PATH','PON_PRODUCT_CATALOG_PATH','PON_PRODUCT_HOST_DIR',
        'PON_PRODUCT_MOVES_PATH','PON_PRODUCT_MOVES_SOURCE_DISPLAY','PON_PRODUCT_MOVES_WORKING_DISPLAY','PON_MOVES_HOST_DIR',
        'PON_UPSTOCKSERIAL_PATH','PON_UPSTOCK_WORKING_DISPLAY','PON_UPSTOCK_FINAL_DISPLAY','PON_IMPORT_HOST_DIR',
        'PON_CLIENT_REPORT_WORKING_DISPLAY','PON_CLIENT_REPORT_FINAL_DISPLAY','PON_REPORT_HOST_DIR',
        'PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED','PON_TRANSLOGIC_IMPORT_HOST_DIR',
        'PON_PRODUCT_MOVES_DIRECT_ENABLED','PON_PRODUCT_MOVES_DIRECT_HOST_DIR'
    )) {
        $value = Get-EnvValue -EnvPath $envPath -Key $key -Default ''
        [void]$environmentText.AppendLine("${key}=$value")
    }
    [void]$environmentText.AppendLine('')
    [void]$environmentText.AppendLine('Secrets/passwords/tokens are intentionally excluded.')
    Set-Content -LiteralPath (Join-Path $stageContent 'ENVIRONMENT_STATE.txt') -Value $environmentText.ToString() -Encoding UTF8
    Write-Pass 'Environment state captured without secrets.'

    $preflightPath = Join-Path $ProjectDir '.update_state\translogic_preflight.json'
    $preflight = $null
    if (Test-Path -LiteralPath $preflightPath) {
        try { $preflight = Get-Content -LiteralPath $preflightPath -Raw | ConvertFrom-Json } catch { Write-Warn "Could not parse Translogic preflight: $($_.Exception.Message)" }
    }
    $upstockDisplay = Get-EnvValue -EnvPath $envPath -Key 'PON_UPSTOCK_FINAL_DISPLAY' -Default (Get-EnvValue -EnvPath $envPath -Key 'PON_UPSTOCKSERIAL_PATH' -Default '')
    $upstockDir = ''
    if ($upstockDisplay) { try { $upstockDir = Split-Path -Parent $upstockDisplay } catch { $upstockDir = '' } }
    $upstockResolved = if ($upstockDir) { Resolve-MappedDrivePath -Path $upstockDir } else { '' }
    $movesDisplay = Get-EnvValue -EnvPath $envPath -Key 'PON_PRODUCT_MOVES_SOURCE_DISPLAY' -Default (Get-EnvValue -EnvPath $envPath -Key 'PON_PRODUCT_MOVES_PATH' -Default '')
    $movesDir = ''
    if ($movesDisplay) { try { $movesDir = Split-Path -Parent $movesDisplay } catch { $movesDir = '' } }
    $movesResolved = if ($movesDir) { Resolve-MappedDrivePath -Path $movesDir } else { '' }

    $externalText = New-Object System.Text.StringBuilder
    [void]$externalText.AppendLine('PON Bikes Automation - External Access State')
    [void]$externalText.AppendLine("Snapshot: $($state.snapshot_at)")
    [void]$externalText.AppendLine('')
    [void]$externalText.AppendLine('[Translogic import / UPStockSerial destination]')
    [void]$externalText.AppendLine("Configured file: $upstockDisplay")
    [void]$externalText.AppendLine("Configured folder: $upstockDir")
    [void]$externalText.AppendLine("Windows folder accessible now: $(if ($upstockDir -and (Test-Path -LiteralPath $upstockDir -PathType Container)) {'YES'} else {'NO'})")
    [void]$externalText.AppendLine("Resolved UNC/path: $upstockResolved")
    [void]$externalText.AppendLine("Direct Docker enabled: $(Get-EnvValue -EnvPath $envPath -Key 'PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED' -Default '0')")
    [void]$externalText.AppendLine("Direct Docker host folder: $(Get-EnvValue -EnvPath $envPath -Key 'PON_TRANSLOGIC_IMPORT_HOST_DIR' -Default '')")
    if ($preflight) {
        [void]$externalText.AppendLine("Last prepare Windows-accessible: $($preflight.import_host_accessible)")
        [void]$externalText.AppendLine("Last prepare Docker read/write verified: $($preflight.import_docker_direct)")
        [void]$externalText.AppendLine("Numbered 1-5 pattern: $($preflight.import_pattern)")
        [void]$externalText.AppendLine("Numbered extension: $($preflight.import_pattern_extension)")
        [void]$externalText.AppendLine("Oldest numbered file: $($preflight.import_oldest_file)")
        [void]$externalText.AppendLine("Oldest numbered file time: $($preflight.import_oldest_time)")
        [void]$externalText.AppendLine("Pattern reason: $($preflight.import_pattern_reason)")
    }
    [void]$externalText.AppendLine("Current fallback: Download/manual transfer when direct Docker access is disabled or unverified.")
    [void]$externalText.AppendLine('')
    [void]$externalText.AppendLine('[PRODUCT_MOVES source]')
    [void]$externalText.AppendLine("Configured file: $movesDisplay")
    [void]$externalText.AppendLine("Configured folder: $movesDir")
    [void]$externalText.AppendLine("Windows file accessible now: $(if ($movesDisplay -and (Test-Path -LiteralPath $movesDisplay -PathType Leaf)) {'YES'} else {'NO'})")
    [void]$externalText.AppendLine("Resolved UNC/path: $movesResolved")
    [void]$externalText.AppendLine("Direct Docker enabled: $(Get-EnvValue -EnvPath $envPath -Key 'PON_PRODUCT_MOVES_DIRECT_ENABLED' -Default '0')")
    [void]$externalText.AppendLine("Direct Docker host folder: $(Get-EnvValue -EnvPath $envPath -Key 'PON_PRODUCT_MOVES_DIRECT_HOST_DIR' -Default '')")
    if ($preflight) {
        [void]$externalText.AppendLine("Last prepare Windows-accessible: $($preflight.product_moves_host_accessible)")
        [void]$externalText.AppendLine("Last prepare Docker verified: $($preflight.product_moves_docker_direct)")
        [void]$externalText.AppendLine("Last prepare Docker host: $($preflight.product_moves_docker_host_dir)")
    }
    [void]$externalText.AppendLine("Current configured runtime source: $($state.source_references.product_moves_working_display)")
    [void]$externalText.AppendLine("Current fallback: existing local working-copy/manual-upload flow when direct source is disabled or unavailable.")
    Set-Content -LiteralPath (Join-Path $stageContent 'EXTERNAL_ACCESS_STATE.txt') -Value $externalText.ToString() -Encoding UTF8
    Write-Pass 'External access state captured.'

    $backupRoot = 'C:\Docker-Projects\PON_Bikes_Automation_Backups'
    $updateStatePath = Join-Path $ProjectDir '.update_state\last_update.json'
    $updateState = $null
    if (Test-Path -LiteralPath $updateStatePath) {
        try { $updateState = Get-Content -LiteralPath $updateStatePath -Raw | ConvertFrom-Json } catch { Write-Warn "Could not parse last_update.json: $($_.Exception.Message)" }
    }
    $lastBackupPointer = Join-Path $backupRoot 'LAST_BACKUP.txt'
    $backupDir = if ($updateState -and $updateState.backup_dir) { [string]$updateState.backup_dir } elseif (Test-Path -LiteralPath $lastBackupPointer) { ([string](Get-Content -LiteralPath $lastBackupPointer -Raw)).Trim() } else { '' }
    $databaseBackup = if ($updateState -and $updateState.database_backup) { [string]$updateState.database_backup } elseif ($backupDir) { Join-Path $backupDir 'database_before_update.sql' } else { '' }
    $backupText = New-Object System.Text.StringBuilder
    [void]$backupText.AppendLine('PON Bikes Automation - Database Backup Reference')
    [void]$backupText.AppendLine("Snapshot: $($state.snapshot_at)")
    [void]$backupText.AppendLine("Backup root: $backupRoot")
    [void]$backupText.AppendLine("Latest rollback backup folder: $backupDir")
    [void]$backupText.AppendLine("Backup folder exists: $(if ($backupDir -and (Test-Path -LiteralPath $backupDir -PathType Container)) {'YES'} else {'NO'})")
    [void]$backupText.AppendLine("Database backup file: $databaseBackup")
    if ($databaseBackup -and (Test-Path -LiteralPath $databaseBackup -PathType Leaf)) {
        $dbBackupItem = Get-Item -LiteralPath $databaseBackup
        [void]$backupText.AppendLine('Database backup exists: YES')
        [void]$backupText.AppendLine("Database backup size bytes: $($dbBackupItem.Length)")
        [void]$backupText.AppendLine("Database backup modified: $($dbBackupItem.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'))")
    } else {
        [void]$backupText.AppendLine('Database backup exists: NO')
    }
    [void]$backupText.AppendLine('The database dump is intentionally NOT embedded in the Continuity Snapshot.')
    Set-Content -LiteralPath (Join-Path $stageContent 'DATABASE_BACKUP_REFERENCE.txt') -Value $backupText.ToString() -Encoding UTF8
    Write-Pass 'Database rollback-backup reference captured.'

    $currentState = New-Object System.Text.StringBuilder
    [void]$currentState.AppendLine('# PON Bikes Automation - Current State')
    [void]$currentState.AppendLine('')
    [void]$currentState.AppendLine("Snapshot generated: $($state.snapshot_at)")
    [void]$currentState.AppendLine("Installed release: **$($state.application.installed_release.release_version)**")
    [void]$currentState.AppendLine("Installed folder: **$ProjectDir**")
    [void]$currentState.AppendLine("Database engine: **$($state.database.engine)** ($($state.database.vendor))")
    [void]$currentState.AppendLine("Receiving migrations applied: **$(@($state.database.migrations).Count)**")
    [void]$currentState.AppendLine("Containers: **$($state.database.counts.containers)**")
    [void]$currentState.AppendLine("Active Product Master rows: **$($state.products.known_active_catalog_entries)**")
    [void]$currentState.AppendLine("Product definitions: **$($state.products.product_definitions)**")
    [void]$currentState.AppendLine("Pending NEW product codes: **$(@($state.products.pending_new_codes).Count)**")
    [void]$currentState.AppendLine('')
    [void]$currentState.AppendLine('## Technical state generated from installed code / database')
    [void]$currentState.AppendLine('')
    [void]$currentState.AppendLine("- Web port: $($state.application.web_port)")
    [void]$currentState.AppendLine("- Direct Translogic import enabled: $($state.application.direct_integration.translogic_import_enabled)")
    [void]$currentState.AppendLine("- Direct PRODUCT_MOVES enabled: $($state.application.direct_integration.product_moves_direct_enabled)")
    [void]$currentState.AppendLine("- Duplicate non-blank Job Orders: $(@($state.database.integrity.duplicate_nonblank_job_orders).Count)")
    [void]$currentState.AppendLine("- Multiple active PRODUCT_MOVES imports: $(@($state.database.integrity.multiple_active_product_moves_imports).Count)")
    if ($state.workflow.last_container_processed) { [void]$currentState.AppendLine("- Last safely determinable container activity: $($state.workflow.last_container_processed.container_id) at $($state.workflow.last_container_processed.last_activity_at)") }
    [void]$currentState.AppendLine('')
    [void]$currentState.AppendLine('## Known pending / warnings')
    if (@($state.known_warnings).Count -eq 0) { [void]$currentState.AppendLine('- None reported by the read-only state exporter.') }
    else { foreach ($warning in @($state.known_warnings)) { [void]$currentState.AppendLine("- $warning") } }
    [void]$currentState.AppendLine('')
    [void]$currentState.AppendLine('## Snapshot security / scope')
    [void]$currentState.AppendLine('- `.env` is excluded.')
    [void]$currentState.AppendLine('- Credential/token/private-key files are excluded by filename.')
    [void]$currentState.AppendLine('- Secret/password/token values in `.env.example` are redacted in BASELINE_CODE.zip.')
    [void]$currentState.AppendLine('- Full database dumps are NOT included. DB_STATE.json contains read-only schema/migration/count/integrity summaries.')
    [void]$currentState.AppendLine('- External source files are referenced and hashed when accessible; large external files are not copied.')
    [void]$currentState.AppendLine('')
    [void]$currentState.AppendLine('## Authoritative functional documentation captured from the installed project')
    [void]$currentState.AppendLine('The sections below are copied from the Markdown documentation physically installed with this release. They are not reconstructed from chat history.')
    $docNames = @('01_OVERVIEW.md','02_OPERATIONAL_WORKFLOW.md','03_CONTAINER_LIFECYCLE.md','04_CLIENT_MANIFEST_IMPORT.md','05_RECEIVE_AND_SCAN.md','06_PRODUCT_CHECK.md','07_NEW_PRODUCT_PROCESS.md','08_PRODUCT_MOVES_AND_TRANSLOGIC.md','09_UPSTOCKSERIAL.md','10_CUSTOMER_REPORT.md','11_PRODUCT_MASTER.md','12_AUTO_MAPPING.md','13_BUSINESS_RULES.md','14_DATABASE_AND_DATA_FLOW.md','15_CONFIGURATION_AND_PATHS.md','16_INSTALL_UPDATE_ROLLBACK.md','17_TESTING_AND_VALIDATION.md','18_CONTINUITY_SNAPSHOT.md','RELEASE_HISTORY.md')
    foreach ($docName in $docNames) {
        $docPath = Join-Path (Join-Path $ProjectDir 'docs') $docName
        if (Test-Path -LiteralPath $docPath) {
            [void]$currentState.AppendLine('')
            [void]$currentState.AppendLine("---`n### Installed doc: $docName`n")
            [void]$currentState.AppendLine((Get-Content -LiteralPath $docPath -Raw))
        }
    }
    Set-Content -LiteralPath (Join-Path $stageContent 'CURRENT_STATE.md') -Value $currentState.ToString() -Encoding UTF8

    $readme = @"
# Continue PON Bikes Automation Development

This ZIP is a **Continuity Snapshot** generated from the physically installed PON Bikes Automation code, the running Django/PostgreSQL database state, and the external source references available at snapshot time.

To continue in a new ChatGPT chat or Work session, attach:

`PON_Bikes_Automation_Continuity_LATEST.zip`

and say:

> Continue PON Bikes Automation development using this Continuity Snapshot as the authoritative current state.

**The installed physical code, database state and external source references contained in this snapshot take precedence over historical chat descriptions.**

Recommended reading order:

1. `CURRENT_STATE.md`
2. `WORKFLOW_STATE.txt`
3. `SOURCE_FILES.txt`
4. `DICTIONARY_STATE.txt`
5. `DB_STATE.json`
6. `FILE_HASHES.csv`
7. `BASELINE_CODE.zip`
8. `INSTALLED_PACKAGES.txt`
9. `VALIDATION_STATE.txt`
10. `ENVIRONMENT_STATE.txt`
11. `EXTERNAL_ACCESS_STATE.txt`
12. `LAST_VALIDATION.log`
13. `DATABASE_BACKUP_REFERENCE.txt`

`BASELINE_CODE.zip` intentionally excludes `.env`, credentials, tokens, private keys, logs, historical backups, generated media, previous continuity snapshots and full database dumps. Secret-like values in `.env.example` are redacted.

Snapshot generated: $($state.snapshot_at)
Installed release: $($state.application.installed_release.release_version)
"@
    Set-Content -LiteralPath (Join-Path $stageContent 'README_CONTINUE.md') -Value $readme -Encoding UTF8

    Write-Info 'Building final Continuity Snapshot ZIP...'
    if (Test-Path -LiteralPath $candidateZip) { Remove-Item -LiteralPath $candidateZip -Force }
    [IO.Compression.ZipFile]::CreateFromDirectory($stageContent, $candidateZip, [IO.Compression.CompressionLevel]::Optimal, $false)
    $verify = [IO.Compression.ZipFile]::OpenRead($candidateZip)
    try {
        $required = @('CURRENT_STATE.md','BASELINE_CODE.zip','FILE_HASHES.csv','DB_STATE.json','WORKFLOW_STATE.txt','SOURCE_FILES.txt','DICTIONARY_STATE.txt','INSTALLED_PACKAGES.txt','VALIDATION_STATE.txt','ENVIRONMENT_STATE.txt','EXTERNAL_ACCESS_STATE.txt','LAST_VALIDATION.log','DATABASE_BACKUP_REFERENCE.txt','README_CONTINUE.md')
        $names = @($verify.Entries | ForEach-Object { $_.FullName })
        foreach ($requiredName in $required) {
            if ($names -notcontains $requiredName) { throw "Snapshot ZIP is incomplete: missing $requiredName" }
        }
    } finally { $verify.Dispose() }
    Copy-Item -LiteralPath $candidateZip -Destination $latestZip -Force
    $zipHash = (Get-FileHash -LiteralPath $candidateZip -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Pass "Continuity Snapshot created: $candidateZip"
    Write-Pass "LATEST updated: $latestZip"
    Write-Pass "SHA-256: $zipHash"
    Remove-Item -LiteralPath $stageDir -Recurse -Force -ErrorAction SilentlyContinue
    exit 0
}
catch {
    Write-Fail $_.Exception.Message
    if (Test-Path -LiteralPath $candidateZip) { Remove-Item -LiteralPath $candidateZip -Force -ErrorAction SilentlyContinue }
    if (Test-Path -LiteralPath $stageDir) { Remove-Item -LiteralPath $stageDir -Recurse -Force -ErrorAction SilentlyContinue }
    Write-Fail 'No incomplete snapshot was published. Any previous PON_Bikes_Automation_Continuity_LATEST.zip was left untouched.'
    exit 1
}
