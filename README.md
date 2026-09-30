# PON Bike Receiving Automation — Stages 1 & 2

This Django application automates the PON bicycle receiving workflow from the first scan through preparation of the Translogic serial/location update file.

### Guided workflow UI

The primary container screen is now a single guided workflow with four stages: **Receive & Scan → Check Products → Translogic → Complete**. The normal operator path stays on this one page and shows only summary counts, status, the next action and file locations. Detailed comparison/product/movement screens remain available as secondary **View details** pages. Earlier stages remain reviewable at any time; if an input changes, dependent outputs are marked outdated and are refreshed automatically when the operator downloads the current file. Completed containers can be reopened before making corrections.

The workflow always displays the operator-facing **Translogic source**, **local working copy** and **final destination** for operational files. Because Docker Desktop cannot reliably bind the mapped network drive `T:` in this environment, the recommended Docker configuration uses local bridge folders under `C:\Docker-Projects\PON_Bike_Data`.


### Release 0928.1528 — multi-container manifests and automatic mapping

- One Client Manifest can contain multiple Container IDs and is split into independent container-specific confirmed batches.
- Additional detected containers are created as `PENDING` with manifest/advised data already loaded and Job Order unassigned.
- Job Order is the primary operator identity and must be unique per container.
- Mapping now detects worksheet, header/data start, Product/Bike code, Description, Quantity and Container columns using confidence, data patterns, saved Customer profiles and Product Master validation where available.
- Confirmed mappings are learned automatically and exact structure matches can go directly to Validate Preview.
- Normal operator output actions remain Download-only.

## Included in this version

- Create a customer and container receiving job.
- Configure the root folder used for 2026 PON containers.
- Upload `.xlsx` and `.xlsm` source files without modifying the originals.
- List Excel files from the configured server folder and import a controlled copy.
- Detect likely SKU, description and quantity columns.
- Recognise coloured rows, including the theme-colour fill used in the supplied `TCNU4108637.xlsx` file.
- Interpret first-scan files where a `T9999` row sets the pallet location for the bike codes that follow.
- Preview normalized information before confirming an import.
- Prevent the same file from being uploaded twice for the same container and purpose.
- Compare expected and received quantities in both directions.
- Preserve source worksheet, row, original values, fill signature and file hash for audit purposes.
- Save reusable import profiles for future customer layouts.
- Synchronize the internal Translogic PON product catalogue from `products_pon_pbp_auto.xls`.
- Import all catalogue rows with `code`, `pon_sku`, `customer`, `code2`, `short_name`, `long_name`, `group1` and `group2`.
- Compare received bike codes exactly against all three Translogic identifiers (`code`, `pon_sku`, `code2`).
- Build and persist a long-name → short-name dictionary from the active XML catalogue, plus conservative learned textual abbreviation rules.
- Clearly classify each received product row as `Existing` or `New`.
- Download an Excel report matching the base layout with Code, Long_Code, Count, LOC, New, L, H, W and Kg.
- Group the printable product list by code, sum its quantity, retain only its first pallet and sort the report by LOC ascending.
- Limit the `PON Product Check` print area to columns A:I while retaining extra audit fields in hidden columns.
- Print `PON Product Check` in portrait orientation.
- Use compact portrait-print widths, leaving Count and LOC centred with visible cell padding.
- Leave existing-product status cells blank and display only `New` exceptions.
- Populate L, H, W and Kg from permanently saved new-product definitions.
- Generate a printable `BARCODE Converter` worksheet with embedded Code 128 images for item and quantity, plus a running total.
- Centre every barcode image horizontally and vertically within its Excel cell.
- Use 14-point text throughout the printable `BARCODE Converter` table.
- Open `BARCODE Converter` without a frozen split so the header is not duplicated visually in Excel.
- Display `Saved` or `Pending` beside each new product in the application, with completed and pending totals.
- Show `New product data for Translogic` before the detailed product-classification table.
- Use a compact no-horizontal-scroll entry grid so code, names, dimensions and weight remain visible together on normal desktop widths.
- Support fast keyboard entry with `Tab`: the nearest complete measurements above are proposed automatically for a blank row, copied values are shown in blue and any edited proposed value is shown in orange.
- Save the entire new-product form only with the bottom `Save new-product data` button; there is no per-row confirmation click.
- Stack LongName directly below ShortName in the same visual column so the two names can be compared quickly while reducing the overall grid width.
- Resolve Group1 from configurable **Group1 family mappings** in Django Administration rather than a single fixed Group1 setting.
- Block save/export and display **Needs decision** when no unique active family/suffix relation can be resolved.
- Capture and permanently reuse ShortName, LongName, resolved Group1, dimensions and weight for every new product.
- Enforce the Translogic column-C limit of 30 characters.
- Suggest meaningful 30-character names using business abbreviations instead of blindly truncating descriptions; every suggestion remains editable.
- Accept Length, Height and Width from operators in centimetres, convert them to millimetres (`cm × 10`) and store the millimetre values permanently for Translogic.
- Calculate Cubic from the stored millimetres by rounding up `Length × Height × Width / 1,000,000,000` to three decimals.
- Assign `Group2=CHG02` when Cubic is greater than `0.4`.
- Generate the exact 30-column `New Product Import` workbook for new product codes, including Inner, Outer, Layer, Comment and Date.
- Highlight required New Product Import headers A, C, D, H, J, M, P, R, S, T, U, AA and AD in yellow.
- Require the operational container date when the container is created, allow it to be corrected later, and export that exact date in column AD.
- Save every generated workbook and its SHA-256 audit record in persistent application storage.
- Export `New Product Import` as Microsoft Excel 5.0/95 `.xls` by default, with a configurable `.xlsx` option.
- Keep `Product check + barcodes` as `.xlsx` so its embedded printable Code 128 images are preserved.

