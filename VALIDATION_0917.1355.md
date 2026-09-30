# Validation — 0917.1355

- Python compileall: PASS.
- Uploaded XML parsed: 8,984 product rows.
- Historical exact LongName → ShortName matches: 7,603.
- Learned word/token abbreviation rules: 60 unique sources.
- Django Admin registration for `ShortNameDictionaryRule`: verified statically.
- Admin inline editing of `Abbreviation` and `Active`: verified statically.
- Migration `0007_short_name_dictionary_rule`: present with data population from existing `ProductCatalog.name_dictionary` JSON.
- Product catalogue activation syncs learned rules into Django without overwriting administrator-edited abbreviation/active values.
- ShortName suggestion reads the effective Django-controlled rule set when rules are present.
- Full Django runtime tests could not be executed in this build environment because Django is not installed and external package installation is unavailable. The application Docker image installs the project requirements during normal build.
