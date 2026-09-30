# CHANGELOG 0918.0930

## Simplified initial screen
- Removed the operational **Add customer** action.
- New containers now ask only for Container ID, Customer and Container date.
- `year` is derived automatically from Container date.
- Removed low-value server/configuration commentary from the operator dashboard.
- Recent containers are shown in one compact table.

## Customer-managed XML configuration
- Customers are maintained in Django Admin.
- Added per-customer product XML source path and application-readable path.
- Dashboard shows the selected customer's XML filename, source path, application path, availability and active imported copy.
- Product catalogue imports are now associated with a customer.
- PON/PBP retain backward-compatible defaults for the current shared XML.
- XML filenames are no longer hard-coded to `products_pon_pbp_auto.xml`; customer-specific `.xml` filenames are accepted while retaining the current XML schema requirements.

## Future workflow documentation
- Added scanner-first design requirements.
- Added customer-configurable/optional stage roadmap.
- Added workflow dependency and file lifecycle documentation.

## Database
- Added migration `0010_customer_product_catalog_configuration`.
