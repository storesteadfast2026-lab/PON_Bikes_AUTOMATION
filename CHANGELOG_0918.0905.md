# PON Bike Automation 0918.0905 — Guided container workflow

This release reorganises the operator experience without changing the verified receiving, product, movement reconciliation or UPStockSerial business rules.

## Main workflow

- Replaces the old container landing page with one guided workflow screen.
- Uses four clickable stages: **Receive & Scan → Check Products → Translogic → Complete**.
- Keeps earlier stages reviewable instead of locking the operator into a forward-only wizard.
- Keeps detailed Expected vs Received, Product Check and Translogic pages as secondary **View details** screens.
- Shows a permanent summary for Advised, Received, Variance and New products.
- Shows a permanent checklist and a single **Next action** explanation.
- Reduces normal-path buttons; manual/fallback actions are moved into Advanced sections.

## Consistency and dependency status

- A newer confirmed First Scan or newer PRODUCT_MOVES snapshot marks an existing UPStockSerial as **outdated / regenerate**.
- A newer client manifest, first scan, active product catalogue or saved new-product definition marks the customer report **outdated / regenerate**.
- Completed containers are historical snapshots: later global catalogue/dictionary changes do not silently invalidate them.
- A completed container can be reopened before corrections; modifying endpoints reject changes while it remains Complete.
- Mark Complete is allowed only when the product workflow is ready and both UPStockSerial and customer report are current.

## File locations

The workflow now shows operator-facing paths rather than Docker-only `/data/...` paths:

- PRODUCT_MOVES source: `T:\STEADFAST\EXCEL FILES\PRODUCT_MOVES.CSV`
- PRODUCT_MOVES working copy: `C:\Docker-Projects\PON_Bike_Data\translogic\PRODUCT_MOVES.CSV`
- UPStockSerial working copy: `C:\Docker-Projects\PON_Bike_Data\import\UPStockSerial.csv`
- UPStockSerial final Translogic location: `T:\Import\UPStockSerial.csv`
- Client report working folder: `C:\Docker-Projects\PON_Bike_Data\reports`

The final customer archive/send destination remains intentionally unconfigured until the business location is agreed.

## Customer report working copy

- Adds a `/data/pon_reports` Docker mount.
- Generated customer receiving workbooks are still stored in persistent application audit storage and are additionally written to the visible Windows working reports folder.

## Compatibility

- No database migration in this release.
- Existing PostgreSQL data and media/audit copies remain unchanged.
- Existing detailed screens and URLs remain available.
- UPStockSerial generation logic remains the verified 0918.0815 logic: ascending Movement order and the legacy 500-row shape.
