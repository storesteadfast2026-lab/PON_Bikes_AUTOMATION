# VALIDATION — 0929.1322

## Build-time validation completed

- Python compilation: PASS.
- Pure Python numbered-file discovery: PASS using arbitrary names; oldest file selected by real mtime rather than file number.
- Ambiguous multiple complete 1–5 patterns: correctly blocked.
- Verified-copy helper: PASS; source and destination SHA-256 match after replacement.
- `receiving/models.py`: unchanged from stable baseline 0929.1248.
- Receiving migrations: unchanged from stable baseline 0929.1248.
- `receiving/services.py`: unchanged from stable baseline 0929.1248, preserving New Product Import / UPStockSerial / Customer Report generation content.
- No Generate/Regenerate operator workflow introduced.
- Port configuration remains 8001.

## Runtime validation performed by 04_VALIDATE.ps1

The installed Docker environment must run `04_VALIDATE.ps1`. It checks:

- Django system check;
- all receiving migrations applied;
- `makemigrations --check --dry-run`;
- PostgreSQL access and Job Order uniqueness;
- complete `receiving` test suite (53 tests in this source tree);
- required host folders and Product Master;
- Windows Translogic preflight report;
- actual real numbered 1–5 pattern/oldest file when available;
- direct import-folder accessibility if enabled;
- Docker runtime discovery of the same numbered set;
- PRODUCT_MOVES selected source visibility and safe fallback;
- HTTP response on port 8001.

## Safety / acceptance coverage added

Regression tests cover:

- real filename discovery without assuming a product-import filename;
- exact complete set 1–5 requirement;
- oldest-file selection from actual timestamps;
- GET confirmation page performs no copy;
- POST requires explicit confirmation;
- only the selected oldest numbered file is replaced;
- format/extension mismatch blocks replacement without conversion;
- UPStockSerial copy is explicit and verified;
- SHA-256 post-copy verification.

## Host-specific items not claimable at build time

The build environment has no access to the user's Windows `T:` drive. Therefore the following are deliberately resolved on the user's machine by `01_PREPARE_INSTALL.ps1`, not assumed here:

- whether `T:\Import` (or its current configured equivalent/UNC path) is actually read/write accessible to Docker;
- the real New Product Import numbered filename/extension pattern;
- which real numbered file is currently oldest;
- whether `T:\STEADFAST\EXCEL FILES\PRODUCT_MOVES.CSV` (or its current configured equivalent/UNC path) is directly readable by Docker.

If any direct-access check fails, the previous Download/local-bridge/manual-upload workflow remains enabled and direct actions are not falsely activated.
