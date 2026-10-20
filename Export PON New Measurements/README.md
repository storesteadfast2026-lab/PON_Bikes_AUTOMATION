# PON - Truly New Measurements (Fix2)

Purpose: export ONLY the saved historical `NEW` products for a selected container, using the **exact single-sheet 14-column Excel layout** of `Export_TGBU4621260_New_Measurements.ps1`.

This is a standalone, **read-only export utility**. It does not update the PON app, import products into Translogic, change classifications, write to PostgreSQL, or require database migrations.

## What's changed since Fix1

- Enter **either** Container ID (`ONEU6047465`) **or** Translogic Job Order (`1773600`) at the prompt. Both resolve to the same PON container.
- Immediately generate and **open the Excel automatically** after entering the identifier. No `YES` prompt and no preview/second execution.
- Restore the **original worksheet format exactly**: one sheet named `New Products`; original columns A:N, header colours, `New` yellow rows, numeric formats, column widths, filters and frozen header. The extra `Container Info` worksheet introduced in Fix1 is removed.
- Preserve the original filename style: `<ContainerId>_New_Products_Measurements.xlsx`, saved beside the BAT and PS1. If it already exists, append a timestamp rather than overwriting it.
- Show the resolved Container ID and Job Order in the console and timestamped `OUTPUT/00_Export_Truly_New_*.txt` log. The Container ID remains in the original worksheet's A1 header.
- Keep `import_classification = NEW` as the only selection criterion. Exclude `PBP_TO_PON` and `EXISTING`. Do not infer `NEW` from today's catalogues.
- Retain the ONEU6047465 known acceptance guard (exactly 4 historically NEW SKUs); this is **not** a filter for any other container.
- Continue copying the UTF-8 **no BOM** Python source directly to the Docker web container, avoiding Windows PowerShell stdin encoding errors.

## Run on Windows

1. Extract this complete ZIP to a **separate folder** (or replace the three utility files in `Export PON New Measurements` after keeping a copy of Fix1). Do not place only the BAT without its companion PS1 and Python file.
2. Run `01_Run_Truly_New_Export.bat`.
3. At `Enter Container ID or Job Order`, type e.g. `1773600` or `ONEU6047465`, then press Enter.
4. Wait for the PON export to finish. Excel opens **automatically**, without asking for `YES`.
5. The workbook is saved **beside the script**. Detailed logs are under `OUTPUT/`.

**No change to Docker, the PON app or its database is needed.** The system must already have Docker Desktop running and the `web` service available.

## Expected ONEU6047465 output

`1773600` => `ONEU6047465`, four historically NEW SKUs:

- `0L0CABFX1C48`
- `0M0STBVX2C61`
- `0M0STBUI1C61`
- `0M0STBUI2C61`

The three PBP-to-PON codes (`0L0CABFX1C54`, `0L0CABFX1C56`, `0L0CABFX2C48`) must be absent.

## Fail closed

An unknown/ambiguous Job Order, missing classifications, unexpected ONEU classification, missing received batch, or incomplete saved measurements prevents export. No classification changes or fabricated measurements are made. No previous Excel is overwritten.

## QA scope and limitations

- **PASS (isolated)**: 12 scenarios, including full original-vs-Fix2 Excel XML equivalence for the sheet, styles and workbook; Job Order/Container ID lookup; historic NEW-only selection; failure modes and no-write source review.
- **NOT RUN**: native Windows PowerShell 5.1, live Docker Compose/Django, production database, automatic Excel GUI opening. The operator's next run validates those in the actual environment.
- See `QA_EVIDENCE.md` and `00_QA_test_results.log`.
