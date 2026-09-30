# PON Bikes Automation — Change Log 0930.1114

## Scope
Continuity Snapshot hotfix only.

## Change
- Replaced the single Docker Go-template lookup used to read the Compose project label in `tools/Create_Continuity_Snapshot.ps1`.
- Previous command used `docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}'` and failed on Windows/PowerShell with `template: :1: function "com" not defined` because the quoted label key was not preserved correctly for Docker's template parser.
- The tool now calls normal `docker inspect`, parses its JSON in PowerShell, and reads the existing `com.docker.compose.project` label from the returned object.

## Unchanged
- `05_CREATE_CONTINUITY_SNAPSHOT.ps1` launcher behaviour.
- `04_VALIDATE.ps1` validation logic.
- Snapshot publication safety: incomplete candidates never replace a valid `PON_Bikes_Automation_Continuity_LATEST.zip`.
- All operational PON code, database models, migrations, workflows, file formats and integrations.
