# Changelog — 0929.1154

## Scope
Low-risk presentation/navigation update on stable baseline 0929.1121. No business-rule, database, file-processing or integration changes.

## Application changes
- Step 2 keeps `Download Product Check + barcodes (.xlsx)` unchanged.
- Step 2 now always exposes the **New Product Import** state directly: the existing Download action is shown when current backend rules say it is ready; otherwise an informational Pending / Not required state is shown without an invalid action.
- Container Detail now includes the existing Recent Containers rail as a sticky left sidebar. The active container is highlighted and another container can be opened directly from the rail.
- Product Check continues to print `Length (cm)`, `Width (cm)`, `Height (cm)` while confirmed ProductDefinition dimensions remain stored internally in mm.

## Shared presentation refactor
- Recent Containers sidebar data is provided by one shared view helper and one shared sidebar template used by Dashboard and Container Detail.
- No second container navigation workflow was created.

## Documentation
- Added the living `docs/` set covering the end-to-end PON workflow, business rules, configuration, installation, validation and release history.

## Database
- No model changes.
- No migration added.
