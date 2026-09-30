# PON Bikes Automation — 1001.0734

Minimal validation hotfix for release 0930.1602.

## Change
- `receiving/tests.py`: `PbpToPonMigrationTests.setUp()` now uses `Group1Family.objects.update_or_create(...)` for the existing `Cervelo` rule instead of attempting to create a duplicate unique `family_name`.

## Runtime impact
None. No operational code, models, migrations, database logic, Docker/configuration, Git handling, PBP → PON logic, Product Check, New Product Import, or Customer Report behaviour was changed.
