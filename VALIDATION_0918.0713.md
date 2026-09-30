# Validation — PON Bike Automation 0918.0713

## Real operational files supplied

The supplied `PRODUCT_MOVES.CSV` was parsed as:

- Header: `product,stock_in_mov`
- 85 non-blank movement rows
- 15 distinct product codes
- Movement Numbers stored by Translogic with leading spaces to a 10-character field

The supplied `UPStockSerial.csv` reference was parsed as:

- Header: `Movement,serial_no,Loc`
- 500 data rows in the file
- 85 populated rows
- 415 blank template rows
- The populated Movement Numbers are exactly the same set and order as PRODUCT_MOVES.CSV

## Mapping validation

A controlled validation reconstructed the corresponding physical first-scan units from the supplied reference and then ran the new Part 2 algorithm:

- PRODUCT_MOVES rows: 85
- Received physical units: 85
- Matched units: 85
- Per-product count mismatches: 0
- Location/serial issues: 0
- Reconciliation status: READY

The generated `UPStockSerial.csv` was compared byte-for-byte with the supplied operational reference:

**PASS — exact byte equality (3,467 bytes).**

This verifies:

- Movement is right-aligned to the existing 10-character field.
- `serial_no` is the original first-scan worksheet row.
- `Loc` is the location inherited by that physical bike from the first scan.
- Movement-file order is preserved.
- The output is CRLF CSV and padded to 500 data rows.

## Additional static validation

- Python `compileall`: PASS for the entire project.
- New service tests added for successful reconciliation, count mismatch blocking and duplicate Movement rejection.
- ZIP integrity will be checked after packaging.

## Runtime limitation in this environment

Django/Docker runtime tests could not be executed in this sandbox because Django is not installed and external package installation is unavailable (no network access). The upgrade script runs `manage.py migrate` and `manage.py check` in the user's Docker environment after rebuild.
