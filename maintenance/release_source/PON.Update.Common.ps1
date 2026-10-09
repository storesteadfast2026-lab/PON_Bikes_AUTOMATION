Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
function Pass([string]$Text) { Write-Host "[PASS] $Text" -ForegroundColor Green }
function Fail([string]$Text) { throw "[FAIL] $Text" }
function Warn([string]$Text) { Write-Host "[WARN] $Text" -ForegroundColor Yellow }
function Hash([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Require([bool]$Condition,[string]$Message) { if (-not $Condition) { Fail $Message } }
function Native([string]$Executable,[string[]]$Arguments,[switch]$Quiet) {
 $old=$ErrorActionPreference; $ErrorActionPreference='Continue'
 try { $result=@(& $Executable @Arguments 2>&1 | ForEach-Object { $line=$_.ToString(); if(-not $Quiet){Write-Host $line}; $line }); $code=$LASTEXITCODE }
 catch { $result=@($_.Exception.Message);$code=-1 }
 finally { $ErrorActionPreference=$old }
 if ($code -ne 0) {
  $printable=(($Arguments -join ' ') -replace '(?i)POSTGRES_PASSWORD=[^ ]+','POSTGRES_PASSWORD=[REDACTED]')
  Fail ("$Executable $printable failed ($code): $($result -join '; ')")
 }
 return [string]($result -join "`n")
}
function Compose([string[]]$Arguments) { return Native 'docker' (@('compose')+$Arguments) }
function In-App([string]$Target,[scriptblock]$Action) {
 Push-Location $Target
 try { return (& $Action) } finally { Pop-Location }
}
function Preflight([string]$Target) {
 $required='C:\Docker-Projects\PON_Bikes_Automation'
 Require ([IO.Path]::GetFullPath($Target).TrimEnd('\') -ieq $required) 'Unexpected application directory.'
 foreach($path in @('compose.yaml','.env','.git','docker-entrypoint.sh')) { Require (Test-Path -LiteralPath (Join-Path $Target $path)) "$path is missing." }
 Require ((Get-Command docker -ErrorAction SilentlyContinue) -ne $null) 'Docker CLI unavailable.'
 Require ((Get-Command git -ErrorAction SilentlyContinue) -ne $null) 'Git CLI unavailable.'
 $commit=(Native 'git' @('--no-optional-locks','-C',$Target,'rev-parse','HEAD')).Trim()
 $branch=(Native 'git' @('--no-optional-locks','-C',$Target,'branch','--show-current')).Trim()
 Require ($commit -eq '11d0ad84e4944e3b5397e482a0e27b38fe1599e2' -and $branch -eq 'test1') 'Unexpected commit/branch. No changes made.'
 $dirty=(Native 'git' @('--no-optional-locks','-C',$Target,'status','--porcelain=v1','--untracked-files=all')).Trim()
 if ($dirty) { Warn 'Git is dirty; the update preserves unrelated changes.' }
 $services=In-App $Target { Compose @('config','--services') }
 Require (($services -split "`n") -contains 'db' -and ($services -split "`n") -contains 'web') 'Compose services db/web not found in the installed configuration.'
 $null=In-App $Target { Compose @('ps','--all') }
 return [pscustomobject]@{ commit=$commit;branch=$branch;dirty=$dirty }
}
function Check-Manifest([string]$Package) {
 $Package=[IO.Path]::GetFullPath($Package).TrimEnd('\','/')
 $path=Join-Path $Package 'PACKAGE_MANIFEST_SHA256.txt'
 Require (Test-Path -LiteralPath $path -PathType Leaf) 'Package manifest is missing.'
 $seen=@{}
 foreach($line in Get-Content -LiteralPath $path) {
  if (-not $line.Trim()) { continue }
  $fields=$line -split "`t",2
  Require ($fields.Count -eq 2 -and $fields[0] -match '^[0-9a-f]{64}$' -and $fields[1] -notmatch '(\.\.|^[\\/])') 'Malformed manifest entry.'
  Require (-not $seen.ContainsKey($fields[1])) "Duplicate manifest entry: $($fields[1])"
  $seen[$fields[1]]=$true
  $file=Join-Path $Package $fields[1]
  Require ((Test-Path -LiteralPath $file -PathType Leaf) -and (Hash $file) -eq $fields[0]) "Package hash mismatch: $($fields[1])"
 }
 foreach($file in Get-ChildItem -LiteralPath $Package -Recurse -File) {
 if($file.FullName -eq $path){continue}
 $relative=$file.FullName.Substring($Package.TrimEnd('\','/').Length).TrimStart('\','/').Replace('\','/')
  if($relative -like 'OUTPUT/*'){continue}
  Require ($seen.ContainsKey($relative)) "Unlisted package file: $relative"
 }
 Pass 'Package integrity verified.'
}
function Source-Hash([string]$Target,[string]$Relative) { $file=Join-Path $Target $Relative; if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { return '' }; return Hash $file }
function Schema([string]$Target) {
 $code=@'
import json
from django.db import connection, transaction
if connection.vendor != 'postgresql': raise RuntimeError('Expected PostgreSQL')
with transaction.atomic():
    with connection.cursor() as c:
        c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        tables = sorted(t for t in connection.introspection.table_names(c) if t.startswith('receiving_'))
        counts = {}
        digests = {}
        columns = {}
        for table in tables:
            c.execute('SELECT COUNT(*) FROM ' + connection.ops.quote_name(table))
            counts[table] = c.fetchone()[0]
            c.execute('SELECT md5(coalesce(string_agg(md5(row_to_json(t)::text), %s ORDER BY md5(row_to_json(t)::text)), %s)) FROM ' + connection.ops.quote_name(table) + ' t', ['', ''])
            digests[table] = c.fetchone()[0]
            if table.startswith('receiving_secondscan') or table == 'receiving_container':
                columns[table] = sorted(x.name for x in connection.introspection.get_table_description(c, table))
        container_code_modes = []
        if 'receiving_container' in tables and 'first_scan_code_mode' in columns.get('receiving_container', []):
            c.execute('SELECT first_scan_code_mode, COUNT(*) FROM receiving_container GROUP BY first_scan_code_mode ORDER BY first_scan_code_mode')
            container_code_modes = [
                {'mode': str(mode or ''), 'count': int(count)}
                for mode, count in c.fetchall()
            ]
        c.execute('SELECT name FROM django_migrations WHERE app = %s ORDER BY name', ['receiving'])
        migrations = [r[0] for r in c.fetchall()]
print('PON_SCHEMA_BEGIN')
print(json.dumps({'counts': counts, 'digests': digests, 'columns': columns, 'migrations': migrations, 'container_code_modes': container_code_modes}, sort_keys=True))
print('PON_SCHEMA_END')
'@
 $out=In-App $Target { Compose @('exec','-T','web','python','manage.py','shell','-c',$code) }
 $match=[regex]::Match($out,'(?s)PON_SCHEMA_BEGIN\s*(\{.*?\})\s*PON_SCHEMA_END')
 Require $match.Success 'Schema response missing.'
 $parsed=($match.Groups[1].Value | ConvertFrom-Json)
 foreach($entry in @($parsed.container_code_modes)) {
  Require ($null -ne $entry.PSObject.Properties['mode'] -and $null -ne $entry.PSObject.Properties['count']) 'Schema container_code_modes entry is malformed.'
  $null=[string]$entry.mode
  $null=[int64]$entry.count
 }
 return $parsed
}
function Compare-Counts($Before,$After,[switch]$LegacyBaseline) {
 $problems=New-Object System.Collections.Generic.List[string]
 foreach($p in $Before.PSObject.Properties) {
  $name=[string]$p.Name
  $current=$After.PSObject.Properties[$name]
  if ($null -eq $current) { $problems.Add("${name}: missing (was $($p.Value))"); continue }
  if ([int64]$current.Value -ne [int64]$p.Value) { $problems.Add("${name}: $($p.Value) -> $($current.Value)") }
 }
 foreach($p in $After.PSObject.Properties) {
  if ($null -eq $Before.PSObject.Properties[$p.Name]) {
   if ($LegacyBaseline -and $p.Name -like 'receiving_firstscan*') { Warn "Legacy 1006.0752 counts omitted $($p.Name); current rows will be preserved and compared from the new safety backup.";continue }
   if ([int64]$p.Value -ne 0) { $problems.Add("$($p.Name): new -> $($p.Value), expected 0") }
   else { Pass "$($p.Name): new -> 0" }
  }
 }
 if ($problems.Count) { Fail ('Operational count violation: '+($problems -join '; ')) }
 Pass 'All existing table counts match; new tables are empty.'
}
function Compare-Operational-State($Before,$After) {
 Compare-Counts $Before.counts $After.counts
 foreach($p in $Before.digests.PSObject.Properties) {
  $current=$After.digests.PSObject.Properties[$p.Name]
  Require ($null -ne $current -and [string]$current.Value -eq [string]$p.Value) "Operational data changed in $($p.Name)."
 }
 Require ((@($Before.migrations | Sort-Object) -join ',') -eq (@($After.migrations | Sort-Object) -join ',')) 'Migration state changed during this no-migration update.'
 Pass 'Operational receiving rows and migration state are unchanged.'
}
function Compare-FirstScanMigrationState($Before,$After) {
 Compare-Counts $Before.counts $After.counts
 $beforeHas0018=@($Before.migrations | Where-Object {$_ -eq '0018_container_first_scan_code_mode'}).Count -eq 1
 $afterHas0018=@($After.migrations | Where-Object {$_ -eq '0018_container_first_scan_code_mode'}).Count -eq 1
 Require $afterHas0018 'Migration 0018_container_first_scan_code_mode is not applied.'
 foreach($p in $Before.digests.PSObject.Properties) {
  if (-not $beforeHas0018 -and $p.Name -eq 'receiving_container') { continue }
  $current=$After.digests.PSObject.Properties[$p.Name]
  Require ($null -ne $current -and [string]$current.Value -eq [string]$p.Value) "Operational data changed in $($p.Name)."
 }
 if ($beforeHas0018) {
  Require ((@($Before.migrations | Sort-Object) -join ',') -eq (@($After.migrations | Sort-Object) -join ',')) 'Migration state changed unexpectedly during idempotent Apply.'
 } else {
  $expected=@($Before.migrations)+@('0018_container_first_scan_code_mode')
  Require ((@($expected | Sort-Object) -join ',') -eq (@($After.migrations | Sort-Object) -join ',')) 'Only migration 0018 may be added by this update.'
  $nonBlank=0
  foreach($entry in @($After.container_code_modes)) {
   if ([string]$entry.mode) { $nonBlank += [int64]$entry.count }
  }
  Require ($nonBlank -eq 0) 'Migration 0018 changed an existing container scan mode; expected blank values only.'
 }
 Pass 'Operational rows are preserved; only the intended 0018 container mode schema change is present.'
}
function Run-Read([string]$Target,[string[]]$Arguments) { return In-App $Target { Compose (@('exec','-T','web','python','manage.py')+$Arguments) } }
function Check-App([string]$Target,[switch]$Tests) {
 $check=Run-Read $Target @('check');Require ($check -match 'System check identified no issues') 'Django check output unexpected.'
 $m=Run-Read $Target @('showmigrations','receiving');Require ($m -match '\[X\]\s+0016_first_scan_scanner' -and $m -match '\[X\]\s+0017_second_scan_operational' -and $m -match '\[X\]\s+0018_container_first_scan_code_mode') '0016, 0017 or 0018 is not applied.'
 $mm=Run-Read $Target @('makemigrations','--check','--dry-run');Require ($mm -match 'No changes detected') 'Django model state differs from migrations.'
 if ($Tests) {
  $result=Run-Read $Target @('test','receiving','--verbosity','1')
  Require ($result -match 'Found 121 test\(s\)' -and $result -match 'Ran 121 tests' -and $result -match '(?m)^OK\s*$') 'Expected exactly 121 passing receiving tests.'
  Pass 'Django receiving tests: 121/121 PASS.'
 }
 Pass 'Django and migration state verified.'
}
function Check-JS([string]$Target) {
 Require ((Get-Command node -ErrorAction SilentlyContinue) -ne $null) 'Node.js is required to verify the six bundled Second Scan scanner tests.'
 $testFile=Join-Path $Target 'receiving/tests_js/second_scan.test.cjs'
 Require (Test-Path -LiteralPath $testFile -PathType Leaf) 'Second Scan JavaScript test file is missing.'
 $source=Get-Content -LiteralPath $testFile -Raw
 $declared=[regex]::Matches($source,'(?m)^\s*test\s*\(').Count
 Require ($declared -eq 6) "Expected exactly six declared Second Scan JavaScript tests; found $declared."
 Require (-not [regex]::IsMatch($source,'(?m)^\s*test\s*\.\s*(?:skip|todo)\s*\(')) 'Second Scan JavaScript tests must not be skipped or marked todo.'
 $null=In-App $Target { Native 'node' @('receiving/tests_js/second_scan.test.cjs') }
 Pass 'Second Scan JavaScript tests: 6/6 PASS.'
}
function Check-PreviewJS([string]$Target) {
 Require ((Get-Command node -ErrorAction SilentlyContinue) -ne $null) 'Node.js is required to verify the source-preview JavaScript tests.'
 $testFile=Join-Path $Target 'receiving/tests_js/source_preview.test.cjs'
 Require (Test-Path -LiteralPath $testFile -PathType Leaf) 'Source-preview JavaScript test file is missing.'
 $source=Get-Content -LiteralPath $testFile -Raw
 $declared=[regex]::Matches($source,'(?m)^\s*test\s*\(').Count
 Require ($declared -eq 3) "Expected exactly three declared source-preview JavaScript tests; found $declared."
 Require (-not [regex]::IsMatch($source,'(?m)^\s*test\s*\.\s*(?:skip|todo)\s*\(')) 'Source-preview JavaScript tests must not be skipped or marked todo.'
 $null=In-App $Target { Native 'node' @('receiving/tests_js/source_preview.test.cjs') }
 Pass 'Source-preview JavaScript tests: 3/3 PASS.'
}
function Check-TIIUReference([string]$Target) {
 $manifest=Join-Path $Target 'sample_data/TIIU4062052.xlsx'
 $scanned=Join-Path $Target 'sample_data/TIIU4062052 PON CON20 07-07-26.xlsx'
 $advised=Join-Path $Target 'sample_data/TIIU4062052 Advised.xlsx'
 foreach($path in @($manifest,$scanned,$advised)) { Require (Test-Path -LiteralPath $path -PathType Leaf) "TIIU4062052 reference missing: $path" }
 $code=@'
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from openpyxl import load_workbook
from receiving.services import build_client_report_rows, compare_lines, first_scan_expected_units, parse_workbook
root=Path('/app/sample_data')
rows, errors=parse_workbook(root/'TIIU4062052.xlsx', {'sheet_name':'Packing List','start_row':20,'row_step':1,'code_column':'B','long_code_column':'B','description_column':'C','quantity_column':'D'})
assert not errors and len(rows)==69 and sum(r['quantity'] for r in rows)==136
client=[SimpleNamespace(**r) for r in rows]
assert first_scan_expected_units(client, True)==134
assert Counter(r['raw_data'].get('_manifest_section') for r in rows)==Counter({'PEDAL 58':40,'FRAMES':17,'E-BIKES':11,'SMALL PARTS':1})
ws=load_workbook(root/'TIIU4062052 PON CON20 07-07-26.xlsx', data_only=True)['Sheet1']
pallet=''; received=[]
for number in range(1, ws.max_row+1):
    main=ws.cell(number,1).value; long_code=ws.cell(number,2).value
    if main and not long_code and str(main).startswith('T'): pallet=str(main)
    elif main and long_code: received.append(SimpleNamespace(code=str(main),long_code=str(long_code),quantity=1,location=pallet,source_row=number,raw_data={'scanner_code_mode':'TWO_CODES'}))
comparison=compare_lines(client, received, two_codes=True)
assert len(received)==135 and sum(r['expected'] for r in comparison)==134 and sum(r['received'] for r in comparison)==135
exceptions=[r for r in comparison if r['status']!='MATCH']
assert [(r['code'],r['expected'],r['received'],r['status']) for r in exceptions]==[('68-25281-5-849-9999-WT',0,1,'UNADVISED')]
repeated=next(r for r in comparison if r['code']=='68-25281-4-849-9999')
assert repeated['source_rows']==[76,77] and repeated['expected']==2 and repeated['received']==2
assert not any(r['code']=='04-27492' for r in comparison)
report=build_client_report_rows(client, received, two_codes=True)
unadvised=next(r for r in report if r['code']=='68-25281-5-849-9999-WT')
assert (unadvised['advised'],unadvised['received'],unadvised['variance'],unadvised['comment'])==(0,1,-1,'Unadvised / Not Advised')
advised=load_workbook(root/'TIIU4062052 Advised.xlsx', data_only=False)['Sheet1']
assert advised['B64'].value=='68-25281-5-849-9999-WT' and advised['D64'].value==0 and advised['E64'].value==1
print('TIIU4062052_REFERENCE_PASS')
'@
 $out=In-App $Target { Compose @('exec','-T','web','python','manage.py','shell','-c',$code) }
 Require ($out -match 'TIIU4062052_REFERENCE_PASS') 'TIIU4062052 reference reconciliation failed.'
 Pass 'TIIU4062052 real Manifest/Scanned/Advised reference: PASS.'
}
function Backup-DB([string]$Target,[string]$File) {
 $id=(In-App $Target { Compose @('ps','-q','db') }).Trim()
 Require ($id -match '^[a-zA-Z0-9]+$') 'Running database container missing.'
 $tmp='/tmp/pon_repair_'+[guid]::NewGuid().ToString('N')+'.sql'
 try {
  $null=Native 'docker' @('exec',$id,'sh','-c',('pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges > '+$tmp))
  $null=Native 'docker' @('cp',("${id}:$tmp"),$File)
  Require ((Test-Path -LiteralPath $File -PathType Leaf) -and (Get-Item -LiteralPath $File).Length -gt 1000) 'PostgreSQL dump is empty or missing.'
 } finally { try { $null=Native 'docker' @('exec',$id,'rm','-f',$tmp) } catch { Warn 'Temporary SQL dump cleanup failed.' } }
 return $id
}
function Db-Env([string]$Id) {
 $vars=@{}
 $raw=Native 'docker' @('inspect','--format','{{range .Config.Env}}{{println .}}{{end}}',$Id) -Quiet
 foreach($line in $raw -split "`n") { if ($line -match '^([^=]+)=(.*)$') { $vars[$matches[1]]=$matches[2] } }
 foreach($key in @('POSTGRES_USER','POSTGRES_DB','POSTGRES_PASSWORD')) { Require ($vars.ContainsKey($key) -and $vars[$key]) "Database container lacks $key" }
 return $vars
}
function Safety-Backup([string]$Target,[string]$Root,$State) {
 $dir=Join-Path $Root ((Get-Date -Format 'yyyyMMdd_HHmmss')+'_before_repair_'+[guid]::NewGuid().ToString('N').Substring(0,8))
 New-Item -ItemType Directory -Path $dir -Force | Out-Null
 $statePath=Join-Path $dir 'STATE.json'
 $State | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $statePath -Encoding UTF8
 $tracked=Native 'git' @('--no-optional-locks','-C',$Target,'ls-files')
 $paths=New-Object System.Collections.Generic.List[string]
 foreach($p in ($tracked -split "`n")) { if ($p.Trim()) { $paths.Add($p.Trim()) } }
 foreach($p in (@((Expected-Hashes).Keys)+@('receiving/migrations/0017_second_scan_operational.py','receiving/second_scan.py','receiving/templates/receiving/second_scan_scanner.html','receiving/test_second_scan.py','receiving/tests_js/second_scan.test.cjs','maintenance/release_source/PON.Update.Common.ps1','maintenance/release_source/Build_PON_Update_Manifest.ps1','.env'))) { if ($paths -notcontains $p -and (Test-Path -LiteralPath (Join-Path $Target $p))) { $paths.Add($p) } }
 $stage=Join-Path $dir 'code_stage';New-Item -ItemType Directory -Path $stage | Out-Null
 foreach($p in $paths) {
  Require ($p -notmatch '(^[\\/]|\.\.)') 'Invalid Git file path.'
  $source=Join-Path $Target $p; if (!(Test-Path -LiteralPath $source -PathType Leaf)) { continue }
  $destination=Join-Path $stage $p;New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force | Out-Null
  Copy-Item -LiteralPath $source -Destination $destination -Force
 }
 $archive=Join-Path $dir 'current_application_files.zip'
 Add-Type -AssemblyName System.IO.Compression.FileSystem
 [IO.Compression.ZipFile]::CreateFromDirectory($stage,$archive)
 $zip=[IO.Compression.ZipFile]::OpenRead($archive);try {
  Require ($zip.Entries.Count -gt 20) 'Application archive is incomplete.'
  Require (@($zip.Entries | Where-Object {$_.FullName -eq '.env'}).Count -eq 1) 'Restored app archive lacks .env.'
 } finally { $zip.Dispose() }
 $null=Native 'git' @('--no-optional-locks','-C',$Target,'bundle','create',(Join-Path $dir 'git_history.bundle'),'--all')
 $dump=Join-Path $dir 'database_before_repair.sql';$id=Backup-DB $Target $dump
 $hashes=[ordered]@{application_zip=(Hash $archive);database_dump=(Hash $dump);git_bundle=(Hash (Join-Path $dir 'git_history.bundle'))}
 $hashes | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dir 'SHA256.json') -Encoding UTF8
 Pass "Current state backup created: $dir"
 return [pscustomobject]@{Directory=$dir;Archive=$archive;Dump=$dump;DbId=$id;DbEnv=(Db-Env $id);Hashes=$hashes}
}
function Verify-Backup([object]$Backup,[object]$Schema) {
 foreach($entry in $Backup.Hashes.GetEnumerator()) {
  $path=switch($entry.Key) { 'application_zip' {$Backup.Archive};'database_dump' {$Backup.Dump};'git_bundle' {(Join-Path $Backup.Directory 'git_history.bundle')} }
  Require ((Hash $path) -eq $entry.Value) "Backup hash mismatch: $($entry.Key)"
 }
 $name='pon_repair_verify_'+[guid]::NewGuid().ToString('N').Substring(0,12)
 $image=(Native 'docker' @('inspect','--format','{{.Config.Image}}',$Backup.DbId)).Trim()
 $args=@('run','-d','--name',$name,'-e',('POSTGRES_USER='+$Backup.DbEnv['POSTGRES_USER']),'-e',('POSTGRES_DB='+$Backup.DbEnv['POSTGRES_DB']),'-e',('POSTGRES_PASSWORD='+$Backup.DbEnv['POSTGRES_PASSWORD']),$image)
 $null=Native 'docker' $args
 try {
  $ready=$false
  for($n=0;$n -lt 45;$n++) {
   $out=& docker exec $name pg_isready -U $Backup.DbEnv['POSTGRES_USER'] -d $Backup.DbEnv['POSTGRES_DB'] 2>$null
   if ($LASTEXITCODE -eq 0) { $ready=$true;break }
   Start-Sleep -Seconds 2
  }
  Require $ready 'Isolated restore database did not start.'
  $null=Native 'docker' @('cp',$Backup.Dump,("${name}:/tmp/backup.sql"))
  $null=Native 'docker' @('exec',$name,'psql','-v','ON_ERROR_STOP=1','-U',$Backup.DbEnv['POSTGRES_USER'],'-d',$Backup.DbEnv['POSTGRES_DB'],'-f','/tmp/backup.sql')
  foreach($table in $Schema.counts.PSObject.Properties) {
   Require ($table.Name -match '^receiving_[a-z0-9_]+$') 'Unexpected database table name.'
   $value=(Native 'docker' @('exec',$name,'psql','-At','-U',$Backup.DbEnv['POSTGRES_USER'],'-d',$Backup.DbEnv['POSTGRES_DB'],'-c',('SELECT COUNT(*) FROM "'+$table.Name+'"'))).Trim()
   Require ($value -match '^\d+$' -and [int64]$value -eq [int64]$table.Value) "Isolated restore count mismatch: $($table.Name)"
   $query='SELECT md5(coalesce(string_agg(md5(row_to_json(t)::text), '''' ORDER BY md5(row_to_json(t)::text)), '''')) FROM "'+$table.Name+'" t'
   $digest=(Native 'docker' @('exec',$name,'psql','-At','-U',$Backup.DbEnv['POSTGRES_USER'],'-d',$Backup.DbEnv['POSTGRES_DB'],'-c',$query)).Trim()
   Require ($digest -eq [string]$Schema.digests.PSObject.Properties[$table.Name].Value) "Isolated restore content mismatch: $($table.Name)"
  }
  Pass 'Backup restored into an independent PostgreSQL container; all receiving counts match.'
 } finally { $null=Native 'docker' @('rm','-f',$name) }
}
function Expected-Hashes { return [ordered]@{
 'receiving/forms.py'='038061e49e20467f8b241cb6da3a5a8873c9c3978cb724d8dd3f475bd355cb17'
 'receiving/management/commands/export_continuity_state.py'='f37b71fddbf00b552d23ecc04b3f73d56c2e565ef0b0dbf87e058acdffbbb778'
 'receiving/migrations/0018_container_first_scan_code_mode.py'='ac8461c6443753798e7413f8befddfca817baf062e93f33a5627ba6f976da3d9'
 'receiving/models.py'='34b08e7dec9175301cea970b2978d07a150afc465ad02f4b0c9dc7bedff0dcff'
 'receiving/services.py'='4cd351b5d2060e9b3543a64cd3add84b250b61639003f02f5b8f2b1da06279cd'
 'receiving/templates/receiving/comparison.html'='346cc968f7e354773b0d8c0b9d113d8d361ad138d679755ef5c0823004705a97'
 'receiving/templates/receiving/first_scan_scanner.html'='a1604daa10de8660b4152be5e2625e1f33bc2b8eb7d914c04381c1889ade0098'
 'receiving/test_first_scan_two_codes.py'='10554093ecdf4821611cd3ad6b9433a52c467c09bb711d0141d3f4ec53f2a9f8'
 'receiving/views.py'='402cf431172a5774d35123c15e773eaa76bc43cccfa30e8449f51cc6900daa8a'
 'receiving/urls.py'='5cb43b856e49487e854b84984d7016f551fecc4295f963a3186f8b51fcd35283'
 'receiving/tests.py'='f74900ba41d14a10bf56d114229a12f97c67b7ad78015224833e280f300ef22d'
 'receiving/tests_js/source_preview.test.cjs'='ee28800111cf813bfa8cbf2213c9e902496f46c85ec9378c934b24e7b096691b'
 'receiving/templates/receiving/configure_import.html'='5ee5a70fa1ddc5ebefe9661f64dfcf8a92f9cacf274d6dd921854e2f69efb76a'
 'static/css/app.css'='40c21546e3ade2a76387b057a1cd1d686bb953f73da6568760c29df8962c5893'
} }
function Baseline-Hashes { return [ordered]@{
 'receiving/forms.py'='2ea781ae28bb42e68394a3362c1640810e240a0fec47a4dc0c4dad00c259941b'
 'receiving/management/commands/export_continuity_state.py'='5d26acb4f7b21fc90fea827e82167c9ab9d9615b87a7caa7f1da11cd9d4e8e5b'
 'receiving/migrations/0018_container_first_scan_code_mode.py'=''
 'receiving/models.py'='26631f5612404450a145984e621dd8c7b1d4f8a99c2a67d368d74ff06363ed0a'
 'receiving/services.py'='58d77d6154d155c770a735eec2e3dd27f9e82a8684cbd92275a23dff1c49f8f2'
 'receiving/templates/receiving/comparison.html'='13a9ae3c141517abe62eb743100ce2950f157623d55ecfda90d94112c62fcfab'
 'receiving/templates/receiving/first_scan_scanner.html'='2f69675789e1bf1bfe534b1a06f600c1c920222426dedb1526315b7e0a9163ef'
 'receiving/test_first_scan_two_codes.py'=''
 'receiving/views.py'='990db73f08f3f6385904a4467adfcadecd84d793b574dc4c422cd7c56d30cba9'
 'receiving/urls.py'='b4ba35c95198a5480f80f7d64e19f927ed19efc1d4d68fc8f449f7087ac8a702'
 'receiving/tests.py'='fd79aef46aac9729b187b7e8a35cff81e2cf9144259ac0584e6cc5f75ad8256b'
 'receiving/tests_js/source_preview.test.cjs'=''
 'receiving/templates/receiving/configure_import.html'='850cd21ce789fa88e9171e26099070049808f29b6d70efea3c84b83cb7afb43c'
 'static/css/app.css'='4d783bf219f75c047afc6b58ca92315ff2f95a0ec0c83af731a4f3ff7e028434'
} }
function Preview-Hashes { return [ordered]@{
 'receiving/forms.py'='038061e49e20467f8b241cb6da3a5a8873c9c3978cb724d8dd3f475bd355cb17'
 'receiving/management/commands/export_continuity_state.py'='5d26acb4f7b21fc90fea827e82167c9ab9d9615b87a7caa7f1da11cd9d4e8e5b'
 'receiving/migrations/0018_container_first_scan_code_mode.py'=''
 'receiving/models.py'='26631f5612404450a145984e621dd8c7b1d4f8a99c2a67d368d74ff06363ed0a'
 'receiving/services.py'='59d196463569675b65ed6649928bab8fe67503b1f1fa5955469fbfa4c4270891'
 'receiving/templates/receiving/comparison.html'='13a9ae3c141517abe62eb743100ce2950f157623d55ecfda90d94112c62fcfab'
 'receiving/templates/receiving/configure_import.html'='5ee5a70fa1ddc5ebefe9661f64dfcf8a92f9cacf274d6dd921854e2f69efb76a'
 'receiving/templates/receiving/first_scan_scanner.html'='2f69675789e1bf1bfe534b1a06f600c1c920222426dedb1526315b7e0a9163ef'
 'receiving/test_first_scan_two_codes.py'=''
 'receiving/tests.py'='f74900ba41d14a10bf56d114229a12f97c67b7ad78015224833e280f300ef22d'
 'receiving/tests_js/source_preview.test.cjs'='ee28800111cf813bfa8cbf2213c9e902496f46c85ec9378c934b24e7b096691b'
 'receiving/urls.py'='5cb43b856e49487e854b84984d7016f551fecc4295f963a3186f8b51fcd35283'
 'receiving/views.py'='7ae5709392d9c0b385eb55bd8b5cad3e70874e8d8eef6edcb6bbf89fa7c886dd'
 'static/css/app.css'='40c21546e3ade2a76387b057a1cd1d686bb953f73da6568760c29df8962c5893'
} }
function Stable-SecondScan-Hashes { return [ordered]@{
 'receiving/migrations/0017_second_scan_operational.py'='a64d62896c3f7a6cc8e7127c44782112fafb889395745d9c98cdbbaea9752b72'
 'receiving/second_scan.py'='e60c07ea918e2ba829de369c444774e5cb86a5a18711a470149395d621774670'
 'receiving/templates/receiving/container_detail.html'='06c31defb084e93d61261d0544164ff1aa2e050971d52aa3ca5d8e1ae7f1699b'
 'receiving/templates/receiving/second_scan_scanner.html'='dc9e62826f1359bb69447c4f99f8f709ba035aa6969d1a885ef7d85e3d7e737f'
 'receiving/test_second_scan.py'='fea0cebbaf2d1918e8632d647213d4eb1c616994b7eff0d27d66e7cafe898058'
 'receiving/tests_js/second_scan.test.cjs'='669d81f33e2e6f7b07049135d2f8690d489624e85725b2fe81de58d7c5873762'
} }
function Assert-Installed-Baseline($Schema,[string]$Target) {
 $expected=Expected-Hashes
 $baseline=Baseline-Hashes
 foreach($relative in $expected.Keys) {
  $actual=Source-Hash $Target $relative
  $preview=(Preview-Hashes)[$relative]
  Require ($actual -in @($baseline[$relative],$preview,$expected[$relative])) "Installed file differs from stable 1006.1629, preview 1006.1701 and this update: $relative"
 }
 foreach($pair in (Stable-SecondScan-Hashes).GetEnumerator()) {
  Require ((Source-Hash $Target $pair.Key) -eq $pair.Value) "Stable Second Scan file differs: $($pair.Key)"
 }
 Require (@($Schema.migrations | Where-Object {$_ -eq '0017_second_scan_operational'}).Count -eq 1) 'Stable migration 0017 is not applied.'
 Require (@($Schema.migrations | Where-Object {$_ -eq '0018_container_first_scan_code_mode'}).Count -le 1) 'Migration 0018 state is inconsistent.'
 foreach($table in @('receiving_firstscansession','receiving_firstscanevent','receiving_firstscanpause','receiving_firstscanphoto','receiving_secondscansession','receiving_secondscanmovement')) {
  Require ($null -ne $Schema.counts.PSObject.Properties[$table]) "Required scanner table missing: $table"
 }
 Pass 'Installed code, scanner tables and migration state match the supported stable/preview baseline or this idempotent update.'
}
function Wait-Web([string]$Target,[int]$Seconds=180) {
 $timer=[Diagnostics.Stopwatch]::StartNew()
 while($timer.Elapsed.TotalSeconds -lt $Seconds) {
  $id=(In-App $Target { Compose @('ps','-a','-q','web') }).Trim()
  if($id) {
   $status=(Native 'docker' @('inspect','--format','{{.State.Status}}',$id)).Trim()
   $restarts=[int](Native 'docker' @('inspect','--format','{{.RestartCount}}',$id)).Trim()
   if($status -in @('exited','dead') -or $restarts -gt 0) { Fail "Web entrypoint failed: $status, restarts $restarts" }
   if($status -eq 'running') {
    $out=Native 'docker' @('top',$id,'-eo','pid,args')
    if($out -match '(gunicorn|uvicorn|manage.py\s+runserver)' -and $out -notmatch 'manage.py\s+migrate') { return }
   }
  }
  Start-Sleep -Seconds 2
 }
 Fail 'Web startup did not complete before the timeout.'
}
function Http([string]$Target) {
 $mapping=(In-App $Target { Compose @('port','web','8000') }).Trim()
 Require ($mapping -match ':(\d+)\s*$') 'Cannot discover web published port.'
 $port=[int]$matches[1]
 if ([IO.Path]::GetFullPath($Target).TrimEnd('\') -ieq 'C:\Docker-Projects\PON_Bikes_Automation') { Require ($port -eq 8001) "Expected port 8001, discovered $port." }
 $reply=Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$port/" -TimeoutSec 15
 Require ($reply.StatusCode -ge 200 -and $reply.StatusCode -lt 400) "HTTP check failed on port $port."
 Pass "HTTP responded on port $port."
}
function Install-Payload([string]$Target,[string]$Package) {
 $expected=Expected-Hashes
 foreach($relative in $expected.Keys) {
  $source=Join-Path (Join-Path $Package 'payload') $relative
  Require ((Test-Path -LiteralPath $source -PathType Leaf) -and (Hash $source) -eq $expected[$relative]) "Payload invalid: $relative"
  $destination=Join-Path $Target $relative
  New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force | Out-Null
  if ((Source-Hash $Target $relative) -ne $expected[$relative]) { Copy-Item -LiteralPath $source -Destination $destination -Force }
  Require ((Source-Hash $Target $relative) -eq $expected[$relative]) "Installed payload invalid: $relative"
 }
 $sourceDir=Join-Path $Target 'maintenance/release_source'
 New-Item -ItemType Directory -Path $sourceDir -Force | Out-Null
 foreach($sourceName in @('PON.Update.Common.ps1','Build_PON_Update_Manifest.ps1')) {
  $origin=Join-Path (Join-Path $Package 'source') $sourceName
  if($sourceName -eq 'PON.Update.Common.ps1') { $origin=Join-Path (Join-Path $Package '_support') $sourceName }
  $dest=Join-Path $sourceDir $sourceName
  if((Source-Hash $Target ('maintenance/release_source/'+$sourceName)) -ne (Hash $origin)){Copy-Item -LiteralPath $origin -Destination $dest -Force}
  Require ((Hash $dest) -eq (Hash $origin)) "Updater source did not install: $sourceName"
 }
 Pass 'First Scan 2 CODES logic, source preview and canonical updater source converged.'
}
function Find-ReleaseBackup([string]$Root,[string]$Release,[string[]]$Statuses=@('applied')) {
 Require (Test-Path -LiteralPath $Root -PathType Container) 'Backup root is unavailable.'
 $matches=New-Object System.Collections.Generic.List[object]
 foreach($directory in Get-ChildItem -LiteralPath $Root -Directory | Sort-Object LastWriteTime -Descending) {
  $statePath=Join-Path $directory.FullName 'UPDATE_STATE.json'
  if(-not (Test-Path -LiteralPath $statePath -PathType Leaf)){continue}
  try{$state=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json}catch{continue}
  if([string]$state.release -eq $Release -and $Statuses -contains [string]$state.status){$matches.Add([pscustomobject]@{Directory=$directory.FullName;State=$state;StatePath=$statePath})}
 }
 Require ($matches.Count -gt 0) "No safety backup for release $Release with status $($Statuses -join ', ') was found."
 return $matches[0]
}
function Restore-DB([string]$Target,[string]$Dump) {
 Require (Test-Path -LiteralPath $Dump -PathType Leaf) 'Rollback dump missing.'
 $id=(In-App $Target { Compose @('ps','-q','db') }).Trim()
 Require ($id -match '^[a-zA-Z0-9]+$') 'Database container missing.'
 $envs=Db-Env $id
 $remote='/tmp/pon_rollback_'+[guid]::NewGuid().ToString('N')+'.sql'
 $null=Native 'docker' @('cp',$Dump,("${id}:$remote"))
 try {
  $null=Native 'docker' @('exec',$id,'dropdb','-U',$envs['POSTGRES_USER'],'--if-exists','--force',$envs['POSTGRES_DB'])
  $null=Native 'docker' @('exec',$id,'createdb','-U',$envs['POSTGRES_USER'],'-O',$envs['POSTGRES_USER'],$envs['POSTGRES_DB'])
  $null=Native 'docker' @('exec',$id,'psql','-v','ON_ERROR_STOP=1','-U',$envs['POSTGRES_USER'],'-d',$envs['POSTGRES_DB'],'-f',$remote)
 } finally { try { $null=Native 'docker' @('exec',$id,'rm','-f',$remote) } catch { Warn 'Rollback SQL temporary cleanup failed.' } }
}
function Inspect-LegacyDump([object]$Backup,[string]$Dump,[object]$CurrentSchema) {
 Require ((Test-Path -LiteralPath $Dump -PathType Leaf) -and (Get-Item -LiteralPath $Dump).Length -gt 1000) 'Old 1006.0752 SQL dump is missing/empty.'
 $name='pon_legacy_verify_'+[guid]::NewGuid().ToString('N').Substring(0,12)
 $image=(Native 'docker' @('inspect','--format','{{.Config.Image}}',$Backup.DbId)).Trim()
 $null=Native 'docker' @('run','-d','--name',$name,'-e',('POSTGRES_USER='+$Backup.DbEnv['POSTGRES_USER']),'-e',('POSTGRES_DB='+$Backup.DbEnv['POSTGRES_DB']),'-e',('POSTGRES_PASSWORD='+$Backup.DbEnv['POSTGRES_PASSWORD']),$image)
 try {
  $ready=$false
  for($n=0;$n -lt 45;$n++) {
   $null=& docker exec $name pg_isready -U $Backup.DbEnv['POSTGRES_USER'] -d $Backup.DbEnv['POSTGRES_DB'] 2>$null
   if($LASTEXITCODE -eq 0){$ready=$true;break};Start-Sleep -Seconds 2
  }
  Require $ready 'Old SQL dump isolated database failed to start.'
  $null=Native 'docker' @('cp',$Dump,("${name}:/tmp/old.sql"))
  $null=Native 'docker' @('exec',$name,'psql','-v','ON_ERROR_STOP=1','-U',$Backup.DbEnv['POSTGRES_USER'],'-d',$Backup.DbEnv['POSTGRES_DB'],'-f','/tmp/old.sql')
  $sql="SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = current_schema() AND tablename LIKE 'receiving_%' ORDER BY tablename"
  $names=(Native 'docker' @('exec',$name,'psql','-At','-U',$Backup.DbEnv['POSTGRES_USER'],'-d',$Backup.DbEnv['POSTGRES_DB'],'-c',$sql)) -split "`n"
  $old=@{}
  foreach($table in $names){
   if(!$table){continue}; Require ($table -match '^receiving_[a-z0-9_]+$') 'Unexpected old table name.'
   $old[$table]=[int64](Native 'docker' @('exec',$name,'psql','-At','-U',$Backup.DbEnv['POSTGRES_USER'],'-d',$Backup.DbEnv['POSTGRES_DB'],'-c',('SELECT COUNT(*) FROM "'+$table+'"'))).Trim()
   $query='SELECT md5(coalesce(string_agg(md5(row_to_json(t)::text), '''' ORDER BY md5(row_to_json(t)::text)), '''')) FROM "'+$table+'" t'
   $digest=(Native 'docker' @('exec',$name,'psql','-At','-U',$Backup.DbEnv['POSTGRES_USER'],'-d',$Backup.DbEnv['POSTGRES_DB'],'-c',$query)).Trim()
   Require ($digest -eq [string]$CurrentSchema.digests.PSObject.Properties[$table].Value) "Old backup differs in operational table $table despite equal row counts; restoring it would lose data."
  }
  Require ($old.Count -gt 10) 'Old backup is missing receiving schema.'
  $oldObject=[pscustomobject]$old
  Compare-Counts $oldObject $CurrentSchema.counts
  Pass 'Old 1006.0752 dump restored independently; all pre-existing tables, including First Scan, have unchanged counts.'
  return $oldObject
 } finally { $null=Native 'docker' @('rm','-f',$name) }
}
function Verify-IsolatedApplication([object]$Backup,[string]$Package,[object]$BeforeSchema) {
 $dir=Join-Path $Backup.Directory 'isolated_application'
 Expand-Archive -LiteralPath $Backup.Archive -DestinationPath $dir
 # This is the restored current application with the intended minimal code
 # integration applied only to the isolated copy, never to the active tree.
 Install-Payload $dir $Package
 $fixture=Join-Path $Package '_fixtures'
 if(Test-Path -LiteralPath $fixture -PathType Container) {
  $samples=Join-Path $dir 'sample_data';New-Item -ItemType Directory -Path $samples -Force | Out-Null
  Get-ChildItem -LiteralPath $fixture -File | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $samples $_.Name) -Force }
 }
 $keys=@('COMPOSE_PROJECT_NAME','PON_WEB_PORT','PON_HOST_PATH','PON_PRODUCT_HOST_DIR','PON_MOVES_HOST_DIR','PON_IMPORT_HOST_DIR','PON_REPORT_HOST_DIR','PON_TRANSLOGIC_IMPORT_HOST_DIR','PON_PRODUCT_MOVES_DIRECT_HOST_DIR','PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED','PON_PRODUCT_MOVES_DIRECT_ENABLED')
 $saved=@{};foreach($key in $keys){$saved[$key]=[Environment]::GetEnvironmentVariable($key,'Process')}
 $project='pon_repair_test_'+[guid]::NewGuid().ToString('N').Substring(0,12)
 $listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0);$listener.Start();$port=$listener.LocalEndpoint.Port;$listener.Stop()
 try {
  $env:COMPOSE_PROJECT_NAME=$project;$env:PON_WEB_PORT=[string]$port;$env:PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED='0';$env:PON_PRODUCT_MOVES_DIRECT_ENABLED='0'
  foreach($key in $keys | Where-Object {$_ -like 'PON_*_HOST_DIR' -or $_ -eq 'PON_HOST_PATH'}) {
   $path=Join-Path $Backup.Directory ('isolated_data/'+$key);New-Item -ItemType Directory -Path $path -Force | Out-Null
   [Environment]::SetEnvironmentVariable($key,$path,'Process')
  }
  $null=In-App $dir { Compose @('up','-d','db') }
  $db=(In-App $dir { Compose @('ps','-q','db') }).Trim();Require ($db -match '^[a-zA-Z0-9]+$') 'Isolated DB missing.'
  $ready=$false
  for($n=0;$n -lt 45;$n++) {
   $null=& docker exec $db pg_isready -U $Backup.DbEnv['POSTGRES_USER'] -d $Backup.DbEnv['POSTGRES_DB'] 2>$null
   if($LASTEXITCODE -eq 0){$ready=$true;break};Start-Sleep -Seconds 2
  }
  Require $ready 'Isolated application PostgreSQL is not ready.'
   $isolatedEnv=Db-Env $db
  $null=Native 'docker' @('cp',$Backup.Dump,("${db}:/tmp/safety.sql"))
  $null=Native 'docker' @('exec',$db,'psql','-v','ON_ERROR_STOP=1','-U',$isolatedEnv['POSTGRES_USER'],'-d',$isolatedEnv['POSTGRES_DB'],'-f','/tmp/safety.sql')
  $null=In-App $dir { Compose @('build','web') }
  $null=In-App $dir { Compose @('up','-d','web') }
  Wait-Web $dir
  Check-App $dir -Tests
  Check-JS $dir
  Check-PreviewJS $dir
  Check-TIIUReference $dir
  $isolatedAfter=Schema $dir
  Compare-FirstScanMigrationState $BeforeSchema $isolatedAfter
  Http $dir
  Pass 'Independent restored application, database, complete tests and HTTP passed.'
 } finally {
  try { $null=In-App $dir { Compose @('down') } } catch { Warn 'Isolated Docker cleanup failed. Inspect only the isolated project.' }
  foreach($key in $keys) { [Environment]::SetEnvironmentVariable($key,$saved[$key],'Process') }
 }
}
function Restore-PreUpdateBaseline([string]$Target,[string]$OldDir,[object]$OldSchema) {
 $oldDump=Join-Path $OldDir 'database_before_update.sql'
 $legacy=@('receiving/models.py','receiving/urls.py','receiving/templates/receiving/container_detail.html')
 $new=@('receiving/migrations/0017_second_scan_operational.py','receiving/second_scan.py','receiving/templates/receiving/second_scan_scanner.html','receiving/test_second_scan.py','receiving/tests_js/second_scan.test.cjs')
 foreach($p in $legacy) { Require (Test-Path -LiteralPath (Join-Path $OldDir $p) -PathType Leaf) "Old code backup missing $p" }
 $expectedBase=@{'receiving/models.py'='27ace795080df078ef011e3df26be16dec8ce5d20c39a36b1774bc966755d7f0';'receiving/urls.py'='20e6307fb4f319c46775b76d329ceca3ac8caa3968a1e3c4bd20617a75a6f970';'receiving/templates/receiving/container_detail.html'='b7b2b251e741358ea8215808b8333d35736a98765be17669a742e6036870f8da'}
 foreach($p in $legacy) { Require ((Hash (Join-Path $OldDir $p)) -eq $expectedBase[$p]) "Old code backup differs: $p" }
 $null=In-App $Target { Compose @('stop','web') }
 foreach($p in $legacy) { Copy-Item -LiteralPath (Join-Path $OldDir $p) -Destination (Join-Path $Target $p) -Force }
 foreach($p in $new) { $path=Join-Path $Target $p;if(Test-Path -LiteralPath $path -PathType Leaf){Remove-Item -LiteralPath $path -Force} }
 Restore-DB $Target $oldDump
 $null=In-App $Target { Compose @('build','web') }
 $null=In-App $Target { Compose @('up','-d','--force-recreate','web') }
 Wait-Web $Target
 $clean=Schema $Target
 Compare-Counts $OldSchema $clean.counts
 Require (@($clean.migrations | Where-Object {$_ -eq '0017_second_scan_operational'}).Count -eq 0) 'Old baseline still has 0017 applied.'
 $out=Run-Read $Target @('check');Require ($out -match 'System check identified no issues') 'Old baseline Django check failed.'
 Http $Target
 Pass 'Path B pre-update code and PostgreSQL baseline restored and checked.'
}
