# 05 — Receive & Scan

Step 1 controls the client manifest and the confirmed physical first scan.

## First Scan

The existing import workflow supports the established scanner/file structure, including location values used for verification. A unique Job Order must be assigned before the operational First Scan can begin.

## Confirmation

A source file is not operational merely because it was uploaded. The existing Configure Mapping / Preview / Confirm flow remains responsible for producing the confirmed Import Batch used by downstream stages.

## Dependencies

Product Check depends on a confirmed First Scan and an active Product Master. Later movement/output stages continue to use the confirmed data rather than unconfirmed uploads.

## Container-aware file selection

Manual source-file selectors show the expected Container ID and a suggested filename pattern such as `*ONEU1569467*.xlsx`. If the selected filename does not visibly contain the current Container ID, the UI warns the operator but does not block the upload. The existing workbook mapping/content validation remains authoritative, so a valid file is not rejected solely because of its filename.

For source files loaded into PON, the workflow shows **Uploaded** using the existing `SourceFile.uploaded_at` timestamp. These external files are not labelled as PON-generated files.
