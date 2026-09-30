# PON.BIKE — Client configuration and scanner roadmap

Version: **0918.0930**  
Date: **18/09/2026**

## Purpose

This document records design decisions that must guide future releases. They are intentionally captured now so the operator workflow remains simple while the application expands to more customers and scanner-based receiving.

## Customer management

- Customers are created and maintained in **Django Admin**.
- The normal receiving screen must not contain an **Add customer** workflow.
- The operator selects an existing customer when creating a container.
- Customer-specific settings must be stored against that customer rather than hard-coded to PON/PBP.

## Product master XML per customer

Each customer can have its own product-master XML and location.

The Customer record now includes:

- **Product catalogue source path** — the Windows/network location shown to the operator.
- **Product catalogue application path** — the path the Django application can actually read (for example a Docker-mounted `/data/...` path).

The dashboard must show the selected customer's:

- XML file name.
- Source location.
- Application-readable location.
- Availability.
- Active imported copy, row count and load time when available.

Current PON/PBP reference source:

`C:\Docker-Projects\Freight-Calc-v1.6\uploaded_data\products_pon_pbp_auto.xls`

Current Docker application path:

`/data/pon_products/products_pon_pbp_auto.xls`

These are defaults for the current operation only. A future customer may point to another XML file and another configured path.

## Scanner-first future workflow

Future releases will use barcode scanners to reduce manual steps. Scanner support is a first-class design constraint even before scanner-specific features are implemented.

Requirements:

- Support scanners that behave as keyboard input (keyboard wedge).
- Keep the scan field focused automatically between scans.
- Accept repeated scans without mouse interaction.
- Provide immediate visual/audio success or error feedback.
- Keep manual entry and file upload as fallback paths.
- Avoid extra confirmation clicks where validation can be automatic.
- Support scanning identifiers such as Container, Location and Bike/Product codes.
- Preserve scan sequence because it is used operationally as `serial_no` in the current Translogic update process.

## Optional / skippable workflow stages

The guided workflow must not assume every customer requires every stage.

Long-term design:

- Each customer can define which stages are required.
- A stage can be `required`, `optional`, `automatic` or `not applicable`.
- The workflow should automatically skip stages that are not required for that customer.
- The operator should see only the stages relevant to the active customer/container.
- Skipping a stage must never bypass required validation for downstream outputs.

Examples that may become customer-configurable later:

- Client manifest required or not.
- First scan imported from Excel vs captured directly by scanner.
- New-product check required or not.
- PRODUCT_MOVES reconciliation required or not.
- Customer report required or not.

## Guiding principle

The operator should answer three questions from one screen:

1. **Where am I?**
2. **Is everything OK?**
3. **What do I do next?**

Detailed data should remain available on demand, but the default interface should show a concise operational summary.
