# CHANGELOG 0918.1342

## Configure Import redesign
- Rebuilt Configure Import using a reusable operational UI system.
- Added a four-step import guide: Upload file → Configure mapping → Validate preview → Confirm import.
- Mapping controls are grouped and explained without changing their existing business behaviour.
- Added live Column Mapping Summary.
- Workbook inspection is presented as a Validation Preview with worksheet, row count, column count and fill information.
- Existing `location_stream`, saved customer profile and profile name controls remain available under Advanced mapping options.
- The existing Continue action still builds the real normalized preview; no decorative/non-functional action was added.

## Validate Preview consistency
- Restyled Batch Preview with the same page header, stepper, summary strip, data table and action bar.
- Existing Confirm Import behaviour is unchanged.

## Reusable design system
- Added generic `app-*` components to `static/css/app.css` so the same visual system can be progressively applied to Product Check, Translogic and reporting screens.
- Added `docs/UI_DESIGN_SYSTEM_0918.1342.md`.

## Data / database
- No model or database migration changes in this release.
- Product master remains `products_pon_pbp_auto.xls` from release 0918.1255.
