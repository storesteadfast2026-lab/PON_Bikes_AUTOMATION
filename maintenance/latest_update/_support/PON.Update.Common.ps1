Set-StrictMode -Version 2.0

function Write-PonInfo { param([string]$Message) Write-Host ("[INFO] {0}" -f $Message) -ForegroundColor Cyan }
function Write-PonPass { param([string]$Message) Write-Host ("[PASS] {0}" -f $Message) -ForegroundColor Green }
function Write-PonWarn { param([string]$Message) Write-Host ("[WARN] {0}" -f $Message) -ForegroundColor Yellow }
function Write-PonFail { param([string]$Message) Write-Host ("[FAIL] {0}" -f $Message) -ForegroundColor Red }


function Get-PonEnvValue {
    param(
        [Parameter(Mandatory=$true)][string]$EnvPath,
        [Parameter(Mandatory=$true)][string]$Key,
        [string]$Default = ""
    )
    if (-not (Test-Path -LiteralPath $EnvPath)) { return $Default }
    $line = Get-Content -LiteralPath $EnvPath | Where-Object {
        $_ -match ('^\s*' + [regex]::Escape($Key) + '\s*=')
    } | Select-Object -Last 1
    if (-not $line) { return $Default }
    return (($line -split '=', 2)[1]).Trim()
}

function Copy-PonTree {
    param(
        [Parameter(Mandatory=$true)][string]$Source,
        [Parameter(Mandatory=$true)][string]$Destination
    )
    if (-not (Test-Path -LiteralPath $Destination)) {
        New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    }
    Get-ChildItem -LiteralPath $Source -Force | Where-Object { $_.Name -ne ".git" } | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
    }
}

function Clear-PonDirectory {
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return }
    Get-ChildItem -LiteralPath $Path -Force | Where-Object { $_.Name -ne ".git" } | ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
    }
}

