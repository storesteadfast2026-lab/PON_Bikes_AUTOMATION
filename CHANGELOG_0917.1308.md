# PON Bike Automation 0917.1308

Path-correction release based on 0917.1238.

- Corrected the Windows XML master path to `C:\Docker-Projects\Freight-Calc-v1.6\uploaded_data\products_pon_pbp_auto.xml`.
- Corrected Docker host bind source to `C:/Docker-Projects/Freight-Calc-v1.6/uploaded_data`.
- Upgrade script now updates both `PON_PRODUCT_HOST_DIR` and `PON_PRODUCT_CATALOG_PATH` in the copied `.env` while preserving database credentials and `COMPOSE_PROJECT_NAME`.
- XML parser, historical long/short-name dictionary, Group1/Group2 logic and database migration from 0917.1238 are unchanged.


Superseded by the next Group1-family/UI release.
