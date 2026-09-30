# PON Bike Automation — 0918.0713

## Part 2 added: PRODUCT_MOVES → UPStockSerial

This version extends the existing 0917.1355 application without changing the Stage 1 XML, name dictionary, Group1, dimensions or New Product Import logic.

### New workflow

- Adds **Part 2 · Movements & labels** to each container.
- Reads `PRODUCT_MOVES.CSV` from the configured operational path. Docker maps `T:/STEADFAST/EXCEL FILES` read-only to `/data/pon_translogic`.
- Supports manual `PRODUCT_MOVES.CSV` upload as a fallback when the mapped T: drive is unavailable.
- Snapshots each imported PRODUCT_MOVES file, SHA-256 and row count for audit.
- Requires the verified columns `product` and `stock_in_mov`.
- Rejects duplicate, blank, non-numeric or over-length Movement Numbers.
- Reconciles movements by product code against the confirmed first scan.
- Requires one physical bike per first-scan row and a valid `T9999` location.
- Uses the original first-scan worksheet row as `serial_no`.
- Preserves `PRODUCT_MOVES.CSV` order in the output while assigning each movement to the next physical first-scan unit of the same product.
- Blocks output when per-product quantities differ.
- Generates the verified `Movement,serial_no,Loc` `UPStockSerial.csv` format.
- Preserves the legacy 500-data-row (`A2:C501`) file shape.
- Writes `T:/Import/UPStockSerial.csv` when the Docker mount is available and always keeps a versioned application audit copy.
- Adds Django Administration pages for PRODUCT_MOVES imports and movement rows.

### Database

Migration `0008_stage2_product_moves.py` adds:

- `ProductMovesImport`
- `ProductMovement`
- `UPSTOCK_SERIAL` as a generated-export kind

### Deployment

Use `Upgrade-PON-Stage2-0918.0713.ps1`. It preserves the existing Compose project/database and adds the required T: drive mount settings to `.env`.
