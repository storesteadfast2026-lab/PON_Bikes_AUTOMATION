# PON Bike Automation — 0918.0730

## Final customer receiving Excel

Built on 0918.0713. This version keeps the complete PRODUCT_MOVES → UPStockSerial workflow and adds the final Excel sent to the customer.

- Adds generated-export kind `CLIENT_REPORT`.
- Adds **Generate client Excel (.xlsx)** to Expected vs received and Part 2.
- Requires confirmed Client manifest + First scan, but does not require PRODUCT_MOVES.
- Output columns: Item Code, Item Name, Advised, Received, Var, Comment.
- Var = Received − Advised and remains numeric 0 on a match.
- Comment is blank except `New` for products historically classified as new in this container. The Product Check classification is persisted so later XML refreshes do not erase the flag.
- Adds `ContainerProductStatus` for that per-container historical classification.
- Long Item Name priority: XML LongName → saved ProductDefinition LongName → client/received description.
- Preserves client-manifest order and appends received-only items.
- Adds Total row for Advised, Received and Var.
- Uses the supplied yellow-header/bordered customer layout with the container number above the table.
- Keeps a versioned audit copy in application media and exposes downloads in both screens.
- Migration: `0009_client_receiving_report.py`.
