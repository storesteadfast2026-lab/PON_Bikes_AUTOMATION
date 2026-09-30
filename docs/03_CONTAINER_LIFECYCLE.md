# 03 — Container Lifecycle

## Creation

A container can be created manually or created automatically when a confirmed client manifest contains additional Container IDs.

Manual creation requires the operational identity fields configured by the current form. Auto-created manifest containers start as **PENDING**, keep their manifest/advised data, and may have no Job Order initially.

## Operational independence

Each Container has its own source files, confirmed batches, scans, product state, movement reconciliation and outputs. A multi-container source workbook does not merge operational data between containers.

## Job Order

One non-blank Job Order can belong to only one Container. A PENDING container without a Job Order cannot start the operational First Scan.

## Completion

The existing workflow determines when a container can be completed. Reopening a completed container re-enables live dependency/staleness checks.
