# Validation — 0917.1324

Validated against the uploaded `products_pon_pbp_auto.xml` and the 0917.1308 code base.

- Uploaded XML rows parsed: **8,984**.
- Historical name dictionary: **7,603** reliable exact LongName → ShortName matches.
- Learned abbreviation rules: **60**.
- Maximum XML ShortName length: **30**.
- Group1 resolver checks active Django mappings and accepts only a unique highest-priority suffix.
- Direct resolver checks: `C26 … → PONCVL`, `SC26 … → PONSCZ`, `F26 … → PONFCS`, `K26 … → PONKHF`.
- Unknown family check returns unresolved and the Administration instruction instead of guessing.
- Synthetic New Product Import workbook verified column **J = PONCVL**, column **M = LongName**, and the existing cubic/Group2 rule remained active.
- All project Python files passed `compileall`.
- Migration `0006_group1_family_mapping.py` creates the mapping table, adds product-level Group1 fields, seeds the conservative relationships and removes the obsolete `TL_GROUP1` setting.
- Full Django test execution was not available in this build environment because Django is installed inside the project Docker image, not the artifact-generation runtime.
