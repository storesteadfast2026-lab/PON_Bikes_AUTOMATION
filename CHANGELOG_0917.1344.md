# PON Bike Automation 0917.1344

## New product data for Translogic — alignment adjustment

- First input line inside each product section is now aligned as:
  - Long code
  - Short name (max 30)
  - Length cm
  - Height cm
  - Width cm
  - Weight kg
- Second line inside each product section is now aligned as:
  - Group1
  - Long name (spans the remaining width)
- Product code and Saved/Pending status remain at the top of each product section.
- The change is visual/layout only. XML parsing, historical name dictionary, Group1 family mapping, dimensions, Group2 rules, saving logic and exports are unchanged from 0917.1324.
