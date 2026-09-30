# 18 — Continuity Snapshot

PON Bikes Automation creates an authoritative Continuity Snapshot so development can continue in a new ChatGPT chat or Work session without depending on historical conversation context.

## Manual step 05

From release **0930.1047**, Continuity creation is explicitly manual and separate from validation.

Standard flow:

```text
01_PREPARE_INSTALL.ps1
02_APPLY_UPDATE.ps1
04_VALIDATE.ps1
05_CREATE_CONTINUITY_SNAPSHOT.ps1
```

04 validates only. When it reaches zero failures it shows the 05 command in green.

05 reuses:

```text
tools\Create_Continuity_Snapshot.ps1
```

No duplicate snapshot engine exists.

## Authoritative sources

The snapshot is generated from:

1. physical code installed in `C:\Docker-Projects\PON_Bikes_Automation`;
2. the running Django/PostgreSQL database state;
3. installed Markdown documentation;
4. real configured external-source references and current accessibility evidence;
5. the most recent validation log;
6. current update/rollback metadata.

Historical chat descriptions are not a source of truth.

## Output

```text
C:\Docker-Projects\PON_Bikes_Automation\continuity\
PON_Bikes_Automation_Continuity_<yyyyMMdd_HHmmss>.zip
PON_Bikes_Automation_Continuity_LATEST.zip
```

`LATEST` is replaced only after the new candidate ZIP has been built and verified as complete. If 05 fails, any prior valid `LATEST` remains untouched.

## Required snapshot contents

- `CURRENT_STATE.md`
- `BASELINE_CODE.zip`
- `FILE_HASHES.csv`
- `DB_STATE.json`
- `WORKFLOW_STATE.txt`
- `SOURCE_FILES.txt`
- `DICTIONARY_STATE.txt`
- `INSTALLED_PACKAGES.txt`
- `VALIDATION_STATE.txt`
- `ENVIRONMENT_STATE.txt`
- `EXTERNAL_ACCESS_STATE.txt`
- `LAST_VALIDATION.log`
- `DATABASE_BACKUP_REFERENCE.txt`
- `README_CONTINUE.md`

### VALIDATION_STATE.txt
Summarises the latest actual validation: installed release, Django check, migrations, model/migration consistency, database access, test count/result, port 8001, and current warnings.

### ENVIRONMENT_STATE.txt
Records non-secret runtime/environment information such as Python, Django, PostgreSQL, Docker/Compose, Docker project, web port and explicitly whitelisted operational paths/flags. Passwords, tokens and secrets are excluded.

### EXTERNAL_ACCESS_STATE.txt
Records current Translogic/PRODUCT_MOVES configured paths, Windows accessibility, mapped/UNC resolution when available, the last prepare preflight, direct Docker flags and the active safe fallback.

### LAST_VALIDATION.log
Contains only the most recent `Validation_*.txt` log present when 05 runs.

### DATABASE_BACKUP_REFERENCE.txt
References the latest rollback folder and `database_before_update.sql`, including existence/size/time when available. The database dump itself is never embedded in the Continuity ZIP.

## Security

`BASELINE_CODE.zip` excludes `.env`, database dumps, generated media, logs, prior continuity snapshots, maintenance/update state, caches, virtual environments, credentials, tokens and private-key files. Secret/password/token values in `.env.example` are redacted in the snapshot copy.

Large external files are referenced and hashed when accessible; they are not copied into the snapshot.

## Starting a new chat or Work session

Attach:

```text
PON_Bikes_Automation_Continuity_LATEST.zip
```

and say:

> Continue PON Bikes Automation development using this Continuity Snapshot as the authoritative current state.

The installed physical code, database state and external source references contained in the snapshot take precedence over historical chat descriptions.
