# VALIDATION 0918.0930

## Static validation completed

- Python compilation: **PASS** for `receiving/`, migrations and `config/`.
- Operational Add Customer route/link removed: **PASS**.
- Customer remains registered and editable in Django Admin: **PASS**.
- `ContainerForm` reduced to Container ID, Customer and Container date: **PASS**.
- Container `year` is derived from the selected container date: **PASS**.
- Per-customer XML source/application path fields added: **PASS**.
- Product catalogues can be associated with a customer: **PASS**.
- Existing PON catalogue migration/backward compatibility included: **PASS**.
- PBP can continue sharing the current PON/PBP XML until a separate customer catalogue is configured: **PASS**.
- Alternate `.xml` filenames accepted; parser still validates the required XML row structure: **PASS**.
- Dashboard displays XML filename, source path, application path, availability and active copy: **PASS**.
- Scanner-first and optional-stage roadmap files included: **PASS**.
- Existing Stage 2 / UPStockSerial generation code was not changed by this release: **PASS**.

## Runtime validation limitation in build environment

The artifact build environment does not contain Docker or Django and has no network access to install them, so `manage.py migrate`, `manage.py check` and Django tests could not be executed here.

The included `Upgrade-PON-CustomerXML-0918.0930.ps1` runs the following in the user's real Docker environment:

1. Rebuild/recreate `web` while preserving PostgreSQL volumes.
2. `python manage.py migrate`.
3. `python manage.py check`.

If any of these fails, the script stops instead of reporting a successful upgrade.
