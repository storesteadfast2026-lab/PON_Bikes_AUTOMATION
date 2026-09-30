# PON Bike Automation 0917.1238

- Replaced `PRODUCTS_PON_PBP.CSV` with `products_pon_pbp_auto.xml`.
- Added XML catalogue fields: `short_name`, `long_name`, `group1`, `group2`.
- Added migration `0005_productcatalogentry_xml_metadata`. Existing PostgreSQL data/volumes are preserved.
- Added tolerant handling for the current XML export's Windows NBSP bytes.
- Added persistent historical name dictionary (stored once per catalogue): exact long-name -> short-name reuse first.
- Added conservative abbreviation rules learned from repeated XML long/short-name pairs.
- Short names remain limited to 30 characters and are never blindly sliced at character 30.
- Product classification now exposes catalogue short name, Group1 and Group2 for verification.
- Docker source now expects `/data/pon_products/products_pon_pbp_auto.xml`.
- Default host source is `C:/Docker-Projects/Freight-Calc-v1.6/uploaded_data`.
- Existing rule for truly new products remains: Group2 becomes CHG02 when cubic > 0.400.
