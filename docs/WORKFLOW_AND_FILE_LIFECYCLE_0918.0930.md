# PON.BIKE — Workflow and file lifecycle

Version: **0918.0930**

## UI principle

The main workflow is guided but reversible. Operators can return to an earlier stage to review or replace data. When an upstream input changes, only dependent outputs should become stale and require regeneration.

## Dependency model

### Client manifest
Affects:
- Advised quantities.
- Variance.
- Customer report.

### First scan
Affects:
- Received quantities.
- Product classification.
- `serial_no` and location mapping.
- PRODUCT_MOVES reconciliation.
- UPStockSerial.csv.
- Customer report.

### Product master XML
Affects:
- Existing/new classification.
- Names and product metadata.
- New-product preparation.
- Customer report.

### PRODUCT_MOVES.csv
Affects:
- Movement reconciliation.
- UPStockSerial.csv.

## File locations

Operational files should always show their paths in the UI.

The application distinguishes:

- **Source location** — where another system or user creates the input.
- **Working location** — local path used reliably by Docker/application processing.
- **Final location** — destination used by Translogic or the business after review.

The current T: network drive cannot be mounted reliably by Docker Desktop. Therefore the application currently uses local working folders and keeps the final Translogic path visible for the later approve/move step.

## Review before final move

Generated files should follow:

`Generated → Review → Approved → Move to final location`

The application must not imply that a file has reached the final Translogic/customer location until that move has actually occurred.
