# CHANGELOG 0928.1528

## Multi-container client manifests
- A single Client Manifest can now contain multiple Container IDs.
- Container values are normalised before comparison (`ONEU 156 946 7` -> `ONEU1569467`).
- The current container keeps only its own manifest rows.
- Other detected containers are created automatically as independent `PENDING` containers when they do not already exist.
- Existing containers are reused rather than duplicated.
- Auto-created containers keep Job Order blank, Received = 0, and no First Scan / PRODUCT_MOVES / UPStockSerial state.
- Each container receives its own confirmed client batch while retaining the shared source manifest filename and upload traceability.
- Completed existing containers are protected from silent manifest replacement.

## Job Order
- Job Order is now the primary field in create/edit and container presentation.
- Non-blank Job Orders must be unique across containers.
- UI/backend validation blocks reuse and identifies the container already using the Job Order.
- A conditional database unique index is created where legacy data permits it.
- Auto-created pending containers cannot start First Scan until a unique Job Order is assigned.
- Assigning a Job Order to a `PENDING` container moves it to `OPEN`.

## Automatic mapping
- Workbook analysis now proposes worksheet, header row, first data row and column mappings.
- Mapping uses header aliases plus real data patterns, historical customer profiles and Product Master matching when available.
- Added automatic Container-column detection, including spaced 4-letter/7-digit container values.
- Each mapping field exposes confidence; low-confidence fields are not forced.
- LongCode remains blank when no reliable candidate exists.
- Confirmed structures are saved automatically as reusable customer mapping profiles.
- Exact saved-profile matches bypass repetitive mapping and go directly to Validate Preview.

## Preview
- Multi-container preview lists each detected container independently with row and advised-unit totals.
- The current container is highlighted.
- New containers are explicitly labelled as `Will be created as PENDING`.
- Existing containers are explicitly labelled as existing.
- Confirmation is blocked if the current container is not present in a container-mapped manifest.

## UI hierarchy
Standard identity order is now:
1. Job Order
2. Container ID
3. Customer
4. Container date

Recent Containers now leads with Job Order and clearly shows `PENDING`, `Manifest uploaded` and advised units where available.

## Output rule preserved
- No operator-facing Generate / Regenerate actions were introduced.
- Current outputs remain Download-first.

## Database
Migration added:
- `0013_multi_container_job_order`