- Add **Part 2 · Movements & labels** to each container.
- Read a controlled local working copy of the Translogic export `PRODUCT_MOVES.CSV`, while always displaying the real source path `T:\STEADFAST\EXCEL FILES\PRODUCT_MOVES.CSV`; manual CSV upload remains a fallback.
- Require the verified `product,stock_in_mov` schema and reject blank, non-numeric, over-length or duplicate Movement Numbers.
- Reconcile movements by **product code** rather than relying on global row position.
- Require one physical bike per confirmed first-scan row and an assigned `T9999` location.
- Use the original first-scan worksheet row as `serial_no`, preserving the existing process.
- Generate the verified `Movement,serial_no,Loc` `UPStockSerial.csv` shape, including the fixed 500-row operational template.
- Write `UPStockSerial.csv` to the configured local working folder for review, while always keeping a versioned audit copy in application storage. The workflow also shows the final Translogic destination `T:\Import\UPStockSerial.csv` as a separate controlled transfer step.
- Block generation when product counts differ between the confirmed first scan and `PRODUCT_MOVES.CSV`; the guided screen shows only the summary/status, while the detailed screen remains available for product-level mismatches.
- Generate the customer receiving `.xlsx` into a visible local working reports folder as well as persistent application storage.
- Detect when `UPStockSerial.csv` or the customer report became outdated because a confirmed input, PRODUCT_MOVES snapshot, product catalogue or saved new-product definition changed.

The application prepares the Translogic import files but still does **not** execute the final import/commit inside Translogic.

## Test result expected for the supplied TCNU4108637 files

The automated tests verify:

- 26 coloured client-manifest product rows.
- 78 expected bicycle units.
- 26 pallet locations.
- 3 bicycles at each pallet location.
- 78 received bicycles.
- Exact quantity match for all 13 product codes.

## Option A — Run with Docker Desktop

