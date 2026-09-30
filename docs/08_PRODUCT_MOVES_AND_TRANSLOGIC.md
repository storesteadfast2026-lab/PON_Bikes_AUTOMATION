# 08 — PRODUCT_MOVES and Translogic

Translogic remains the source of Movement Numbers. PON Bikes Automation does not invent movements.

The existing PRODUCT_MOVES parsing, snapshot and reconciliation logic is unchanged. Product quantities are reconciled against the confirmed First Scan. A mismatch prevents the workflow from treating UPStockSerial as ready.

## Source selection

The operator-facing configured source remains:

```text
T:\STEADFAST\EXCEL FILES\PRODUCT_MOVES.CSV
```

Historically Docker reads the local bridge copy under the configured `PON_MOVES_HOST_DIR`. Release 0929.1322 adds a **preflight only** for direct reading:

- `01_PREPARE_INSTALL.ps1` checks whether the configured Windows source file exists;
- it resolves the mapped drive to UNC when Windows exposes that mapping;
- it asks Docker to bind-mount the candidate folder read-only;
- direct mode is enabled only when the actual `PRODUCT_MOVES.CSV` exists and Docker can read the folder.

If any check fails, PON does not change the operational source. Refresh continues to use the existing local working-copy/manual-upload fallback.

At runtime Refresh prefers the verified direct Translogic file only while it is actually readable. If it disappears, the existing configured fallback is used automatically. The CSV parser, SHA-256 audit, quantity reconciliation and movement assignment logic are unchanged.

## File provenance

PRODUCT_MOVES remains an external Translogic file. PON shows its configured source/working paths and records **Uploaded** as the time the active PRODUCT_MOVES snapshot was loaded into PON. PON does not present this timestamp as a PON **Generated** time.
