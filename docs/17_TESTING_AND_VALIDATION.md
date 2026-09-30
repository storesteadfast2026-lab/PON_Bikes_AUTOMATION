# 17 — Testing and Validation

A release is considered runtime-valid only after the installed Docker environment completes `04_VALIDATE.ps1` with `Failures: 0`.

04 checks, as applicable:

- `compose.yaml` and `.env`;
- Docker web/database containers;
- Django system check;
- receiving migrations;
- `makemigrations --check --dry-run`;
- PostgreSQL access;
- non-blank Job Order uniqueness;
- complete `receiving` test suite;
- configured working folders and Product Master;
- current Translogic/direct-access preflight state;
- PRODUCT_MOVES configured runtime source;
- HTTP response on port 8001.

## Separation from Continuity Snapshot

From release **0930.1047**, 04 is validation-only. It does not create, publish or update a Continuity Snapshot.

With zero failures it prints the next manual action:

```powershell
.\05_CREATE_CONTINUITY_SNAPSHOT.ps1
```

05 uses the latest validation log as evidence and will not publish a new authoritative snapshot if that log contains `[FAIL]` entries.

## Translogic warnings

If direct T:/UNC access cannot be verified, 04 may report warnings while the existing safe fallback remains active. Direct integration must not be reported as active unless its preflight passed.

## Continuity exporter regression protection

The Django continuity state exporter remains read-only and machine-readable. Snapshot creation uses installed physical code/database/configuration as authoritative state and does not modify operational records.
