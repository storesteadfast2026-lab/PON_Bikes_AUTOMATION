"""PON Second Scan. Product validation is mandatory before serial persistence."""
import csv
from collections import Counter
import hashlib
import io
import re

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Container, FirstScanSession, ImportBatch, ProductMovesImport, SecondScanMovement, SecondScanSession

LOCATION = re.compile(r"^[A-Z]{2}\d{3}$")
MOVEMENT = re.compile(r"^[0-9]{1,10}$")
# Sheet 'TL Stock': movement A, product D, location I, serial S, Long SKU U, WH_LOC V.
ALIASES = {
    "movement": ("movement", "movementnumber", "movno", "mov", "stockinmov"),
    "expected_product": ("product", "productcode", "code"),
    "source_location": ("location", "loc", "palletref"),
    "wh_loc": ("whloc", "warehouselocation"),
    "existing_serial": ("serial", "serialno", "serialnumber"),
    "long_sku": ("longsku", "longcode", "code2"),
}


def clean(value):
    return str(value or "").strip().upper()


def parse_stock(data, expected):
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    headers = {re.sub(r"[^a-z0-9]", "", (h or "").lower()): h for h in (reader.fieldnames or [])}
    mapping = {field: next((headers[a] for a in aliases if a in headers), None) for field, aliases in ALIASES.items()}
    if len(reader.fieldnames or []) == 23:
        for field, index in {"movement": 0, "expected_product": 3, "source_location": 8,
                             "existing_serial": 18, "long_sku": 20, "wh_loc": 21}.items():
            mapping[field] = mapping[field] or reader.fieldnames[index]
    if not mapping["movement"] or not mapping["expected_product"]:
        raise ValueError("CSV requires Movement / Mov_no / stock_in_mov and Product columns.")
    rows = {}
    known_serials = set()
    for raw in reader:
        if None in raw:
            raise ValueError("CSV row has more values than its header.")
        serial = clean(raw.get(mapping["existing_serial"])) if mapping["existing_serial"] else ""
        if serial and serial != "0":
            known_serials.add(serial)
        movement = clean(raw.get(mapping["movement"]))
        if movement not in expected:
            continue  # STOCK_SERIAL_SCANNING can contain stock outside this container.
        if not MOVEMENT.fullmatch(movement):
            raise ValueError("Movement Number must contain 1–10 digits.")
        if movement in rows:
            raise ValueError(f"Duplicate Movement Number: {movement}.")
        row = {field: clean(raw.get(header)) if header else "" for field, header in mapping.items()}
        if row["expected_product"] != clean(expected[movement]):
            raise ValueError(f"Movement {movement}: Product differs from this container's PRODUCT_MOVES.")
        for field, limit in (("expected_product", 100), ("source_location", 30), ("wh_loc", 30), ("existing_serial", 160), ("long_sku", 160)):
            if len(row[field]) > limit:
                raise ValueError(f"Movement {movement}: {field} is too long.")
        rows[movement] = row
    missing = set(expected) - rows.keys()
    if missing:
        raise ValueError(f"Stock data missing {len(missing)} container movements; first: {sorted(missing)[0]}.")
    if not rows:
        raise ValueError("No container movements found in STOCK_SERIAL_SCANNING.CSV.")
    return rows, sorted(known_serials)