function Invoke-PonCompose {
    param(
        [Parameter(Mandatory=$true)][string]$WorkingDirectory,
        [Parameter(Mandatory=$true)][string[]]$Arguments,
        [switch]$AllowFailure
    )
    Push-Location $WorkingDirectory
    try {
        & docker compose @Arguments
        $code = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
    if (-not $AllowFailure -and $code -ne 0) {
        throw "docker compose $($Arguments -join ' ') failed with exit code $code"
    }
    return $code
}

function Get-PonDbContainer {
    param([Parameter(Mandatory=$true)][string]$WorkingDirectory)
    Push-Location $WorkingDirectory
    try {
        $id = (& docker compose ps -q db 2>$null | Select-Object -First 1)
    }
    finally {
        Pop-Location
    }
    if ($id) { return $id.Trim() }
    return ""
}

function Wait-PonDbHealthy {
    param(
        [Parameter(Mandatory=$true)][string]$WorkingDirectory,
        [int]$TimeoutSeconds = 60
    )
    Invoke-PonCompose -WorkingDirectory $WorkingDirectory -Arguments @('up','-d','db') | Out-Null
    $stopwatch = [Diagnostics.Stopwatch]::StartNew()
    do {
        $container = Get-PonDbContainer -WorkingDirectory $WorkingDirectory
        if ($container) {
            $status = (& docker inspect -f '{{.State.Health.Status}}' $container 2>$null)
            if ($status -and $status.Trim() -eq 'healthy') { return $container }
        }
        Start-Sleep -Seconds 2
    } while ($stopwatch.Elapsed.TotalSeconds -lt $TimeoutSeconds)
    throw "PostgreSQL did not become healthy within $TimeoutSeconds seconds."
}

function Backup-PonDatabase {
    param(
        [Parameter(Mandatory=$true)][string]$InstallDir,
        [Parameter(Mandatory=$true)][string]$OutputFile
    )
    $envPath = Join-Path $InstallDir '.env'
    $dbUser = Get-PonEnvValue -EnvPath $envPath -Key 'POSTGRES_USER' -Default 'pon_bikes'
    $dbName = Get-PonEnvValue -EnvPath $envPath -Key 'POSTGRES_DB' -Default 'pon_bikes'
    $dbContainer = Wait-PonDbHealthy -WorkingDirectory $InstallDir
    $cmd = "pg_dump -U '$dbUser' -d '$dbName' --clean --if-exists --no-owner --no-privileges > /tmp/pon_pre_update.sql"
    & docker exec $dbContainer sh -c $cmd
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL backup failed.' }
    & docker cp ("{0}:/tmp/pon_pre_update.sql" -f $dbContainer) $OutputFile
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy PostgreSQL backup to the host.' }
    & docker exec $dbContainer rm -f /tmp/pon_pre_update.sql | Out-Null
}

function Restore-PonDatabase {
    param(
        [Parameter(Mandatory=$true)][string]$InstallDir,
        [Parameter(Mandatory=$true)][string]$InputFile
    )
    if (-not (Test-Path -LiteralPath $InputFile)) {
        throw "Database backup not found: $InputFile"
    }
    $envPath = Join-Path $InstallDir '.env'
    $dbUser = Get-PonEnvValue -EnvPath $envPath -Key 'POSTGRES_USER' -Default 'pon_bikes'
    $dbName = Get-PonEnvValue -EnvPath $envPath -Key 'POSTGRES_DB' -Default 'pon_bikes'
    $dbContainer = Wait-PonDbHealthy -WorkingDirectory $InstallDir
    & docker cp $InputFile ("{0}:/tmp/pon_rollback.sql" -f $dbContainer)
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy PostgreSQL rollback file into the database container.' }
    $terminate = "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$dbName' AND pid <> pg_backend_pid();"
    & docker exec $dbContainer psql -U $dbUser -d postgres -c $terminate | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not terminate active PostgreSQL connections.' }
    & docker exec $dbContainer psql -U $dbUser -d $dbName -v ON_ERROR_STOP=1 -f /tmp/pon_rollback.sql
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL rollback restore failed.' }
    & docker exec $dbContainer rm -f /tmp/pon_rollback.sql | Out-Null
}

function Find-PonPreviousInstall {
    param(
        [Parameter(Mandatory=$true)][string]$TargetDir,
        [string]$ExplicitDir = ''
    )
    if ($ExplicitDir) {
        if (-not (Test-Path -LiteralPath (Join-Path $ExplicitDir 'compose.yaml'))) {
            throw "CurrentInstallDir does not contain compose.yaml: $ExplicitDir"
        }
        return (Resolve-Path -LiteralPath $ExplicitDir).Path
    }
    if (Test-Path -LiteralPath (Join-Path $TargetDir 'compose.yaml')) {
        return (Resolve-Path -LiteralPath $TargetDir).Path
    }

    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $runningWeb = (& docker ps --filter 'label=com.docker.compose.project=pon_bike_automation_09161055' --filter 'label=com.docker.compose.service=web' --format '{{.ID}}' 2>$null | Select-Object -First 1)
        if ($runningWeb) {
            $workingDir = (& docker inspect -f '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}' $runningWeb 2>$null)
            if ($workingDir) {
                $workingDir = $workingDir.Trim()
                if (Test-Path -LiteralPath (Join-Path $workingDir 'compose.yaml')) {
                    return (Resolve-Path -LiteralPath $workingDir).Path
                }
            }
        }
    }

    $root = Split-Path -Parent $TargetDir
    if (-not (Test-Path -LiteralPath $root)) { return '' }
    $candidates = Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue | Where-Object {
        $_.FullName -ne $TargetDir -and
        ($_.Name -like 'PON_Bike_Automation_*' -or $_.Name -like 'PON_Bikes_Automation_*') -and
        (Test-Path -LiteralPath (Join-Path $_.FullName 'compose.yaml'))
    } | Sort-Object LastWriteTime -Descending
    if ($candidates) { return $candidates[0].FullName }
    return ''
}

function Set-PonEnvValue {
    param(
        [Parameter(Mandatory=$true)][string]$EnvPath,
        [Parameter(Mandatory=$true)][string]$Key,
        [Parameter(Mandatory=$true)][string]$Value
    )
    $lines = @()
    if (Test-Path -LiteralPath $EnvPath) { $lines = @(Get-Content -LiteralPath $EnvPath) }
    $pattern = '^\s*' + [regex]::Escape($Key) + '\s*='
    $updated = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) {
            $lines[$i] = "$Key=$Value"
            $updated = $true
        }
    }
    if (-not $updated) { $lines += "$Key=$Value" }
    Set-Content -LiteralPath $EnvPath -Value $lines -Encoding UTF8
}

