# CHANGELOG — 0929.1248

## Scope
Validation-only hotfix on top of 0929.1227.

## Changed
- Updated `receiving/tests.py` so the Container-ID upload hint is validated using stable text/content assertions instead of `assertContains(..., html=True)` on a mixed text + `<b>` fragment.
- The application HTML already rendered the required Container ID and filename pattern correctly; runtime application code is unchanged.

## Not changed
- No runtime application behaviour.
- No business logic.
- No models or migrations.
- No database schema/data.
- No file processing or integrations.
- No PRODUCT_MOVES or New Product Import changes.
- No Completed/Pending changes.
