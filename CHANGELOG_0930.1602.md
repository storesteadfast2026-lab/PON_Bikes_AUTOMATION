# PON Bikes Automation — 0930.1602

Incremental Product Check / New Product Import / Customer Report update.

- Added three-way PON classification: `Existing`, `PBP → PON`, `New`.
- `PBP → PON` is excluded from New counts/comments but included in the existing New Product Import workflow.
- Historical PBP CODE/PON_SKU/CODE2 identity, names, cubic, weight and dimensions are reused when valid.
- PBP Group1 is not copied; current PON Group1 mapping is resolved.
- Existing Group2 cubic rule is preserved, including CHG02 > 0.4.
- Customer Report migration rows are highlighted orange without changing values/calculations.
- Product Master parser preserves optional cubic/weight/height/width/length fields in existing raw_data JSON.
- No model change and no migration.
