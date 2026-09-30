# Validation — PON Bike Automation 0918.0730

## Customer report logic

Static and service-level validation covers:

- client order preservation;
- advised and received aggregation by Item Code;
- `Var = Received - Advised`;
- numeric zero when quantities match;
- XML LongName preference for existing products;
- saved ProductDefinition LongName for new products;
- per-container historical New/Existing snapshot;
- `New` comment driven by that snapshot after Product Check, with current XML as fallback before a snapshot exists;
- received-only products appended after advised products;
- requested six-column Excel layout and total row.

A sample output for the bundled real test container `TCNU4108637` is included under `sample_output/`. Its confirmed source data reconcile to 13 product codes, Advised 78, Received 78 and total Var 0.

Part 2 from 0918.0713 remains unchanged: the supplied PRODUCT_MOVES and UPStockSerial reference still define the tested movement/serial/location workflow.

## Spreadsheet visual verification

The bundled sample customer workbook was generated and inspected with the real `TCNU4108637` sample inputs:

- 13 product codes;
- Advised total: 78;
- Received total: 78;
- total Var: 0;
- yellow `Item Code / Item Name / Advised / Received / Var / Comment` header;
- container identifier above the table;
- bordered rows and final Total row;
- no spreadsheet formula errors found in the sample output.

## Static application validation

- Python `compileall`: PASS.
- Client-report row logic smoke test: PASS (negative variance, zero variance and historical `New` flag).
- Existing Part 2 service block `PRODUCT_MOVES -> reconciliation -> UPStockSerial` is unchanged apart from whitespace.
- Django runtime check could not be executed in this sandbox because Django is not installed. `Upgrade-PON-ClientReport-0918.0730.ps1` runs `migrate` and `manage.py check` inside the user's Docker environment after rebuild.
