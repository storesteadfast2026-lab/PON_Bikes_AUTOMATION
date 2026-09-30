# Release History

This file summarises the stable release line. Detailed per-release changes remain in the `CHANGELOG_<version>.md` files.

- **0930.1047** — Continuity Snapshot separated into explicit manual step 05; 04 validation-only; five additional validation/environment/external-access/backup-reference files added to every snapshot; includes 0929.1616 null-output reliability fix. No operational runtime or database change.
- **0929.1525** — Continuity Snapshot system generated from installed code/database/source references after successful validation; manual snapshot tools; continuity preservation across updates; standard green/red/yellow/cyan installer output; validation-only fix for the 0929.1322 presentation assertion. No database migration or operational workflow change.
- **0929.1322** — Guarded Translogic file exchange: explicit verified UPStockSerial copy, runtime discovery of the real numbered New Product Import 1–5 set with oldest-file replacement confirmation, and optional direct PRODUCT_MOVES Refresh only after real host/Docker access preflight. No database migration or output-format change.
- **0929.1248** — Validation-only hotfix for the Container-ID filename-hint presentation test; no runtime application behaviour changed.
- **0929.1227** — Generated/Uploaded provenance display, Container-ID filename guidance/warnings, Customer Report download name `<CONTAINER> Advised.xls`, and visible UPStockSerial source/destination with disabled Copy to Translogic placeholder. No business logic or database change.
- **0929.1154** — Step 2 New Product Import visibility/status, persistent Recent Containers sidebar in Container Detail, living documentation set. Product Check remains cm presentation with internal mm storage.
- **0929.1121** — validation/test alignment hotfix; stable baseline with complete receiving test suite passing in the installed environment.
- **0929.1059** — stage selector UI and Product Check cm presentation.
- **0929.0719** — migration-state alignment for ShortNameDictionaryRule fields.
- **0929.0712** — multi-container/auto-mapping validation fixes.
- **0928.1619** — migration hotfix.
- **0928.1528** — multi-container manifests, Job Order uniqueness/priority, automatic mapping and saved mapping profiles.

Older historical notes remain in existing CHANGELOG/VALIDATION and dated documentation files.

- **0929.1616** — Continuity Snapshot PowerShell null-output hotfix; no operational application changes.

- **0930.1602** — Added PON/PBP-aware three-way Product Check classification (`Existing`, `PBP → PON`, `New`); reused valid historical PBP Translogic measurements for the existing New Product Import workflow; added orange Customer Report migration rows without changing report calculations.
