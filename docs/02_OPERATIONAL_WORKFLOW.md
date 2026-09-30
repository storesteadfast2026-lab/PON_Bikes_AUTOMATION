# 02 — Operational Workflow

## End-to-end flow

```text
Job Order / Container
        ↓
Client Manifest
        ↓
Receive & Scan / First Scan
        ↓
Product Check
        ↓
NEW Product Data (when required)
        ↓
PRODUCT_MOVES from Translogic
        ↓
Reconciliation
        ↓
UPStockSerial
        ↓
Review / explicit Copy to Translogic when verified
        ↓
Customer Report
        ↓
Complete
```

## Workspace behaviour

Container Detail is the main operational workspace. The stage circles are selectors rather than scroll links. Selecting a stage replaces the visible stage content in the area immediately below the progress bar.

The status of each stage continues to come from the existing workflow calculations; selecting a stage does not change Completed/Pending state.

## Navigation

A sticky Recent Containers rail is available on the dashboard and Container Detail. The active container is highlighted and marked as Current. Selecting another container opens its existing Container Detail record.


## Translogic file exchange

Release 0929.1322 keeps Download as an operator option and adds guarded direct transfer only when the real destination has passed host/Docker preflight. UPStockSerial and New Product Import are never copied automatically. A replacement requires an explicit confirmation screen and post-copy verification. PRODUCT_MOVES direct Refresh is enabled only when the configured real source is readable from Docker; otherwise the previous bridge/manual path stays active.
