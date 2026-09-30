# PON Bike Automation — Changes 0917.1122

Base package: `PON_Bike_Automation_Stage1_0917.0900.zip`.

## New product entry screen

- Moved **New product data for Translogic** above **Product classification**.
- Replaced the horizontally scrolling input table with a compact responsive grid.
- Product code, long code, short name, full name, Length, Height, Width and Weight remain visible together on standard desktop widths.
- Browser Tab order follows the visual row order for fast keyboard data entry.
- Length, Height, Width and Weight remain required numeric fields.
- When the operator reaches a completely blank row, the nearest complete four numeric values above are proposed automatically.
- Proposed/copied values are shown in blue.
- A proposed value changed by the operator is shown in orange; unchanged proposed values stay blue.
- There is no per-row confirmation action.
- Data is persisted only when **Save new-product data** is pressed at the bottom.
- Existing saved product definitions continue to be stored by product code and remain available when containers are deleted/recreated.

## Existing business rules preserved

- Dimensions are entered in centimetres and stored/exported internally in millimetres.
- Short name remains limited to 30 characters.
- Full name remains complete.
- Cubic and `Group2=CHG02` rules are unchanged.
- Existing PostgreSQL volume naming and Compose project name are unchanged, so updating the source folder does not intentionally create a new database volume.