1. Copy `.env.example` to `.env`.
2. Change the passwords and `DJANGO_SECRET_KEY` in `.env`.
3. Add this extra line to `.env` using the Windows folder that Docker Desktop can access:

   ```text
   PON_HOST_PATH=S:/FORMS/CUSTOMER/PON - Pon.Bike/2026 Containers
   PON_PRODUCT_HOST_DIR=C:/Docker-Projects/Freight-Calc-v1.6/uploaded_data
   PON_MOVES_HOST_DIR=C:/Docker-Projects/PON_Bike_Data/translogic
   PON_IMPORT_HOST_DIR=C:/Docker-Projects/PON_Bike_Data/import
   PON_REPORT_HOST_DIR=C:/Docker-Projects/PON_Bike_Data/reports
   ```

4. From PowerShell, run:

   ```powershell
   docker compose up --build
   ```

5. Open `http://localhost:8001`.
6. Log in with the superuser configured in `.env`.

Docker Desktop often cannot see mapped network drives such as `T:` that exist only in the interactive Windows session. For `PRODUCT_MOVES` and `UPStockSerial`, use the local bridge folders shown above. Copy the Translogic export from `T:\STEADFAST\EXCEL FILES` into the local `translogic` working folder before Refresh; after review, copy the generated local `UPStockSerial.csv` to `T:\Import`. A later bridge/UNC deployment can automate those two transfers without changing the receiving logic.

## Option B — Run natively on Windows

From PowerShell in this project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:PON_CONTAINER_ROOT = 'S:\FORMS\CUSTOMER\PON - Pon.Bike\2026 Containers'
$env:PON_PRODUCT_MOVES_PATH = 'T:\STEADFAST\EXCEL FILES\PRODUCT_MOVES.CSV'
$env:PON_UPSTOCKSERIAL_PATH = 'T:\Import\UPStockSerial.csv'
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

Then open `http://localhost:8000` (native Windows execution only).

The Docker host port can be changed in `.env` without editing `compose.yaml`:

```text
PON_WEB_PORT=8001
```

The application still listens on port `8000` inside its container. By default Docker publishes it as `8001:8000`, avoiding a conflict with the Freight Calculator.

The image includes Gnumeric's `ssconvert` utility to produce the genuine BIFF7 `Microsoft Excel 5.0/95` format requested by Translogic for `New Product Import`. The application validates the BIFF7 marker before offering that import file. Barcode reports are not imported into Translogic and remain `.xlsx`, because BIFF7 conversion removes embedded barcode images.

## Apply this update without deleting the database

For the 0918.0930 release, copy your existing `.env` into the new project folder and run:

```powershell
.\Upgrade-PON-CustomerXML-0918.0930.ps1
```

The script preserves PostgreSQL, rebuilds/recreates only the web service, applies migration `0010_customer_product_catalog_configuration`, and runs `python manage.py check` inside Docker. It also adds the operator-facing PON XML source path to `.env` when it is missing.

Equivalent manual sequence:

```powershell
docker compose up -d --build --force-recreate web
docker compose exec -T web python manage.py migrate
docker compose exec -T web python manage.py check
```

Do not add `-v` to `docker compose down`; the database volume must be preserved.

The Compose project name is fixed as `pon_bike_automation_09161055`, matching the original installation. This means replacing the application folder does not silently create a different database volume. Normal restarts, `docker compose down`, rebuilds and Windows restarts preserve:

- PostgreSQL data in `pon_bike_db`.
- Uploaded and generated files in `pon_bike_media`.

Only `docker compose down -v` intentionally deletes those volumes.

SQLite is used for this simple local test. Docker uses PostgreSQL.

## Reproduce the real-file parser tests

The sample files are included only for this internal test package. Run:

```powershell
python -m unittest discover -s tests -v
```

## Import TCNU4108637

