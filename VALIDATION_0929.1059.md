# Validation — 0929.1059

## Source-level validation completed before packaging
- Python compile validation passed for `receiving`, `config` and `manage.py`.
- No migration files differ from baseline 0929.0719.
- `compose.yaml` still defaults to port 8001.
- Stage-selector JavaScript contains no `scrollIntoView` navigation.
- Step 2 uses existing export URLs; no export backend/workflow was duplicated.
- Product Check conversion is limited to `build_product_check_workbook`; ProductDefinition millimetre fields and New Product Import conversion logic were not changed.
- Regression tests were added for stage-selector markup, immediate Step 2 downloads, Product Check availability before dimensions, and printed cm values while stored mm remain unchanged.

## Runtime validation after installation
`04_VALIDATE.ps1` runs:
- Django `check`;
- migration state and `makemigrations --check --dry-run`;
- database/Job Order checks;
- the complete `receiving` Django test suite;
- host-folder/product-master checks;
- HTTP check on configured port (8001 by default).

Full Django runtime tests require the installed Docker environment and are therefore executed by `04_VALIDATE.ps1` after `02_APPLY_UPDATE.ps1`.
