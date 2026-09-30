# CHANGELOG 0918.0950

## Scope
Initial dashboard refresh only.

## Changes
- Redesigned the first screen into a cleaner two-panel landing page.
- Added **Job Order** to container creation and recent-container summary.
- Job Order is stored on the container and can be used later to identify the job in Translogic.
- Default customer selection now preselects the first configured customer.
- Product master XML remains visible with filename, source location, application path and active copy.
- XML maintenance actions were moved under **XML maintenance options** to reduce noise.
- Recent containers now show Customer, Job Order, Date and Status.
- Container detail header now also shows the Job Order when available.

## Database
- Added migration `0011_container_job_order`.