1. Create the `PON - Pon.Bike` customer if it is not already present.
2. Create container `TCNU4108637` for 2026.
3. Upload `TCNU4108637.xlsx` as **Client manifest**.
4. Accept the suggested mapping: SKU `D`, description `E`, quantity `G`, coloured rows only.
5. Preview and confirm 26 rows / 78 units.
6. Upload `TCNU4108637 PON CON40 15-09-26.xlsx` as **First scan / received bikes**.
7. Accept column `A`, row `1`, and the `T9999` location-stream option.
8. Preview and confirm 78 rows / 78 units.
9. Open **View comparison**. All 13 codes should show `MATCH`.

## Server-folder configuration

The default setting is:

```text
S:\FORMS\CUSTOMER\PON - Pon.Bike\2026 Containers
```

It can be changed using either:

- Environment variable `PON_CONTAINER_ROOT`, or
- Django Administration → App settings, using key `PON_CONTAINER_ROOT`.

The database setting takes priority over the environment variable. This allows future yearly and customer routes to be added without changing application code.

The official internal Translogic product source is:

```text
C:\Docker-Projects\Freight-Calc-v1.6\uploaded_data\products_pon_pbp_auto.xls
```

For Docker Desktop, `.env` maps its containing folder read-only:

```text
PON_PRODUCT_HOST_DIR=C:/Docker-Projects/Freight-Calc-v1.6/uploaded_data
```

Inside Docker the application reads:

```text
/data/pon_products/products_pon_pbp_auto.xls
```

Docker reads the host folder through `PON_PRODUCT_HOST_DIR`; the XML file itself is read-only from the PON container. The path can also be overridden in Django Administration using the `PON_PRODUCT_CATALOG_PATH` app setting. A persisted legacy `PRODUCTS_PON_PBP.CSV` override is intentionally ignored after this upgrade.

## Guided container workflow

Open a container from the dashboard. The main page shows four clickable stages and always keeps the important file routes visible.

- **Receive & Scan** — confirm Client Manifest and First Scan. Replacements are available inside the stage instead of as separate top-level screens.
- **Check Products** — see only Advised, Received, Variance and New product totals. Use the detail screen only when a new product needs data or a product-level review is required.
- **Translogic** — refresh the local working copy of `PRODUCT_MOVES.CSV`, reconcile it to the confirmed First Scan, then generate `UPStockSerial.csv`. A mismatch blocks generation and links to the detailed reconciliation page.
- **Complete** — generate/review the customer report, finish the Translogic import/label step, then explicitly mark the container Complete. A completed container stays reviewable and can be reopened before corrections.

File cards show:

```text
PRODUCT_MOVES
Source:  T:\STEADFAST\EXCEL FILES\PRODUCT_MOVES.CSV
Working: C:\Docker-Projects\PON_Bike_Data\translogic\PRODUCT_MOVES.CSV

UPStockSerial
Working: C:\Docker-Projects\PON_Bike_Data\import\UPStockSerial.csv
Final:   T:\Import\UPStockSerial.csv

Customer report
Working: C:\Docker-Projects\PON_Bike_Data\reports
Final:   configurable later when the archive/customer-send location is agreed
```

## Product catalogue and new-product report

The catalogue source is XML and contains `code`, `pon_sku`, `customer`, `code2`, `short_name`, `long_name`, `group1` and `group2`. The app sanitises legacy Windows NBSP bytes before XML parsing and learns a conservative long-name/short-name dictionary from the active catalogue.


1. Open the dashboard.
2. Create the container and enter its required **Container date**. Existing containers can be corrected with **Edit container**.
3. In **PON product catalogue**, select **Synchronize internal file**.
4. Open a container with a confirmed first-scan file.
5. Select **Check new products**.
6. Review `Existing` and `New` classifications.
7. Review ShortName and LongName together, confirm that Django resolved a clear Group1 family, then complete length, height and width in centimetres plus weight in kilograms and save. Django converts dimensions to millimetres. A product with no clear Group1 relation cannot be saved/exported until the relation is added in Administration → Group1 family mappings.
8. Select **New Product Import** to download the Translogic product file.
9. Select **Product check + printable barcodes (.xlsx)** for the review list and printable barcodes.

