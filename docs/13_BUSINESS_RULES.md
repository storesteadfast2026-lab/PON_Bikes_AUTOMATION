# 13 — Business Rules

- One non-blank Job Order belongs to one Container.
- A client manifest may contain multiple Container IDs.
- Auto-created containers start PENDING and do not receive an invented Job Order.
- Operational data is isolated by Container.
- First Scan requires a Job Order.
- Product Check can be downloaded before NEW product dimensions are complete.
- Printable Product Check dimensions are shown in cm.
- ProductDefinition dimensions remain stored internally in mm.
- Translogic creates Movement Numbers; PON does not invent them.
- PRODUCT_MOVES quantity reconciliation must be valid before UPStockSerial is considered ready.
- Normal output UI uses Download rather than Generate/Regenerate.
- Stage selector clicks change visible content only; they do not alter workflow completion state.

## PBP → PON classification (0930.1602)

For PON receiving, exact PON matches take precedence. A SKU with no PON record but an exact PBP match is `PBP → PON`; it is not New but must be included in New Product Import so a PON Translogic record can be created. PBP Group1 is never copied directly: current PON family mapping is authoritative. Customer Report rows for this classification have no `New` comment and are highlighted orange only for visibility.
