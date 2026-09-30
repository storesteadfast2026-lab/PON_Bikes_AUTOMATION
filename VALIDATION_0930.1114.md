# PON Bikes Automation — Validation 0930.1114

## Package-level validation completed before delivery
- PASS: the failing Docker Go-template command was identified exactly in `tools/Create_Continuity_Snapshot.ps1`.
- PASS: the Go-template lookup was removed and replaced with normal `docker inspect` JSON parsing.
- PASS: no `docker inspect -f` / Compose-label Go-template remains in the Continuity Snapshot implementation.
- PASS: `05_CREATE_CONTINUITY_SNAPSHOT.ps1` is unchanged.
- PASS: `04_VALIDATE.ps1` is unchanged.
- PASS: receiving runtime code is unchanged.
- PASS: model and migration files are unchanged.
- PASS: snapshot candidate/LATEST publication protection remains unchanged.

## Runtime validation required on the installed Windows/Docker environment
After applying this incremental hotfix, run the normal validation and then manual step 05:

1. `01_PREPARE_INSTALL.ps1`
2. `02_APPLY_UPDATE.ps1`
3. `04_VALIDATE.ps1`
4. `05_CREATE_CONTINUITY_SNAPSHOT.ps1`

Step 05 is considered successful only when:
- no Docker template parsing error is emitted;
- a timestamped `PON_Bikes_Automation_Continuity_<timestamp>.zip` exists;
- `PON_Bikes_Automation_Continuity_LATEST.zip` is updated;
- both paths are printed by the snapshot tool/launcher;
- process exit code is 0.
