# PON Bike Automation 0917.1324

Group1-family and compact name-comparison release, based on the working 0917.1308 XML version.

- Added `Group1Family` as a Django-admin configurable relationship between family, Group1 suffix, recognition phrases and priority.
- Group1 is now resolved per new product; the configured customer prefix is added automatically (`PON` + `CVL` → `PONCVL`).
- Seeded conservative clear relationships: Cervelo→CVL, Santa Cruz→SCZ, Focus→FCS, explicit legacy Focus E-Bikes→FEB, Kalkhoff→KHF, explicit Kalkhoff Non E-Bikes→KNE, Gazelle→GAZ and Reserve→RSV.
- Current XML prefixes C26/C27, SC26/SC27, F26 and K26 are included where the family relation is clear enough for new bicycles.
- Ambiguous/category suffixes (`SCP`, `ACC`, `HAN`, `MAR`) are not guessed.
- If no relationship is clear, the UI displays `Needs decision` and instructs the operator to add/adjust it in **Administration → Group1 family mappings**. Save and New Product Import remain blocked until resolved.
- Removed the legacy fixed `TL_GROUP1` export setting.
- `ProductDefinition` now stores the resolved Group1 and the mapping used.
- New Product Import column J now uses each product's resolved Group1.
- In **New product data for Translogic**, LongName now sits directly below ShortName in the same column for visual comparison.
- The separate LongName column was removed, making the data-entry grid narrower; Group1 status now uses the space beneath LongCode.
- Existing XML parser, 30-character ShortName dictionary, measurement proposal workflow and Group2 cubic rule are retained.
