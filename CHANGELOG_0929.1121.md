# CHANGELOG 0929.1121

## Scope
Validation hotfix only. Application runtime code is unchanged from 0929.1059.

## Changes
- Updated legacy Product Check workbook test expectations from mm headers/values to the intentional cm presentation.
- Updated the Product Master dashboard test to validate the configured source path from the Django context rather than JSON-escaped HTML.
- Updated the compact New Product editor test to match the current Short name / Long name labels.
- Updated the container-date edit test to include the now-required Job Order field.

## Runtime behaviour
No business logic, models, migrations, file processing, database logic, integrations or UI runtime behaviour changed.
