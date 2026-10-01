$ErrorActionPreference = "Stop"

$AppDir = "C:\Docker-Projects\PON_Bikes_Automation"
$ContainerId = "TGBU4621260"
$OutputName = "${ContainerId}_New_Products_Measurements.xlsx"
$OutputFile = Join-Path $PSScriptRoot $OutputName
$DockerFile = "/tmp/$OutputName"

if (-not (Test-Path $AppDir)) {
    throw "Application folder not found: $AppDir"
}

Set-Location $AppDir

Write-Host ""
Write-Host "============================================================"
Write-Host "PON - EXPORT NEW PRODUCT MEASUREMENTS"
Write-Host "Container: $ContainerId"
Write-Host "============================================================"

$PythonCode = @'
from collections import defaultdict
from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

from receiving.models import (
    Container,
    ContainerProductStatus,
    ProductDefinition,
)
from receiving.views import _persisted_product_check_data

CONTAINER_ID = "TGBU4621260"
OUTPUT = "/tmp/TGBU4621260_New_Products_Measurements.xlsx"

container = Container.objects.get(identifier=CONTAINER_ID)

# Historical classification is authoritative for "New".
new_statuses = list(
    ContainerProductStatus.objects
    .filter(container=container, import_classification="NEW")
    .order_by("code")
)

new_codes = [s.code.strip().upper() for s in new_statuses]
new_code_set = set(new_codes)

if not new_codes:
    raise RuntimeError(
        f"No historical NEW products found for container {CONTAINER_ID}."
    )

# Read the persisted Product Check rows so Count / LOC / Long_Code come
# from the actual received data for this container.
catalog, received_batch, rows, summary = _persisted_product_check_data(container)

if not received_batch:
    raise RuntimeError(
        f"No confirmed RECEIVED batch found for container {CONTAINER_ID}."
    )

received = defaultdict(lambda: {
    "count": 0,
    "locations": [],
    "long_codes": [],
})

for row in rows:
    code = str(row.get("code") or "").strip().upper()
    if code not in new_code_set:
        continue

    received[code]["count"] += int(row.get("count") or 0)

    loc = str(row.get("location") or "").strip()
    if loc and loc not in received[code]["locations"]:
        received[code]["locations"].append(loc)

    long_code = str(row.get("long_code") or "").strip()
    if long_code and long_code not in received[code]["long_codes"]:
        received[code]["long_codes"].append(long_code)

# Measurements entered/saved by the app.
definitions = {
    p.code.strip().upper(): p
    for p in ProductDefinition.objects.filter(code__in=new_codes).order_by("code", "-confirmed", "-pk")
}

missing = []
export_rows = []

def positive(value):
    if value is None:
        return False
    try:
        return Decimal(str(value)) > 0
    except Exception:
        return False

for code in new_codes:
    definition = definitions.get(code)

    if definition is None:
        missing.append((code, "No ProductDefinition"))
        continue

    length_mm = definition.length_mm
    height_mm = definition.height_mm
    width_mm = definition.width_mm
    weight_kg = definition.weight_kg

    invalid = []
    if not positive(length_mm):
        invalid.append("Length")
    if not positive(height_mm):
        invalid.append("Height")
    if not positive(width_mm):
        invalid.append("Width")
    if not positive(weight_kg):
        invalid.append("Weight")

    if invalid:
        missing.append((code, "Missing/invalid: " + ", ".join(invalid)))
        continue

    length_mm = Decimal(str(length_mm))
    height_mm = Decimal(str(height_mm))
    width_mm = Decimal(str(width_mm))
    weight_kg = Decimal(str(weight_kg))

    length_cm = length_mm / Decimal("10")
    height_cm = height_mm / Decimal("10")
    width_cm = width_mm / Decimal("10")
    cubic_m3 = (length_mm * height_mm * width_mm) / Decimal("1000000000")

    info = received.get(code, {})

    export_rows.append([
        code,
        " / ".join(info.get("long_codes", [])),
        info.get("count", 0),
        " / ".join(info.get("locations", [])),
        "New",
        float(length_cm),
        float(height_cm),
        float(width_cm),
        float(weight_kg),
        float(cubic_m3),
        float(weight_kg),
        float(height_mm),
        float(width_mm),
        float(length_mm),
    ])

if missing:
    details = "\n".join(f"  - {code}: {reason}" for code, reason in missing)
    raise RuntimeError(
        "The database contains historical NEW products without complete "
        "saved measurements:\n" + details
    )

# ------------------------------------------------------------
# Create Excel
# ------------------------------------------------------------
wb = Workbook()
ws = wb.active
ws.title = "New Products"

headers = [
    CONTAINER_ID,
    "Long_Code",
    "Count",
    "LOC",
    "New",
    "L",
    "H",
    "W",
    "Kg",
    "M3",
    "Weight",
    "Height",
    "Width",
    "Length",
]

ws.append(headers)

for item in export_rows:
    ws.append(item)

# Formatting
header_fill = PatternFill("solid", fgColor="D9EAF7")
new_fill = PatternFill("solid", fgColor="FFF2CC")
thin = Side(style="thin", color="D0D0D0")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

for cell in ws[1]:
    cell.font = Font(bold=True)
    cell.fill = header_fill
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = border

for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=14):
    for cell in row:
        cell.border = border
        cell.fill = new_fill
        cell.alignment = Alignment(vertical="center")

# Number formats
for row_num in range(2, ws.max_row + 1):
    for col in ("F", "G", "H"):
        ws[f"{col}{row_num}"].number_format = "0.0"
    ws[f"I{row_num}"].number_format = "0.000"
    ws[f"J{row_num}"].number_format = "0.000"
    ws[f"K{row_num}"].number_format = "0.000"
    for col in ("L", "M", "N"):
        ws[f"{col}{row_num}"].number_format = "0"

widths = {
    "A": 20,
    "B": 22,
    "C": 10,
    "D": 18,
    "E": 10,
    "F": 10,
    "G": 10,
    "H": 10,
    "I": 10,
    "J": 11,
    "K": 11,
    "L": 12,
    "M": 12,
    "N": 12,
}

for col, width in widths.items():
    ws.column_dimensions[col].width = width

ws.freeze_panes = "A2"
ws.auto_filter.ref = ws.dimensions

wb.save(OUTPUT)

print("")
print("=" * 70)
print("EXPORT COMPLETE")
print("=" * 70)
print(f"Container              : {CONTAINER_ID}")
print(f"Historical NEW products: {len(new_codes)}")
print(f"Products exported      : {len(export_rows)}")
print(f"Excel                   : {OUTPUT}")
print("=" * 70)
'@

$PythonCode | docker compose exec -T web python manage.py shell

if ($LASTEXITCODE -ne 0) {
    throw "Database export failed. No Excel file was copied."
}

docker compose cp "web:$DockerFile" "$OutputFile"

if ($LASTEXITCODE -ne 0) {
    throw "Excel was created in Docker but could not be copied to Windows."
}

if (-not (Test-Path $OutputFile)) {
    throw "Expected Excel file was not created: $OutputFile"
}

Write-Host ""
Write-Host "[PASS] Excel created from the application database:"
Write-Host $OutputFile
Write-Host ""

Start-Process $OutputFile
