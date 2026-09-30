# PON Bikes Automation — Incremental Installation Standard
Release: 0921.1306

## Permanent application folder
From this release onward, the active application lives at:

`C:\Docker-Projects\PON_Bikes_Automation`

Future releases should **not** create version-numbered application folders. Each update ZIP is unpacked in Downloads and updates this same stable folder.

## Run from the extracted ZIP folder
Use Windows PowerShell in the folder you extracted from Downloads.

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

## Normal update sequence
1. Extract the ZIP in Downloads.
2. Open PowerShell in the extracted folder.
3. Run `01_PREPARE_INSTALL.ps1`.
4. Run `02_APPLY_UPDATE.ps1`.
5. Run `04_VALIDATE.ps1`.
6. If the release is not acceptable, run `03_ROLLBACK.ps1`.

## Important
Never use `docker compose down -v` for this application. The `-v` option can remove persistent named volumes.

## Incremental update model
Updates are incremental from the operator's point of view: the active folder never changes, `.env` and persistent Docker volumes are preserved, and every update gets its own rollback snapshot.

For reliability, each ZIP contains a complete application payload rather than only changed files. This avoids stale files or missing dependencies while still updating the same permanent installation folder.

`01_PREPARE_INSTALL.ps1` also validates `PACKAGE_MANIFEST_SHA256.txt` before modifying the installed application.
