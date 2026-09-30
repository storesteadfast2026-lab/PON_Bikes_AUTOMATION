# 16 — Install, Update, Validate, Continuity and Rollback

PON Bikes Automation uses one stable installation directory and incremental update packages.

## Stable installation

```text
C:\Docker-Projects\PON_Bikes_Automation
```

## Standard update sequence

After extracting `PON_Bikes_Automation_Update_<MMDD.HHmm>.zip`:

```powershell
.\01_PREPARE_INSTALL.ps1
.\02_APPLY_UPDATE.ps1
.\04_VALIDATE.ps1
.\05_CREATE_CONTINUITY_SNAPSHOT.ps1
```

`00_OPEN_POWERSHELL_HERE.bat` opens PowerShell in the extracted update directory.

## Responsibilities

- **01** verifies package integrity, creates rollback code/DB backups, preserves `.env`, copies the release and preserves prior Continuity snapshots.
- **02** rebuilds/recreates the web container, applies migrations and runs Django system check.
- **04** performs runtime validation only. It never creates or publishes a Continuity Snapshot.
- **05** is the explicit/manual Continuity Snapshot step and reuses the installed snapshot tool.
- **03** is rollback-only and is used only when restoration is actually required.

Never use `docker compose down -v` as part of the update process.

## Manual Continuity step

When 04 finishes with zero failures it prints:

```text
NEXT:
.\05_CREATE_CONTINUITY_SNAPSHOT.ps1
```

05 requires a latest validation log without `[FAIL]` entries. It then generates a timestamped snapshot and updates `PON_Bikes_Automation_Continuity_LATEST.zip` only after the candidate ZIP is complete and verified.

A failed snapshot does not replace a previous valid `LATEST`.

## Rollback

Use `03_ROLLBACK.ps1` only when restoration is actually required. It uses the snapshot produced by 01. A failed validation may instead be corrected by a later incremental hotfix without rollback.

## Continuity preservation

The `continuity` folder is preserved when the stable application tree is replaced so prior snapshots are not lost during an update.

Console convention: **green = PASS/success**, **red = FAIL/error**, **yellow = WARN/non-blocking fallback**, **cyan = INFO/path/version/next step**.
