# CHANGELOG 0918.1255

## Product master switched to Excel .xls
- Primary shared product master changed from `products_pon_pbp_auto.xml` to `products_pon_pbp_auto.xls`.
- Default Windows source remains the configured product-master directory under `Freight-Calc-v1.6\uploaded_data`.
- Docker now reads `/data/pon_products/products_pon_pbp_auto.xls`.
- The dashboard and Django Admin now refer to a generic **Product master (Excel .xls)** rather than XML.
- Customer-specific product master paths remain supported.

## XLS reading
- Added direct operational support for legacy `.xls` files.
- The application converts `.xls` to a temporary `.xlsx` internally with the already-installed Gnumeric `ssconvert`, then reads it with the existing workbook parser.
- Required product-master columns are detected case-insensitively: `code`, `pon_sku`, `customer`, `code2`, `short_name`, `long_name`, `group1`, `group2`.
- Header variants such as `PON SKU`, `Short Name`, `Long Name`, `Group 1`, and `Group 2` are accepted.
- Legacy XML parsing remains available only for backwards compatibility with previously imported catalogues.

## Database/configuration
- Migration `0012_product_master_xls` updates known PON/PBP paths ending in `products_pon_pbp_auto.xml` to `.xls`.
- The upgrade script also updates the same filename in `.env` when present.
