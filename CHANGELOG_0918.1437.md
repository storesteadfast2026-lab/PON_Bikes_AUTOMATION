# CHANGELOG 0918.1437

## Home / Container Processing
- Moved **Recent containers** from the bottom table to a persistent left-side rail.
- Each recent container is now a full clickable card; no separate Open button is required.
- Added live filtering by Container ID, customer, Job Order and status.
- The right side of Home now focuses only on creating a new container and displaying its configured product master.
- Removed the large How it works block from Home to reduce visual noise.
- Product-master maintenance remains available but is collapsed by default.

## Job Order
- Job Order remains stored on the Container model from migration 0011.
- Job Order is now required for newly created containers in the operational form.
- Existing containers with an empty Job Order remain readable/editable and are not deleted or migrated.

## Compatibility
- Preserves product-master `.xls` support introduced in 0918.1255.
- Preserves the import UI/design system introduced in 0918.1342.
- No new database migration is introduced in this release.
