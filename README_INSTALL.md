# PON Bikes Automation — Incremental Installation Standard
Release: 0930.1114

## Release 0930.1114 behaviour
- Continuity Snapshot hotfix only.
- Fixes `template: :1: function "com" not defined` in manual step 05 by replacing the Docker Go-template label lookup with normal `docker inspect` JSON parsing in PowerShell.
- No operational PON runtime, database, migration, workflow or validation-04 logic change.


## Release 0930.1047 behaviour
- Continuity Snapshot creation is now an explicit **manual step 05**.
- `04_VALIDATE.ps1` validates only and never creates/publishes/updates a Continuity Snapshot.
- With `Failures: 0`, 04 prints `NEXT: .\05_CREATE_CONTINUITY_SNAPSHOT.ps1` in green.
- New root launchers: `05_CREATE_CONTINUITY_SNAPSHOT.ps1` and `05_CREATE_CONTINUITY_SNAPSHOT.bat`.
- 05 reuses the installed `tools\Create_Continuity_Snapshot.ps1`; no second snapshot engine exists.
- Every valid snapshot now also includes `VALIDATION_STATE.txt`, `ENVIRONMENT_STATE.txt`, `EXTERNAL_ACCESS_STATE.txt`, `LAST_VALIDATION.log`, and `DATABASE_BACKUP_REFERENCE.txt`.
- Includes the 0929.1616 null-safe Continuity output fix.
- No operational application or database schema change.


## Release 0929.1322 behaviour
- Preserves the existing stable installation, database, file generation formats and Completed/Pending logic.
- `01_PREPARE_INSTALL.ps1` now inspects the **actual configured Translogic paths** before direct access is enabled. It checks mapped-drive and available UNC candidates rather than assuming that `T:` is visible inside Docker.
- The Translogic import destination is enabled for direct copy only after a Docker **read/write** probe succeeds. A temporary probe file is created and removed during this check.
- If exactly one real coherent numbered file set 1–5 exists, 01 prints and records its actual filename pattern, extension and oldest file/time. No filename such as `ImproExtra` or `ImpProdExtra` is hard-coded.
- PRODUCT_MOVES direct Refresh is enabled only when the configured real `PRODUCT_MOVES.CSV` exists and Docker can read its folder. Otherwise the existing local bridge/manual-upload process remains active.
- `04_VALIDATE.ps1` re-checks Django, migrations, tests, paths, real Translogic discovery and PRODUCT_MOVES source visibility.

### Important during 01
Read the Translogic preflight lines. They will state one of the following outcomes:

- direct destination **READ/WRITE VERIFIED**, plus the real numbered pattern/oldest file when safely found; or
- direct destination **NOT VERIFIED**, in which case Download/manual transfer remains active;
- direct PRODUCT_MOVES **VERIFIED**; or
- direct PRODUCT_MOVES **NOT VERIFIED**, in which case the previous bridge/manual-upload flow remains active.

Do not manually force the direct feature flags if preflight failed.

## Release 0929.1248 behaviour
- Validation-only hotfix: updates one presentation test that used a brittle mixed HTML fragment comparison.
- No application runtime, business logic, database, migration, file processing or integration change.
- Re-validates the complete `receiving` test suite through `04_VALIDATE.ps1`.


## Release 0929.1227 behaviour
- Shows Generated and Uploaded timestamps separately using existing audit timestamps.
- Adds Container-ID filename guidance/warnings for manual source-file selection without blocking content-valid files.
- Downloads Customer Report as `<CONTAINER> Advised.xls` without changing report content.
- Shows UPStockSerial Source and Translogic destination paths and exposes a disabled Copy to Translogic control; direct copy is intentionally deferred.
- No database model or migration change is introduced by this release.


## Release 0929.1154 behaviour
- Step 2 shows the existing New Product Import Download action when ready and a clear non-action status when it is not ready.
- Container Detail keeps the Recent Containers sidebar visible on desktop, highlights the active container and allows direct container switching.
- Product Check remains centimetres for printed measurement presentation only; internal dimensions remain millimetres.
- A living `docs/` documentation set is now maintained with the application.
- No database model or migration change is introduced by this release.


## Release 0929.1059 behaviour
- The workflow progress bar is now a stage selector: only the selected stage appears immediately below it.
- Step 2 exposes direct Download actions for Product Check + barcodes and, when existing rules allow it, New Product Import.
- Product Check prints Length / Width / Height in centimetres only; stored dimensions and Translogic exports remain millimetres.
- No new database migration is introduced by this release.

## Release 0922.1335 behaviour
Output files are now operator-facing **downloads only**. The normal UI does not show Generate or Regenerate actions. If a current file must be rebuilt because its inputs changed, the application refreshes it automatically when Download is clicked.

## Permanent application folder
From this release onward, the active application lives at:

`C:\Docker-Projects\PON_Bikes_Automation`

Future releases should **not** create version-numbered application folders. Each update ZIP is unpacked in Downloads and updates this same stable folder.

## Open PowerShell in the extracted ZIP folder
Double-click:

`00_OPEN_POWERSHELL_HERE.bat`

It opens a new PowerShell window already positioned in the folder where the update ZIP was extracted. You do not need to right-click the folder or manually type `cd`.