The downloaded workbook contains:

- `PON Product Check`: the base product list with new/existing status and dimension columns labelled and displayed in millimetres; they remain empty when a new product has not yet been completed.
- `BARCODE Converter`: printable Code 128 barcodes for every product and its quantity.

`New Product Import` contains one row per **new product code**, not one row per physical bicycle. Its columns and fixed values follow the `ContainerScanMacro4 FABIAN Cervelo.xlsm` reference. The barcode worksheet contains all received bicycle quantities.

Column `AD (Date)` contains the operational date entered by the user when the container is created. It never uses the file-generation date. Export is blocked for a legacy container until that date is entered with **Edit container**.

The short-name suggestion first checks the persistent dictionary built from the XML's real `long_name` / `short_name` pairs. If there is no reliable exact match, it applies only repeated, high-confidence textual abbreviations learned from the XML, then the stable business fallbacks such as `FRAME → FR`, `OFFSET → OFF`, `CLOUD → CLD` and `BREAK → BRK`. Numeric model, size and capacity tokens are never learned as abbreviation rules. Review or edit the proposal, then save all rows once with the bottom button; exports never silently cut the text at character 30.

## Translogic export configuration

Open **Administration → App settings** to change these values without editing code:

| Key | Default | Purpose |
|---|---|---|
| `TL_EXPORT_FORMAT` | `excel_5_95` | Use `excel_5_95` for the legacy Translogic import `.xls`, or `xlsx` for a future modern import format. It does not change the printable barcode workbook, which must remain `.xlsx`. |
| `TL_CUSTOMER` | `PON` | Customer column. |
| `TL_STATUS` | `L` | Status column. |
| `TL_GROUP2_CUBIC_THRESHOLD` | `0.4` | Boundary for the special Group2. |
| `TL_GROUP2_LARGE` | `CHG02` | Group2 when Cubic is greater than the boundary. |
| `TL_GROUP2_DEFAULT` | blank | Group2 at or below the boundary. |
| `TL_QUANTITY` | `1` | Fixed Quantity. |
| `TL_PALLET` | `0` | Fixed Pallet. |
| `TL_LIFT` | `1` | Fixed Lift. |
| `TL_OUTER` | `1` | Fixed Outer value in column AA. |

### Group1 family mapping

Group1 is no longer a single fixed application setting. Open **Administration → Group1 family mappings**. Each row defines a family, a suffix such as `CVL`, `SCZ`, `FCS` or `KHF`, recognition phrases, priority and active status. The configured Translogic customer prefix is prepended automatically, so suffix `CVL` becomes `PONCVL` for PON and `PBPCVL` for PBP.

The upgrade seeds conservative relationships supported by the current XML: Cervelo→CVL, Santa Cruz→SCZ, Focus→FCS, explicit legacy Focus E-Bikes→FEB, Kalkhoff→KHF, explicit Kalkhoff Non E-Bikes→KNE, Gazelle→GAZ and Reserve→RSV. Current XML bike prefixes `C26/C27`, `SC26/SC27`, `F26` and `K26` are included where the relationship is sufficiently clear. Ambiguous/category suffixes such as `SCP`, `ACC`, `HAN` and `MAR` are intentionally not guessed for a new bicycle.

If no active rule matches, or equal-priority rules point to different suffixes, the UI shows **Needs decision** and tells the operator to add/adjust the relation in Django Administration. Saving and New Product Import are blocked until Group1 is resolved.

Matching is exact after trimming spaces and converting letters to uppercase. Partial matches are never treated as existing products.

When the folder is available, the container screen lists Excel workbooks from that root and places filenames or subfolders matching the selected container first. Selecting a file creates a controlled copy in application storage; the source file remains unchanged.

## Safety decisions in this MVP

