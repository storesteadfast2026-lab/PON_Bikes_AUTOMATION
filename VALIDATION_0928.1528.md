# VALIDATION 0928.1528

## Build-time validation completed
- Python compile validation passed for the full `receiving` and `config` packages.
- The real uploaded workbook `TGBU4621260 ONEU1569467 ONEU2096348 LIST.xlsx` was inspected with the spreadsheet tooling.
- Verified real workbook structure:
  - worksheet: `Purchase Lines`
  - header row: 1
  - data rows: 309
  - Bike/Product code: column B (`No.`)
  - Description: column C (`Description`)
  - Quantity: column E (`Quantity`)
  - Container: column F (`Reserved Qty. (Base)`)
- Verified real container split:
  - `ONEU1569467`: 41 rows / 102 advised units
  - `TGBU4621260`: 148 rows / 249 advised units
  - `ONEU2096348`: 120 rows / 120 advised units
  - total: 309 rows / 471 advised units
- Output templates were scanned and no new Generate / Regenerate operator action was introduced.

## Runtime validation included in 04_VALIDATE.ps1
After installation, 04 validates:
- Docker and PostgreSQL availability
- Django system check
- receiving migrations, including 0013
- database connectivity
- no duplicate non-blank Job Orders
- targeted Django acceptance tests for:
  - multi-container mapping
  - pending container creation
  - existing-container reuse
  - saved mapping profiles
  - low-confidence mapping behaviour
  - Job Order uniqueness and field order
- product master / working folders
- HTTP application response on port 8001

## Environment limitation during package build
The build environment does not have network access to install the Django runtime dependencies, so the targeted Django test suite could not be executed here. The package therefore makes those tests part of `04_VALIDATE.ps1` inside the application's normal Docker runtime. Static Python compilation and real-workbook data validation were completed successfully.
