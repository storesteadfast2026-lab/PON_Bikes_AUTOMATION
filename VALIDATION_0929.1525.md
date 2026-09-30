# PON Bikes Automation — Validation 0929.1525

## Build-time checks completed

- Python syntax compilation: PASS for the new continuity management command and updated test module.
- No model or migration file changed.
- Existing operational services and output builders remain unchanged.
- Continuity tooling is additive and read-only by design.
- Required snapshot file names and exclusion rules are defined in the installed tool.
- Previous continuity snapshots are restored after the application payload is copied during future updates.
- Stale 0929.1322 UI assertion updated to the current guarded-copy message.

## Runtime validation performed by `04_VALIDATE.ps1`

The installed Docker environment must still verify:

- Django system check;
- all receiving migrations applied;
- models match migration state;
- PostgreSQL connectivity;
- Job Order uniqueness;
- complete `receiving` test suite, including the read-only continuity exporter test;
- configured source/working folders;
- Product Master availability;
- PRODUCT_MOVES runtime source/fallback;
- HTTP response on port 8001.

Only if all checks above have zero failures does `04_VALIDATE.ps1` run the Continuity Snapshot tool.

The snapshot tool then verifies the required files are present inside the final ZIP before updating `PON_Bikes_Automation_Continuity_LATEST.zip`.

A snapshot failure must be reported as a validation failure and must not replace the previous valid LATEST snapshot.
