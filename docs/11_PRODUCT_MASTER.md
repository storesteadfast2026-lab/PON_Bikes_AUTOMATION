# 11 — Product Master

The current PON/PBP Product Master source is an Excel `.xls` file. Default configured source path:

```text
C:\Docker-Projects\Freight-Calc-v1.6\uploaded_data\products_pon_pbp_auto.xls
```

Product Master configuration is customer-specific. Synchronisation/import activates a catalogue copy used for exact product matching and naming metadata.

The application keeps the existing short-name dictionary and Group1 mapping administration. Product Master maintenance is available from the dashboard; ordinary container operation consumes the active catalogue.

## Optional historical Translogic fields (0930.1602)

The XLS Product Master parser continues to require the existing eight identity/name/group columns and additionally preserves these optional columns in `ProductCatalogEntry.raw_data` when present: `cubic`, `weight`, `height`, `width`, and `length` (`lenght` is accepted as the historical spelling). These fields are used only for PBP → PON reuse and do not require a schema migration.
