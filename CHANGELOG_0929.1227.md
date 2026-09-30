# CHANGELOG — 0929.1227

Incremental low-risk presentation/file-metadata update on stable baseline 0929.1154.

## Application changes

- File provenance is displayed separately as **Generated** and **Uploaded** using existing timestamps:
  - `SourceFile.uploaded_at` for Client Manifest / First Scan.
  - `ProductMovesImport.imported_at` for PRODUCT_MOVES loaded into PON.
  - `GeneratedExport.generated_at` for Product Check, New Product Import, UPStockSerial and Customer Report.
- Manual Client Manifest / First Scan file selectors now show the expected Container ID and suggested filename pattern. A filename that does not visibly contain the Container ID produces a warning only; existing workbook/content validation remains authoritative.
- Customer Report download filename is now `<CONTAINER> Advised.xls`. Only the HTTP download filename changes; workbook content and generation remain unchanged.
- UPStockSerial displays configured Source file path and Translogic destination path directly.
- **Copy to Translogic** is visible but disabled. No direct-copy backend is added in this release because none existed safely in the baseline.
- Existing Download action remains available when UPStockSerial is ready.

## Intentionally unchanged

- Database models and migrations.
- Completed/Pending logic.
- PRODUCT_MOVES parsing/import/reconciliation logic.
- New Product Import generation/content.
- Customer Report workbook content/generation.
- Product Check content/unit logic.
- Docker/port configuration (`8001`).

## Documentation

Updated living documentation in `docs/` for source upload guidance, provenance timestamps, Translogic paths/transfer state, Customer Report filename, and release history.
