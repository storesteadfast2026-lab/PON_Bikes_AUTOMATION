# VALIDATION — 0929.1227

## Static/package validation completed before delivery

- Python syntax compile: PASS for `receiving/views.py` and `receiving/tests.py`.
- No new migration file: PASS.
- `receiving/models.py` unchanged from stable baseline 0929.1154: PASS.
- `receiving/services.py` unchanged from stable baseline 0929.1154: PASS.
- `compose.yaml` unchanged; Windows port remains `8001`: PASS.
- PRODUCT_MOVES processing functions unchanged: PASS.
- New Product Import export function unchanged: PASS.
- Completed/Pending computation unchanged: PASS.
- Customer Report workbook builder unchanged: PASS.
- Customer Report download header changed to `<CONTAINER> Advised.xls`: PASS by code/test coverage.
- Customer Report response-body preservation is covered by regression test.
- Container-aware file selector guidance/warning present without filename blocking: PASS by code/test coverage.
- Generated / Uploaded labels use existing model timestamps: PASS by code inspection/test coverage.
- UPStockSerial configured Source / Destination paths are visible: PASS by template inspection/test coverage.
- `Copy to Translogic` is visible and disabled; no copy URL/backend introduced: PASS.
- Package SHA-256 manifest is regenerated after packaging.

## Runtime validation

The delivery environment does not run the project's Docker/Django runtime. `04_VALIDATE.ps1` performs runtime validation on the installed application and must confirm:

- Django system check.
- all receiving migrations applied.
- `makemigrations --check --dry-run` reports no model drift.
- PostgreSQL connectivity.
- no duplicate non-blank Job Orders.
- complete `receiving` test suite (expected 48 tests after this release).
- configured working folders and Product Master.
- HTTP application response on port 8001.

The release is fully accepted only when `04_VALIDATE.ps1` reports `Failures: 0`.
