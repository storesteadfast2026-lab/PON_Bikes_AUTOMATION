# CHANGELOG 0921.1250

## Container full-process view

The container detail page now shows all four operational stages immediately:

1. Receive & Scan
2. Check Products
3. Translogic
4. Complete

### Behaviour
- The four main stages are always expanded and cannot be collapsed accidentally.
- The workflow stepper remains at the top and now acts as quick navigation to each stage.
- Each stage keeps its existing status, summary metrics, primary action and detailed links.
- Optional/technical controls inside a stage remain under their own Advanced/Manual disclosure areas.
- The stage area now uses the full page width for easier scanning.
- The overall status/next-action panel remains available below the four stages.

### Compatibility
- No business rules were changed.
- No database migration was added.
- Existing Job Order, XLS product master, PRODUCT_MOVES, UPStockSerial and customer report logic is unchanged.
