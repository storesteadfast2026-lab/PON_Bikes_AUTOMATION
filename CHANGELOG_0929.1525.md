# PON Bikes Automation — Change Log 0929.1525

## Scope

Continuity / maintainability release. No receiving business rule, database schema, output file format, serial logic, movement logic, Product Check logic, New Product Import content, UPStockSerial content or Customer Report content is changed.

## Changes

- Added automatic **Continuity Snapshot** generation after a successful `04_VALIDATE.ps1` run.
- Added manual tools:
  - `tools\Create_Continuity_Snapshot.ps1`
  - `tools\Create_Continuity_Snapshot.bat`
- Snapshot is generated from the physically installed code, running Django/PostgreSQL state, installed Markdown documentation and accessible external-source metadata.
- Snapshot ZIP includes `CURRENT_STATE.md`, `BASELINE_CODE.zip`, `FILE_HASHES.csv`, `DB_STATE.json`, `WORKFLOW_STATE.txt`, `SOURCE_FILES.txt`, `DICTIONARY_STATE.txt`, `INSTALLED_PACKAGES.txt` and `README_CONTINUE.md`.
- `.env`, credentials, tokens, private keys, full DB dumps, logs, generated media, previous snapshots and caches are excluded from baseline code. Secret-like values in `.env.example` are redacted in the snapshot copy.
- Existing continuity snapshots are preserved by future `01_PREPARE_INSTALL.ps1` runs.
- Added read-only Django management command `export_continuity_state` for machine-readable technical/workflow state.
- Added validation that the continuity state exporter does not modify operational rows.
- Fixed the stale 0929.1322 presentation assertion so the test matches the current guarded Translogic message.
- Standardised update-script console status colours: green PASS/success, red FAIL/error, yellow WARN/fallback, cyan informational output.

## Database

No migration. No schema change.

## Operational impact

None. Snapshot generation is read-only with respect to operational data.
