# 09 — UPStockSerial

UPStockSerial is produced from the existing reconciliation process after valid PRODUCT_MOVES data is available.

The established output fields and file content are unchanged. The normal operator interaction remains **Download** when ready; no Generate/Regenerate control is added.

## Configured working and destination paths

The current operator-facing configuration is preserved:

```text
Source / working file:
C:\Docker-Projects\PON_Bike_Data\import\UPStockSerial.csv

Translogic destination:
T:\Import\UPStockSerial.csv
```

These values are read from the existing environment/settings rather than invented by the UI.

## Copy to Translogic

Release 0929.1322 completes the existing visible **Copy to Translogic** action only when the installer has verified real read/write Docker access to the configured Translogic destination folder.

Before any copy, PON displays:

- source filename and configured source path;
- destination filename and configured Translogic destination path;
- destination accessibility;
- whether `UPStockSerial.csv` already exists at the destination;
- existing destination modified date/time when available.

Copy is never automatic. The operator opens a confirmation page and explicitly confirms the copy/replacement. Immediately before copying, PON verifies that the destination file has not changed since the confirmation page was opened. It then copies through a temporary file, atomically replaces the final file where supported, and verifies SHA-256 after the copy.

A successful transfer is recorded in the persistent media audit with the container, user, timestamp, destination, whether a file was replaced, file size and verified SHA-256. The latest verified transfer is shown back in the workflow.

If the destination cannot be verified as read/write from Docker, **Copy to Translogic remains unavailable and Download/manual transfer remains unchanged**.
