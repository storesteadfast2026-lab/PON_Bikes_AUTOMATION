# VALIDATION 0918.1255

## Completed in build environment
- Python source compilation: PASS.
- Product-master header normalisation and row-normalisation helpers checked with representative values.
- Default application/configuration paths point to `products_pon_pbp_auto.xls`.
- Docker image already installs Gnumeric, which supplies `ssconvert` used to read legacy `.xls` files.

## Runtime validation required on the user's real file
The actual `products_pon_pbp_auto.xls` was not attached to this chat, so the final data-level check must be run against the real workbook after installation.

Expected columns:
- code
- pon_sku
- customer
- code2
- short_name
- long_name
- group1
- group2

After installation, use **Synchronize product master**. The dashboard should show the active copy and row count. If the real XLS uses different column names/layout, capture the exact error and adjust the mapping rather than guessing.