function Resolve-PonMappedDrivePath {
    param([Parameter(Mandatory=$true)][string]$Path)
    if ($Path -notmatch '^([A-Za-z]):[\\/](.*)$') { return '' }
    $drive = ($matches[1] + ':')
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

function Test-PonDockerBind {
    param(
        [Parameter(Mandatory=$true)][string]$HostPath,
        [switch]$RequireWrite
    )
    if (-not (Test-Path -LiteralPath $HostPath -PathType Container)) { return $false }
    try {
        if ($RequireWrite) {
            # The copy-to-Translogic action is enabled only when Docker can actually
            # create and remove a temporary file in the real destination folder.
            $probeName = '.pon_write_probe_' + [guid]::NewGuid().ToString('N')
            $mountArg = "type=bind,source=$HostPath,target=/probe"
            $python = "from pathlib import Path; import sys; p=Path('/probe')/'$probeName'; p.write_bytes(b'pon'); ok=p.is_file() and p.read_bytes()==b'pon'; p.unlink(); sys.exit(0 if ok and not p.exists() else 1)"
            & docker run --rm --mount $mountArg python:3.12-slim python -c $python *> $null
            return ($LASTEXITCODE -eq 0)
        }
        $mountArg = "type=bind,source=$HostPath,target=/probe,readonly"
        & docker run --rm --mount $mountArg python:3.12-slim python -c "import os,sys; sys.exit(0 if os.path.isdir('/probe') and os.access('/probe', os.R_OK) else 1)" *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Get-PonNumberedImportPattern {
    param([Parameter(Mandatory=$true)][string]$Directory)
    $result = [ordered]@{
        available = $false
        pattern = ''
        extension = ''
        oldest_name = ''
        oldest_time = ''
        files = @()
        reason = ''
    }
    if (-not (Test-Path -LiteralPath $Directory -PathType Container)) {
        $result.reason = 'Directory is not accessible from Windows.'
        return [pscustomobject]$result
    }
    $groups = @{}
    Get-ChildItem -LiteralPath $Directory -File -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.Name -match '^(.*?)([1-5])(\.[^.]+)$') {
            $prefix = $matches[1]
            $number = [int]$matches[2]
            $extension = $matches[3]
            $key = ($prefix.ToLowerInvariant() + '|' + $extension.ToLowerInvariant())
            if (-not $groups.ContainsKey($key)) {
                $groups[$key] = [ordered]@{ Prefix=$prefix; Extension=$extension; Files=@{} }
            }
            $groups[$key].Files[$number] = $_
        }
    }
    $complete = @()
    foreach ($group in $groups.Values) {
        $all = $true
        foreach ($n in 1..5) { if (-not $group.Files.ContainsKey($n)) { $all = $false } }
        if ($all) { $complete += ,$group }
    }
    if ($complete.Count -eq 0) {
        $result.reason = 'No complete numbered file set 1-5 was found.'
        return [pscustomobject]$result
    }
    if ($complete.Count -gt 1) {
        $patterns = @($complete | ForEach-Object { "$($_.Prefix){1-5}$($_.Extension)" })
        $result.reason = 'Multiple complete numbered sets were found: ' + ($patterns -join ', ')
        return [pscustomobject]$result
    }
    $selected = $complete[0]
    $rows = @()
    foreach ($n in 1..5) {
        $file = $selected.Files[$n]
        $rows += [pscustomobject]@{
            number = $n
            name = $file.Name
            full_name = $file.FullName
            last_write_time = $file.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')
        }
    }
    $oldest = $rows | Sort-Object @{Expression={ [datetime]$_.last_write_time }}, name | Select-Object -First 1
    $result.available = $true
    $result.pattern = "$($selected.Prefix){1-5}$($selected.Extension)"
    $result.extension = $selected.Extension.ToLowerInvariant()
    $result.oldest_name = $oldest.name
    $result.oldest_time = $oldest.last_write_time
    $result.files = $rows
    return [pscustomobject]$result
}