def import_stock(container, user, upload):
    if not upload or upload.size > settings.MAX_UPLOAD_SIZE:
        raise ValueError("Select a STOCK_SERIAL_SCANNING.CSV within the upload size limit.")
    if FirstScanSession.objects.filter(container=container, status__in=["ACTIVE", "PAUSED"]).exists():
        raise ValueError("Finish First Scan before importing Second Scan stock.")
    received = ImportBatch.objects.filter(source_file__container=container, source_file__kind="RECEIVED", status="CONFIRMED").first()
    moves = ProductMovesImport.objects.filter(container=container, active=True).first()
    if not received or not moves:
        raise ValueError("Confirm First Scan and reconcile this container's PRODUCT_MOVES first.")
    movement_rows = list(moves.rows.values("source_row", "product", "movement"))
    received_counts = Counter()
    for code, quantity in received.lines.values_list("code", "quantity"):
        received_counts[clean(code)] += quantity
    if not movement_rows or received_counts != Counter(clean(r["product"]) for r in movement_rows):
        raise ValueError("First Scan and PRODUCT_MOVES must reconcile before Second Scan.")
    data = upload.read()
    rows, known_serials = parse_stock(data, {r["movement"]: r["product"] for r in movement_rows})
    session, _ = SecondScanSession.objects.get_or_create(container=container, defaults={"created_by": user})
    if session.finished_at:
        raise ValueError("Second Scan is finished; its stock snapshot is locked.")
    if session.pending_movement_id:
        raise ValueError("Complete or cancel the pending bike before updating stock.")
    existing = {row.movement: row for row in container.second_scan_movements.all()}
    if any(row.completed_at and key not in rows for key, row in existing.items()):
        raise ValueError("Updated stock must preserve all completed movements.")
    # Validate every row before modifying the snapshot. Completed bikes are immutable.
    for key, row in rows.items():
        old = existing.get(key)
        if old and old.completed_at and any(getattr(old, f) != row[f] for f in ("expected_product", "source_location", "wh_loc", "long_sku")):
            raise ValueError(f"Updated stock changes verified Movement {key}; review in Translogic.")
    for key, row in rows.items():
        old = existing.get(key)
        if not old or not old.completed_at:
            SecondScanMovement.objects.update_or_create(container=container, movement=key, defaults={k: v for k, v in row.items() if k != "movement"})
    container.second_scan_movements.filter(completed_at__isnull=True).exclude(movement__in=rows).delete()
    session.known_serials = known_serials
    session.imported_at = timezone.now()
    session.source_name = str(upload.name)[:255]
    session.source_sha256 = hashlib.sha256(data).hexdigest()
    session.save()
    return session


def state(session):
    rows = session.container.second_scan_movements
    completed = rows.filter(completed_at__isnull=False)
    pending = session.pending_movement
    if session.finished_at:
        phase = "FINISHED"
    elif pending:
        phase = "WAITING_SERIAL" if session.product_verified_at else "WAITING_PRODUCT"
    else:
        phase = "WAITING_MOVEMENT" if session.current_location else "WAITING_LOCATION"
    return {
        "location": session.current_location, "scanned": completed.count(), "total": rows.count(),
        "phase": phase, "movement": pending.movement if pending else "",
        "expected_product": pending.expected_product if pending else "",
        "bike_location": session.pending_location,
        "recent": list(completed.order_by("-completed_at", "-id").values("movement", "product_code", "serial", "location")[:20]),
    }


def clear_pending(session):
    session.pending_movement = None
    session.pending_location = ""
    session.movement_scanned_at = None
    session.product_verified_at = None


def scan(session, value, user):
    raw_value = str(value or "").strip()
    value = clean(raw_value)
    if session.finished_at:
        raise ValueError("Second Scan is finished.")
    if not value:
        raise ValueError("Empty barcode / Serial is not allowed.")
    if LOCATION.fullmatch(value):
        session.current_location = value
        session.save()
        return f"Current Location = {value}."
    if not session.current_location:
        raise ValueError("Scan Location first (AA010).")
    pending = session.pending_movement
    if not pending:
        pending = session.container.second_scan_movements.filter(movement=value).first()
        if not pending:
            raise ValueError("Movement Number not found for this container — REVIEW.")
        if pending.completed_at:
            raise ValueError("Movement Number already completed.")
        # A warehouse location may differ from the pallet reference in Translogic.
        # When the source itself uses AA010 format, retain the workbook location check.
        if LOCATION.fullmatch(pending.source_location) and pending.source_location != session.current_location:
            raise ValueError(f"Location mismatch: expected {pending.source_location}.")
        session.pending_movement = pending
        session.pending_location = session.current_location
        session.movement_scanned_at = timezone.now()
        session.product_verified_at = None
        session.save()
        return "Movement found. Scan physical Product Code."
    if not session.product_verified_at:
        if value != pending.expected_product:
            raise ValueError("LABEL / BIKE MISMATCH — STOP. Scan the matching physical Product before Serial.")
        session.product_verified_at = timezone.now()
        session.save()
        return "Product verified. Scan Serial Number."
    if len(value) > 160:
        raise ValueError("Serial exceeds the supported storage length.")
    if value in {pending.expected_product, pending.long_sku, "D" + pending.expected_product} or "D" + value == pending.expected_product:
        raise ValueError("Serial cannot be Product Code or Long Code.")
    export_serial = value[-16:]
    if (value in session.known_serials or export_serial in {serial[-16:] for serial in session.known_serials}
            or SecondScanMovement.objects.exclude(serial="").filter(serial__iendswith=export_serial).exists()):
        raise ValueError("Serial is duplicated or already exists in Translogic.")
    # The session lock serializes scans for this container; the DB serial constraint
    # additionally protects simultaneous completions in different PON containers.
    try:
        with transaction.atomic():
            pending.product_code = pending.expected_product
            pending.serial = raw_value
            pending.location = session.pending_location
            pending.movement_scanned_at = session.movement_scanned_at
            pending.product_verified_at = session.product_verified_at
            pending.completed_at = timezone.now()
            pending.scanned_by = user
            pending.save()
    except IntegrityError as exc:
        raise ValueError("Serial was already registered; review before retrying.") from exc
    clear_pending(session)
    session.save()
    return "Bike complete. Scan next Movement Number."


