# 15 — Configuration and Paths

Current operator-facing paths are controlled by the existing environment/settings. Important configured defaults in the current baseline are:

```text
Product Master:
C:\Docker-Projects\Freight-Calc-v1.6\uploaded_data\products_pon_pbp_auto.xls

PRODUCT_MOVES source:
T:\STEADFAST\EXCEL FILES\PRODUCT_MOVES.CSV

PRODUCT_MOVES working bridge:
C:\Docker-Projects\PON_Bike_Data\translogic\PRODUCT_MOVES.CSV

UPStockSerial working:
C:\Docker-Projects\PON_Bike_Data\import\UPStockSerial.csv

UPStockSerial final / Translogic destination:
T:\Import\UPStockSerial.csv

Customer report working:
C:\Docker-Projects\PON_Bike_Data\reports
```

The active application folder is:

```text
C:\Docker-Projects\PON_Bikes_Automation
```

The Docker web service is exposed on Windows port **8001**. Real `.env` values are preserved by incremental updates.

## Direct Translogic access introduced in 0929.1322

No mapped-drive or UNC route is assumed to work simply because Windows displays it. `01_PREPARE_INSTALL.ps1` performs the real-host preflight before enabling either direct feature.

### Translogic import destination

The installer derives the candidate folder from the **currently configured UPStockSerial Translogic destination**. It checks the visible Windows folder and, where possible, the UNC path behind the mapped drive. Direct import-folder mode is enabled only after Docker successfully creates, reads and deletes a temporary probe file in that real folder.

The installer then inspects that same real folder for one unique complete numbered-file set 1–5. The detected pattern, extension, oldest filename and timestamps are written to:

```text
C:\Docker-Projects\PON_Bikes_Automation\.update_state\translogic_preflight.json
```

If no unique real set is found, PON does not invent a pattern and New Product Import replacement stays disabled.

### PRODUCT_MOVES direct source

The installer starts from the currently configured operator-facing source:

```text
T:\STEADFAST\EXCEL FILES\PRODUCT_MOVES.CSV
```

Direct mode is enabled only if the file exists and Docker can bind/read its parent folder. Otherwise the existing local bridge and manual upload remain active.

### Internal feature flags

The installer manages these values in the preserved `.env` only after preflight:

```text
PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED
PON_TRANSLOGIC_IMPORT_HOST_DIR
PON_PRODUCT_MOVES_DIRECT_ENABLED
PON_PRODUCT_MOVES_DIRECT_HOST_DIR
```

They must not be set to an unverified route merely to make a button appear.
