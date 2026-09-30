# 01 — Overview

PON Bikes Automation is a Django application used to control PON/PBP bicycle receiving and the hand-off to Translogic. The application keeps each container operationally independent and provides a guided four-stage workspace.

## Primary operational identity

The standard display/input order is:

1. Job Order
2. Container ID
3. Customer
4. Container date

A non-blank Job Order is unique to one Container. Containers created automatically from a multi-container manifest may remain without a Job Order until the operator assigns one.

## Main stages

1. **Receive & Scan** — client manifest and confirmed first scan.
2. **Check Products** — expected vs received, Product Check, and NEW product data.
3. **Translogic** — PRODUCT_MOVES reconciliation and UPStockSerial.
4. **Complete** — customer report and completion checks.

The progress bar acts as a stage selector. Only the selected stage is shown immediately below it. The Recent Containers rail remains available in Container Detail so the operator can change container without returning to the dashboard.

## Output principle

The normal operator UI exposes **Download** actions, not Generate/Regenerate controls. Availability is derived from the existing workflow prerequisites.
