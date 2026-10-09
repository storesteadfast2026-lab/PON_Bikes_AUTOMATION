param([Parameter(Mandatory=$true)][string]$PackageDir,
      [string]$TargetDir='C:\Docker-Projects\PON_Bikes_Automation')
$ErrorActionPreference='Stop'
$source=Join-Path $TargetDir 'maintenance/release_source/PON.Update.Common.ps1'
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw 'Canonical PON updater source is missing.' }
$destination=Join-Path $PackageDir '_support/PON.Update.Common.ps1'
if (-not (Test-Path -LiteralPath (Split-Path $destination -Parent))) { New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force | Out-Null }
Copy-Item -LiteralPath $source -Destination $destination -Force
$manifest=Join-Path $PackageDir 'PACKAGE_MANIFEST_SHA256.txt'
$rows=@(Get-ChildItem -LiteralPath $PackageDir -File -Recurse | Where-Object {
 $_.FullName -ne $manifest -and $_.FullName -notlike (Join-Path $PackageDir 'OUTPUT\*')
} | Sort-Object FullName | ForEach-Object {
 $relative=$_.FullName.Substring(([IO.Path]::GetFullPath($PackageDir)).TrimEnd('\').Length).TrimStart('\','/')
 ((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()+"`t"+$relative)
})
[IO.File]::WriteAllLines($manifest,$rows,(New-Object System.Text.UTF8Encoding($false)))
foreach($row in $rows){
 $parts=$row -split "`t",2
 $path=Join-Path $PackageDir $parts[1]
 if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $parts[0]) { throw "Manifest verification failed: $($parts[1])" }
}
Write-Host "[PASS] Canonical updater helper copied; $($rows.Count) manifest hashes verified."