- The server folder is mounted read-only in Docker.
- Uploaded source files are copied into controlled application storage.
- Imported information stays in preview until a user confirms it.
- A new confirmed import supersedes the prior confirmed import of the same type, but the previous batch remains in the database.
- The application generates controlled Translogic files but never imports them automatically.

## Short Name Dictionary (0917.1355)
The XML-learned abbreviation rules are visible in **Django Administration → Short name dictionary**. Administrators can edit the abbreviation (`target`) or disable a rule (`active`) without changing code. Exact historical LongName → ShortName matches remain automatic and take priority.

## Part 2 — PRODUCT_MOVES and UPStockSerial

After Part 1 is complete and the receiving job in Translogic has been exploded/split so that there is one physical bike per movement:

1. From Translogic, export `SF Receive Product Label Mov PON/PBP/DLS`. The operational file is `T:\STEADFAST\EXCEL FILES\PRODUCT_MOVES.CSV`.
2. Open the container in PON and select **Part 2 · Movements & labels**.
3. Select **Read / refresh PRODUCT_MOVES.CSV**. The app snapshots the CSV and its SHA-256 for audit. If Docker cannot see the T: mount, use **Upload CSV fallback**.
4. The app compares product quantities in the confirmed first scan against the movement export. A product mismatch blocks generation; it is never silently repaired by row order.
5. For each product, movement rows are paired with that product's physical first-scan rows in original scan order. The original worksheet row is written as `serial_no`; the inherited `T9999` pallet/location is written as `Loc`.
6. When every product quantity matches, select **Generate UPStockSerial.csv**.
7. The application creates the exact verified header `Movement,serial_no,Loc`, right-aligns Movement to the existing 10-character field, and pads the file to 500 data rows (`A2:C501`) to preserve the current Translogic import template.
8. A versioned audit copy is retained in application media. When the Docker mount is available, the operational copy is also written as `T:\Import\UPStockSerial.csv`.
9. In Translogic, run `SF2 Stock Serial Update`, review, import/commit, then print from `SF Receive Product Label Mov PON/PBP/DLS - Print`.

### Part 2 path configuration

Native Windows defaults:

```text
PON_PRODUCT_MOVES_PATH=T:\STEADFAST\EXCEL FILES\PRODUCT_MOVES.CSV
PON_UPSTOCKSERIAL_PATH=T:\Import\UPStockSerial.csv
```

Docker bind mounts:

```text
PON_MOVES_HOST_DIR=T:/STEADFAST/EXCEL FILES
PON_IMPORT_HOST_DIR=T:/Import
```

Inside Docker these are exposed as `/data/pon_translogic/PRODUCT_MOVES.CSV` and `/data/pon_import/UPStockSerial.csv`. If Docker Desktop cannot mount the mapped T: drive, use the UNC path behind T: in `PON_MOVES_HOST_DIR` and `PON_IMPORT_HOST_DIR`.



## Final client receiving report (0918.0730)

Once both the client manifest and first scan are confirmed, the app can generate the customer-facing Excel independently of Part 2. Open **Expected vs received** or **Part 2 · Movements & labels** and select **Generate client Excel (.xlsx)**.

The workbook is named `Receiving_Container_Data_<container>_<timestamp>.xlsx` and contains the requested columns `Item Code`, `Item Name`, `Advised`, `Received`, `Var`, `Comment`. `Item Name` uses the active XML LongName for existing products, the saved new-product LongName for new products, and the client description as fallback. `Var` is `Received - Advised` and is explicitly `0` when quantities match. `Comment` is blank except for products classified as new for this container. The app snapshots the New/Existing decision during Product Check so a later XML refresh cannot erase the historical `New` flag. Client-manifest order is retained and unexpected received-only products are appended. A Total row sums Advised, Received and Var.

Generated client files are versioned in application media and remain downloadable from both the comparison and Part 2 screens. This output does not depend on PRODUCT_MOVES or UPStockSerial, so it can be generated while Part 2 is being tested.

