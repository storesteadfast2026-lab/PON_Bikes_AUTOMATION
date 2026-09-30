# Validation — 0917.1238

Validated against the uploaded `products_pon_pbp_auto.xml` snapshot.

- XML rows parsed: **8,984**.
- Required XML fields verified: `code`, `pon_sku`, `customer`, `code2`, `short_name`, `long_name`, `group1`, `group2`.
- Maximum observed `short_name` length: **30** characters.
- Historical name dictionary retained: **7,603** reliable exact long-name → short-name mappings.
- Learned textual abbreviation rules: **60** conservative rules.
- Learned rules explicitly exclude numeric tokens, so sizes, model numbers, capacities and similar numeric identifiers are not shortened by learned rules.
- XML parser successfully normalises the legacy Windows NBSP byte (`0xA0`) present in the current source file.
- `compose.yaml` parsed successfully as YAML and points to `/data/pon_products/products_pon_pbp_auto.xml`.
- All Python files passed `compileall` syntax validation.
- Core XML parsing and name-dictionary functions were executed directly against the uploaded XML.

The full Django test suite was not executed in the build environment because Django is not installed there and external package installation is unavailable. The project Docker image still installs Django from `requirements.txt` during a normal `docker compose build`.
