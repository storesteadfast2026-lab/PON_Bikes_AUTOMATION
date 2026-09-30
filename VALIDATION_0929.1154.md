# Validation — 0929.1154

## Build-time checks performed before packaging
- Python source compilation: PASS.
- Product Check implementation still contains `Length (cm)`, `Width (cm)`, `Height (cm)`: PASS.
- Product Check cm conversion remains presentation-only; stored `*_mm` fields were not modified: PASS by source diff/regression-test inspection.
- Container Detail contains the shared Recent Containers sidebar and active-container marker: PASS by static inspection.
- Step 2 contains the existing New Product Import export URL only under the existing `new_product_import_download_ready` condition and exposes a non-action status otherwise: PASS by static inspection.
- No `Generate` / `Regenerate` action added: PASS.
- No `scrollIntoView` introduced: PASS.
- Port mapping remains 8001 in the release payload: PASS.
- Migration file set is unchanged from 0929.1121: PASS.

## Runtime validation
The complete Django/runtime validation must be performed after installation with `04_VALIDATE.ps1`. It runs:
- Django system check;
- applied migration check;
- `makemigrations receiving --check --dry-run`;
- PostgreSQL access and Job Order uniqueness check;
- complete `python manage.py test receiving` suite, including the new sidebar and Step 2 regression coverage;
- Product Master / working-folder checks;
- HTTP check on the configured port (default 8001).

The release is operationally validated only when `04_VALIDATE.ps1` reports `Failures: 0`.