## 0918.0815 - UPStockSerial ordering

The final `UPStockSerial.csv` is written in ascending numeric `Movement` order to match the historical Excel output. This changes only the output row order: the reconciled Movement-to-`serial_no`-to-`Loc` assignment is preserved. The three-column layout and 500-data-row legacy shape remain unchanged.

## Release 0918.0930 — customer XML configuration and simplified start screen

The operator dashboard is intentionally reduced to the information needed to start or resume receiving. Customers are maintained in Django Admin. Each Customer can define an operator-facing XML source path and an application-readable XML path; the selected customer's file name/path/status is shown directly beside the New Container form.

The current PON/PBP XML continues to work with the existing Docker mount. New customers can be configured in **Django Admin → Receiving → Customers**. If a customer's XML is stored outside the currently mounted `/data/pon_products` host folder, the Docker mount must also be extended before the application can read it.

Future scanner and optional-stage requirements are documented in:
- `docs/CLIENT_CONFIGURATION_AND_SCANNER_ROADMAP_0918.0930.md`
- `docs/WORKFLOW_AND_FILE_LIFECYCLE_0918.0930.md`

## 0918.1255 — Product master is now Excel .xls
The operational shared PON/PBP master is now expected at:

`C:\Docker-Projects\Freight-Calc-v1.6\uploaded_data\products_pon_pbp_auto.xls`

Inside Docker it is read as:

`/data/pon_products/products_pon_pbp_auto.xls`

Customer-specific paths remain configurable in Django Admin. The `.xls` parser expects the same product metadata used previously: `code`, `pon_sku`, `customer`, `code2`, `short_name`, `long_name`, `group1`, `group2`.

## UI release 0918.1342
Configure Import and Validate Preview now use reusable `app-*` workflow components. See `docs/UI_DESIGN_SYSTEM_0918.1342.md`. This release does not change import business rules or database models.

## Release 0918.1437 — Home Recent Containers rail

The Home / Container Processing screen now keeps recent containers in a persistent left-side rail. Each container card opens the container directly with one click and can be filtered by Container ID, customer, Job Order or status. The main area is dedicated to creating a new container and showing the selected customer's product master.

New containers require a Job Order in the operational form. Existing records remain compatible.

## Release 0921.1250 — full container process view

The container detail screen now displays Receive & Scan, Check Products, Translogic and Complete simultaneously. The operator no longer needs to expand each stage to understand what has happened. The top workflow indicator remains available for quick scrolling to a stage. Detailed/exception screens are still available when needed.

## Release 0929.1322 — guarded Translogic exchange

This release does not assume that the Windows mapped drive `T:` is accessible to Docker. During `01_PREPARE_INSTALL.ps1`, the current configured Translogic destination and PRODUCT_MOVES source are inspected on the Windows host; mapped-drive paths are resolved to UNC when available and Docker bind access is probed before direct integration is enabled.

For UPStockSerial and New Product Import, copying remains an explicit operator action. A confirmation page is shown before replacement and the destination is verified by SHA-256 after copy. New Product Import numbered files are discovered from the real folder as one coherent existing 1–5 set; the oldest actual file is proposed. PON never assumes the numbered filename/extension and never converts a mismatched generated format.

PRODUCT_MOVES Refresh uses the real source directly only when it passed preflight and remains readable; otherwise the existing local working-copy/manual-upload process remains active.

## Continuity Snapshot

From release 0930.1047, `04_VALIDATE.ps1` validates only. After `Failures: 0`, run `05_CREATE_CONTINUITY_SNAPSHOT.ps1` manually to create/update the authoritative Continuity Snapshot under `C:\Docker-Projects\PON_Bikes_Automation\continuity`. The installed engine remains `tools\Create_Continuity_Snapshot.ps1`. See `docs/18_CONTINUITY_SNAPSHOT.md`.
