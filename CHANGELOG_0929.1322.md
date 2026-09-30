# CHANGELOG — 0929.1322

## Scope
Safe simplification of file exchange with Translogic. Existing file formats, parsing, reconciliation, Completed/Pending logic and database models are preserved.

## Changes

- Completed the existing **Copy to Translogic** workflow for UPStockSerial when the real configured Translogic destination has passed Windows + Docker read/write preflight.
- Added an explicit confirmation screen before copy/replacement. Destination changes between review and confirmation cancel the transfer and require another review.
- Added post-copy SHA-256 verification and a persistent transfer audit in the existing Docker media volume.
- Added discovery of the **real** numbered New Product Import set 1–5. No filename is hard-coded. Exactly one complete prefix/extension pattern must exist.
- The oldest real numbered file is proposed from its actual modification timestamp. Replacement occurs only after explicit operator confirmation.
- If the PON-generated New Product Import extension differs from the real Translogic numbered-file extension, direct replacement is blocked; no conversion is attempted.
- Added optional direct PRODUCT_MOVES Refresh. It is enabled only when the configured source exists and Docker can read the real folder. Otherwise the existing local bridge/manual-upload flow remains active.
- Extended `01_PREPARE_INSTALL.ps1` to inspect mapped-drive/UNC candidates and enable direct integration only after real access checks.
- Extended `04_VALIDATE.ps1` to report the real numbered pattern/oldest file found during preflight and runtime source visibility.
- Updated living Markdown documentation under `docs/`.

## Files changed

Application/configuration:
- `.env.example`
- `compose.yaml`
- `config/settings.py`
- `receiving/views.py`
- `receiving/urls.py`
- `receiving/translogic_transfer.py` (new)
- `receiving/templates/receiving/container_detail.html`
- `receiving/templates/receiving/stage2.html`
- `receiving/templates/receiving/translogic_transfer_confirm.html` (new)
- `static/css/app.css`
- `receiving/tests.py`
- `sample_translogic_import_direct/.gitkeep` (new safe disabled fallback mount)
- `sample_translogic_moves_direct/.gitkeep` (new safe disabled fallback mount)

Installer/validation:
- `_support/PON.Update.Common.ps1`
- `01_PREPARE_INSTALL.ps1`
- `04_VALIDATE.ps1`

Documentation:
- `docs/02_OPERATIONAL_WORKFLOW.md`
- `docs/07_NEW_PRODUCT_PROCESS.md`
- `docs/08_PRODUCT_MOVES_AND_TRANSLOGIC.md`
- `docs/09_UPSTOCKSERIAL.md`
- `docs/15_CONFIGURATION_AND_PATHS.md`
- `docs/17_TESTING_AND_VALIDATION.md`
- `docs/README.md`
- `docs/RELEASE_HISTORY.md`

## Database

No model change and no new migration.

## Important runtime rule

The build environment cannot access the user's Windows mapped drive `T:`. Therefore this release does **not** claim a production numbered-file pattern in advance. `01_PREPARE_INSTALL.ps1` inspects the actual configured host folder and prints/records the real pattern and oldest file if they can be safely identified. If real access cannot be verified, direct copy stays disabled and the previous workflow remains available.