The window shows the normal command sequence for 01, 02, 04, 05 and rollback 03.


### 01 — Prepare install/update
`powershell -ExecutionPolicy Bypass -File .\01_PREPARE_INSTALL.ps1`

What it does:
- Detects the current stable install, or the newest legacy `PON_Bike_Automation_*` folder on the first migration.
- Creates a full application snapshot under `C:\Docker-Projects\PON_Bikes_Automation_Backups`.
- Creates a PostgreSQL logical backup before touching the installation.
- Copies the new release to `C:\Docker-Projects\PON_Bikes_Automation`.
- Preserves the current `.env`.
- Does **not** apply migrations yet.

### 02 — Apply update
`powershell -ExecutionPolicy Bypass -File .\02_APPLY_UPDATE.ps1`

What it does:
- Rebuilds/recreates the web container.
- Keeps the existing PostgreSQL named volume.
- Applies Django migrations.
- Runs `manage.py check`.
- Shows receiving migration status.

### 03 — Roll back last update
`powershell -ExecutionPolicy Bypass -File .\03_ROLLBACK.ps1`

What it does:
- Requires typing `ROLLBACK` before proceeding.
- Stops the web service.
- Restores the previous application snapshot.
- Restores the PostgreSQL snapshot taken by 01.
- Rebuilds the previous web version and runs Django check.

For unattended rollback only:
`powershell -ExecutionPolicy Bypass -File .\03_ROLLBACK.ps1 -Force`

### 04 — Validate
`powershell -ExecutionPolicy Bypass -File .\04_VALIDATE.ps1`

What it checks:
- compose.yaml and .env.
- Docker web/database containers.
- Django system check.
- Receiving migrations.
- Database connectivity and counts.
- Product/movement/import/report host folders.
- Default `products_pon_pbp_auto.xls` presence.
- HTTP response on the configured app port.

Validation logs are stored in:
`C:\Docker-Projects\PON_Bikes_Automation\logs`

### 05 — Create Continuity Snapshot (manual)
`powershell -ExecutionPolicy Bypass -File .\05_CREATE_CONTINUITY_SNAPSHOT.ps1`

What it does:
- Requires the latest validation log to contain no `[FAIL]` entries.
- Reuses the installed `tools\Create_Continuity_Snapshot.ps1`.
- Reads installed physical code, current Django/PostgreSQL state, configured source references, latest validation evidence and rollback-backup references.
- Creates a timestamped Continuity ZIP and updates `PON_Bikes_Automation_Continuity_LATEST.zip` only after the candidate ZIP is complete and verified.
- Does not modify operational records.

A double-click wrapper is also available: `05_CREATE_CONTINUITY_SNAPSHOT.bat`.

## Normal update sequence
1. Extract the ZIP in Downloads.
2. Double-click `00_OPEN_POWERSHELL_HERE.bat`.
3. In the PowerShell window, run `./01_PREPARE_INSTALL.ps1`.
4. Run `./02_APPLY_UPDATE.ps1`.
5. Run `./04_VALIDATE.ps1`.
6. If `Failures: 0`, run `./05_CREATE_CONTINUITY_SNAPSHOT.ps1`.
7. If the release is not acceptable, run `./03_ROLLBACK.ps1`.

## Important
Never use `docker compose down -v` for this application. The `-v` option can remove persistent named volumes.

## Incremental update model
Updates are incremental from the operator's point of view: the active folder never changes, `.env` and persistent Docker volumes are preserved, and every update gets its own rollback snapshot.

For reliability, each ZIP contains a complete application payload rather than only changed files. This avoids stale files or missing dependencies while still updating the same permanent installation folder.

`01_PREPARE_INSTALL.ps1` also validates `PACKAGE_MANIFEST_SHA256.txt` before modifying the installed application.

## 0929.0719 migration hotfix

This package fixes the Django 5.1 aggregation error in migration `0013_multi_container_job_order`. If 0928.1528 stopped during `02_APPLY_UPDATE.ps1`, use this package and run the normal `00 -> 01 -> 02 -> 04` sequence. A rollback is not required before applying this hotfix.

## 0929.1121 validation hotfix
This package does not change application runtime behaviour from 0929.1059. It updates outdated regression-test expectations so the full validation suite reflects the intentionally changed UI and Product Check cm presentation.

## Continuity Snapshot — manual step 05 from 0930.1047

`04_VALIDATE.ps1` performs validation only. When it finishes with zero failures it shows:

```text
NEXT:
.\05_CREATE_CONTINUITY_SNAPSHOT.ps1
```

Run 05 manually to create:

```text
C:\Docker-Projects\PON_Bikes_Automation\continuity\PON_Bikes_Automation_Continuity_<timestamp>.zip
C:\Docker-Projects\PON_Bikes_Automation\continuity\PON_Bikes_Automation_Continuity_LATEST.zip
```

05 reuses the installed `tools\Create_Continuity_Snapshot.ps1`. It requires the latest validation log to contain no `[FAIL]` entries. A failed snapshot never replaces a previous valid `LATEST`.

The console convention is: green = PASS/success, red = FAIL/error, yellow = WARN/non-blocking fallback, cyan = INFO/path/version/next step.