@login_required
@transaction.atomic
def scanner(request, pk):
    containers = Container.objects.select_related("customer")
    container = get_object_or_404(containers.select_for_update(of=("self",)) if request.method == "POST" else containers, pk=pk, customer__code__iexact="PON")
    session = SecondScanSession.objects.filter(container=container).select_related("pending_movement").first()
    error = ""
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "import":
                # Roll back all import writes on a validation failure.
                with transaction.atomic():
                    session = import_stock(container, request.user, request.FILES.get("file"))
            else:
                if not session or not session.imported_at:
                    raise ValueError("Import STOCK_SERIAL_SCANNING.CSV before scanning.")
                if action == "scan":
                    message = scan(session, request.POST.get("barcode"), request.user)
                elif action == "cancel" and not session.finished_at:
                    clear_pending(session)
                    session.save()
                    message = "Pending bike cancelled; no Serial recorded."
                elif action == "finish":
                    if session.pending_movement_id or container.second_scan_movements.filter(completed_at__isnull=True).exists():
                        raise ValueError("Complete every Movement before finishing Second Scan.")
                    wh_locations = {}
                    for location, wh_loc in container.second_scan_movements.exclude(wh_loc="").values_list("location", "wh_loc"):
                        if location in wh_locations and wh_locations[location] != wh_loc:
                            raise ValueError("Conflicting WH_LOC for the same Location; review stock before finishing.")
                        wh_locations[location] = wh_loc
                    session.finished_at = session.finished_at or timezone.now()
                    session.save()
                    message = "Second Scan complete. CSV downloads ready."
                else:
                    raise ValueError("Invalid Second Scan action.")
                return JsonResponse({"ok": True, "message": message, "state": state(session)})
        except ValueError as exc:
            error = str(exc)
            if action != "import":
                return JsonResponse({"ok": False, "message": error, "state": state(session) if session else None}, status=400)
            session = SecondScanSession.objects.filter(container=container).select_related("pending_movement").first()
    return render(request, "receiving/second_scan_scanner.html", {"container": container, "session": session, "scan_state": state(session) if session else None, "error": error})


@login_required
def download(request, pk, kind):
    session = get_object_or_404(SecondScanSession.objects.select_related("container__customer"), container_id=pk, container__customer__code__iexact="PON")
    if kind not in ("serial", "locations") or not session.finished_at:
        return HttpResponse("Finish Second Scan before downloading.", status=409)
    rows = list(session.container.second_scan_movements.all())
    if not rows or any(not r.completed_at or not r.product_verified_at or r.product_code != r.expected_product or not r.serial or not r.location for r in rows):
        return HttpResponse("Second Scan contains incomplete or unverified bikes.", status=409)
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    if kind == "serial":
        writer.writerow(["Mov (10Ch)", "Serial", "Location"])
        for row in sorted(rows, key=lambda r: int(r.movement)):
            writer.writerow([row.movement.rjust(10), row.serial[-16:], row.location])
        filename = "UPSTOCKSERIALSCAN.CSV"
    else:
        writer.writerow(["code", "name"])
        locations = {}
        for row in rows:
            if row.wh_loc:
                if row.location in locations and locations[row.location] != row.wh_loc:
                    return HttpResponse("Conflicting WH_LOC for the same Location; review Translogic stock.", status=409)
                locations[row.location] = row.wh_loc
        writer.writerows(sorted(locations.items()))
        filename = "UPWHLOCSSCAN.CSV"
    response = HttpResponse(output.getvalue().encode("utf-8"), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
