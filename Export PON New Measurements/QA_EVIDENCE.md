# PON Export Truly New Measurements - Fix2 QA

## Scope

Correct two user-reported regressions in Fix1, without changing PON business rules:
1. Entering Job Order `1773600` incorrectly failed the Container ID regex.
2. The workbook format differed from the original TGBU script (extra worksheet), and running it required a `YES` confirmation.

## Root causes

- PowerShell validated user input only as `^[A-Z]{4}[0-9]{7}$`, without resolving `Container.job_order`.
- The Python exporter created an additional `Container Info` worksheet.
- PowerShell ran PREVIEW and then prompted for `YES` before EXPORT.

## Verified code-level corrections

- ORM lookup uses `Container.identifier__iexact` for container-shaped input, or `Container.job_order__iexact` for Job Orders; unknown or ambiguous matches are rejected.
- **Single** export pass, no PREVIEW stage or operator confirmation.
- `Start-Process -FilePath $OutputFile` opens the resulting workbook automatically on Windows.
- The Python export preserves the original New Products 14-column workbook: actual regression test runs the original TGBU Python exporter and Fix2 on the same mocked rows, then compares the generated `xl/worksheets/sheet1.xml`, `xl/styles.xml`, and `xl/workbook.xml` **byte-for-byte**. All three matched.
- Historic `NEW` classification is the sole inclusion rule; explicit `PBP_TO_PON` exclusions verified.
- No database writes are present in the new exporter.
- Python/PowerShell file bytes are UTF-8 without a BOM.

## Isolated test results

`12 passed / 0 failed`. See `00_QA_test_results.log` and `00_QA_test_results.json`.

The ONEU6047465 acceptance case is covered with four NEW SKU and three PBP_TO_PON SKU (mock records). Both search inputs produce identical sheet XML. A second container confirms the selection generalises beyond the four named SKU.

## Operational status

- Windows PowerShell 5.1 and Docker Compose: **NOT RUN** in this environment.
- Live PON PostgreSQL DB, real Container ID/Job Order mapping, Excel GUI auto-open: **NOT RUN**.
- Do **not** claim live operational PASS solely from the isolated QA. Operator should run `01_Run_Truly_New_Export.bat` and send the `OUTPUT/00_Export...txt` log if it fails.
- Package does not replace app source or require a rollback of PON. Previous export utility remains available as a separate archive.
