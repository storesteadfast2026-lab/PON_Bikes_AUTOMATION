# PON.BIKE UI Design System
Version: 0918.1342

## Objective
Keep the receiving application visually and behaviourally consistent while the workflow grows.

## Reusable components introduced
The CSS classes prefixed with `app-` are generic workflow components and are not tied to Configure Import.

- `app-page-head` — page title, context and back navigation.
- `app-stepper` / `app-step` — guided multi-step processes.
- `app-panel` / `app-panel-head` — primary screen sections.
- `app-field` / `app-field-stack` — consistent form controls.
- `app-stat-strip` — compact operational summary metrics.
- `preview-status` — success/review state banner.
- `app-data-table` — operational preview/detail tables.
- `app-actionbar` — fixed/consistent final actions.
- `app-context-chip` — container/customer context indicator.
- `app-advanced-box` — hides uncommon or technical controls from the normal path.

## First adoption
`Configure import` now uses the common components for:
- 4-step import progress.
- Mapping settings.
- Workbook validation preview.
- Column mapping summary.
- Advanced mapping options.
- Continue/Cancel action bar.

`Validate preview` uses the same components so the operator does not visually jump to an older interface after building the preview.

## Recommended next adoption order
1. Product Check.
2. Translogic / PRODUCT_MOVES.
3. Customer report review.
4. Container detail cards that are still using legacy presentation.

## UI principles
- One obvious primary action per step.
- Summary first; detailed data only when requested or required by an exception.
- Technical/recovery functions belong under Advanced options.
- Always preserve container/customer context at the top of operational pages.
- Reuse the same status vocabulary: Ready, Review required, Pending, Complete.
- Scanning flows should remain keyboard/scanner friendly and avoid unnecessary confirmation clicks.

## Home navigation pattern adopted in 0918.1437
The Home screen now uses a persistent **Recent Containers rail** on the left.

Principles:
- A container is selected by clicking the whole container card, not a small secondary button.
- Search/filter stays close to the container list.
- The main workspace is reserved for the current primary task (creating a new container).
- Status, customer, date and Job Order are visible directly in the selection rail.
- This rail/list pattern should be reused wherever operators switch between operational objects frequently.
