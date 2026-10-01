from pathlib import Path
from datetime import datetime
import hashlib
import io
import json
import ntpath
from types import SimpleNamespace

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.serializers.json import DjangoJSONEncoder
from django.core.files import File
from django.core.files.base import ContentFile
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse
from openpyxl.utils import get_column_letter

from .forms import (
    ContainerForm,
    ImportMappingForm,
    ProductCatalogUploadForm,
    ProductDefinitionForm,
    ProductMovesUploadForm,
    SourceUploadForm,
)
from .models import (
    AppSetting,
    Container,
    ContainerProductStatus,
    Customer,
    GeneratedExport,
    Group1Family,
    ImportBatch,
    ImportProfile,
    NormalizedLine,
    ProductCatalog,
    ProductCatalogEntry,
    ProductDefinition,
    ProductMovesImport,
    ProductMovement,
    SourceFile,
)
from .services import (
    PRODUCT_CATALOG_PATTERN,
    EXPORT_DEFAULTS,
    analyse_workbook_mapping,
    available_server_files,
    build_product_check_workbook,
    build_new_product_workbook,
    build_name_dictionary,
    build_client_receiving_workbook,
    build_client_report_rows,
    build_upstockserial_csv,
    classify_product_codes,
    compare_products_to_catalog,
    compare_lines,
    convert_excel_output,
    file_sha256,
    inspect_workbook,
    parse_product_catalog,
    pbp_to_pon_product_data,
    parse_product_moves_csv,
    parse_workbook,
    path_sha256,
    product_check_summary,
    reconcile_product_movements,
    normalize_container_identifier,
    resolve_group1_family,
    resolve_server_file,
    suggest_mapping,
    suggest_translogic_name,
)
from .translogic_transfer import copy_file_verified, discover_numbered_import_set, sha256_file


def _export_configuration():
    descriptions = {
        "TL_EXPORT_FORMAT": "excel_5_95 or xlsx. Applies only to files imported into Translogic; printable barcode reports always use xlsx so embedded images remain visible.",
        "TL_CUSTOMER": "Fixed Customer value in New Product Import.",
        "TL_STATUS": "Fixed Status value in New Product Import.",
        "TL_GROUP2_CUBIC_THRESHOLD": "Cubic threshold for the special Group2.",
        "TL_GROUP2_LARGE": "Group2 when Cubic is greater than the threshold.",
        "TL_GROUP2_DEFAULT": "Group2 when Cubic is not greater than the threshold.",
        "TL_QUANTITY": "Fixed Quantity value in New Product Import.",
        "TL_PALLET": "Fixed Pallet value in New Product Import.",
        "TL_LIFT": "Fixed Lift value in New Product Import.",
        "TL_OUTER": "Fixed Outer value in New Product Import.",
    }
    existing = {item.key: item.value for item in AppSetting.objects.filter(key__in=EXPORT_DEFAULTS)}
    missing = [
        AppSetting(key=key, value=value, description=descriptions[key])
        for key, value in EXPORT_DEFAULTS.items()
        if key not in existing
    ]
    if missing:
        AppSetting.objects.bulk_create(missing, ignore_conflicts=True)
    return {
        key: AppSetting.objects.filter(key=key).values_list("value", flat=True).first() or default
        for key, default in EXPORT_DEFAULTS.items()
    }


def _store_export(container, user, kind, filename, file_format, content, row_count):
    record = GeneratedExport(
        container=container,
        kind=kind,
        original_name=filename,
        file_format=file_format,
        row_count=row_count,
        sha256=hashlib.sha256(content).hexdigest(),
        generated_by=user,
    )
    record.file.save(filename, ContentFile(content), save=False)
    record.save()
    return record


def _configured_root():
    setting = AppSetting.objects.filter(key="PON_CONTAINER_ROOT").first()
    return setting.value if setting and setting.value else settings.PON_CONTAINER_ROOT


def _configured_product_catalog_path():
    setting = AppSetting.objects.filter(key="PON_PRODUCT_CATALOG_PATH").first()
    if setting and setting.value:
        # Do not let a persisted legacy CSV override keep the upgraded app on the old source.
        if not str(setting.value).upper().endswith("PRODUCTS_PON_PBP.CSV"):
            return setting.value
    return settings.PON_PRODUCT_CATALOG_PATH


def _customer_catalog_paths(customer):
    """Return operator/source and application-readable product-master paths for one customer."""
    source_path = (getattr(customer, "product_catalog_source_path", "") or "").strip()
    app_path = (getattr(customer, "product_catalog_app_path", "") or "").strip()
    # Backward-compatible default for the existing shared PON/PBP catalogue.
    if customer and customer.code.upper() in {"PON", "PBP"}:
        source_path = source_path or settings.PON_PRODUCT_CATALOG_SOURCE_DISPLAY
        app_path = app_path or _configured_product_catalog_path()
    filename_source = source_path or app_path
    filename = ntpath.basename(filename_source.replace("/", "\\")) if filename_source else "Not configured"
    return {
        "source_path": source_path,
        "app_path": app_path,
        "filename": filename,
        "available": bool(app_path and Path(app_path).is_file()),
    }


def _active_catalog_for_customer(customer):
    if not customer:
        return None
    catalog = ProductCatalog.objects.filter(active=True, customer=customer).first()
    if catalog:
        return catalog
    # Current PON/PBP operations may share one product master until PBP receives its own config.
    if customer.code.upper() == "PBP":
        shared = ProductCatalog.objects.filter(active=True, customer__code="PON").first()
        if shared:
            return shared
    # Compatibility for data imported before catalogues became customer-specific.
    return ProductCatalog.objects.filter(active=True, customer__isnull=True).first()




def _known_product_codes_for_customer(customer):
    catalog = _active_catalog_for_customer(customer)
    if not catalog:
        return set()
    codes = set()
    for code, pon_sku, code2 in ProductCatalogEntry.objects.filter(catalog=catalog).values_list("code", "pon_sku", "code2"):
        for value in (code, pon_sku, code2):
            if value:
                codes.add(str(value).strip().upper().replace(" ", ""))
    return codes


def _source_mapping_analysis(source):
    profiles = list(ImportProfile.objects.filter(
        customer=source.container.customer,
        kind=source.kind,
        active=True,
    ).order_by("-created_at"))
    return analyse_workbook_mapping(
        source.file.path,
        source.kind,
        known_product_codes=_known_product_codes_for_customer(source.container.customer),
        saved_profiles=profiles,
    )


def _container_preview_groups(batch):
    groups = {}
    for line in batch.lines.all().order_by("source_row"):
        identifier = line.container_identifier or ""
        if not identifier:
            continue
        group = groups.setdefault(identifier, {"identifier": identifier, "rows": 0, "units": 0})
        group["rows"] += 1
        group["units"] += line.quantity
    current = normalize_container_identifier(batch.container.identifier)
    result = []
    for identifier in sorted(groups):
        item = groups[identifier]
        item["is_current"] = identifier == current
        existing = Container.objects.filter(identifier=identifier).first()
        item["exists"] = bool(existing)
        item["existing_status"] = existing.get_status_display() if existing else ""
        result.append(item)
    return result


def _confirm_multi_container_manifest(batch, user):
    """Split one confirmed client workbook into independent container-specific batches."""
    source = batch.source_file
    current_container = source.container
    current_identifier = normalize_container_identifier(current_container.identifier)
    groups = {}
    for line in list(batch.lines.all().order_by("source_row")):
        identifier = line.container_identifier or ""
        if identifier:
            groups.setdefault(identifier, []).append(line)

    if not groups:
        return {"created": [], "linked": [], "current_units": batch.total_units, "legacy_mismatch": ""}
    if current_identifier not in groups and len(groups) == 1:
        detected_identifier = next(iter(groups))
        batch.lines.update(container_identifier=current_identifier)
        return {"created": [], "linked": [], "current_units": batch.total_units, "legacy_mismatch": detected_identifier}
    if current_identifier not in groups:
        raise ValueError(
            f"This manifest contains {', '.join(sorted(groups))}, but not the current container {current_container.identifier}."
        )

    created = []
    linked = []
    current_lines = groups[current_identifier]
    batch.lines.exclude(pk__in=[line.pk for line in current_lines]).delete()
    batch.total_rows = len(current_lines)
    batch.total_units = sum(line.quantity for line in current_lines)
    batch.save(update_fields=["total_rows", "total_units"])
    current_container.manifest_source_name = source.original_name
    current_container.save(update_fields=["manifest_source_name"])

    for identifier, lines in sorted(groups.items()):
        if identifier == current_identifier:
            continue
        container, was_created = Container.objects.get_or_create(
            identifier=identifier,
            defaults={
                "customer": current_container.customer,
                "container_date": current_container.container_date,
                "year": current_container.year,
                "status": "PENDING",
                "job_order": "",
                "auto_created_from_manifest": True,
                "manifest_source_name": source.original_name,
                "created_by": user,
            },
        )
        if container.customer_id != current_container.customer_id:
            raise ValueError(
                f"Container {identifier} already exists for customer {container.customer.code}; it was not modified."
            )
        if not was_created and container.status == "CLOSED":
            raise ValueError(
                f"Container {identifier} is already Complete. Reopen it before replacing its client manifest."
            )
        changed = []
        if container.manifest_source_name != source.original_name:
            container.manifest_source_name = source.original_name
            changed.append("manifest_source_name")
        if was_created:
            created.append(identifier)
        else:
            linked.append(identifier)
        if changed:
            container.save(update_fields=changed)

        sibling_source, _ = SourceFile.objects.get_or_create(
            container=container,
            kind="CLIENT",
            sha256=source.sha256,
            defaults={
                "file": source.file.name,
                "original_name": source.original_name,
                "status": "CONFIRMED",
                "uploaded_by": user,
            },
        )
        sibling_source.file.name = source.file.name
        sibling_source.original_name = source.original_name
        sibling_source.status = "CONFIRMED"
        sibling_source.save(update_fields=["file", "original_name", "status"])
        ImportBatch.objects.filter(
            source_file__container=container,
            source_file__kind="CLIENT",
            status="CONFIRMED",
        ).update(status="SUPERSEDED")
        sibling_batch = ImportBatch.objects.create(
            source_file=sibling_source,
            status="CONFIRMED",
            mapping=batch.mapping,
            total_rows=len(lines),
            total_units=sum(line.quantity for line in lines),
            created_by=user,
            confirmed_at=timezone.now(),
        )
        NormalizedLine.objects.bulk_create([
            NormalizedLine(
                batch=sibling_batch,
                source_sheet=line.source_sheet,
                source_row=line.source_row,
                code=line.code,
                long_code=line.long_code,
                description=line.description,
                quantity=line.quantity,
                location=line.location,
                fill_signature=line.fill_signature,
                raw_data=line.raw_data,
                container_identifier=identifier,
            )
            for line in lines
        ])
    return {"created": created, "linked": linked, "current_units": batch.total_units, "legacy_mismatch": ""}


def _direct_product_moves_path():
    if not settings.PON_PRODUCT_MOVES_DIRECT_ENABLED:
        return None
    direct_path = Path(settings.PON_PRODUCT_MOVES_DIRECT_PATH)
    return direct_path if direct_path.is_file() else None


def _configured_product_moves_path():
    # Prefer the verified direct Translogic mount only while the real file is
    # currently readable. Otherwise retain the existing local bridge/fallback.
    direct_path = _direct_product_moves_path()
    if direct_path:
        return str(direct_path)
    setting = AppSetting.objects.filter(key="PON_PRODUCT_MOVES_PATH").first()
    if setting and setting.value:
        return setting.value
    return settings.PON_PRODUCT_MOVES_PATH


def _configured_upstockserial_path():
    setting = AppSetting.objects.filter(key="PON_UPSTOCKSERIAL_PATH").first()
    if setting and setting.value:
        return setting.value
    return settings.PON_UPSTOCKSERIAL_PATH


def _configured_client_report_dir():
    setting = AppSetting.objects.filter(key="PON_CLIENT_REPORT_DIR").first()
    if setting and setting.value:
        return setting.value
    return settings.PON_CLIENT_REPORT_DIR


def _direct_translogic_import_dir():
    if not settings.PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED:
        return None
    directory = Path(settings.PON_TRANSLOGIC_IMPORT_DIRECT_PATH)
    return directory if directory.is_dir() else None


def _windows_destination_for(filename):
    configured = str(settings.PON_UPSTOCK_FINAL_DISPLAY or "").strip()
    if not configured:
        return filename
    directory = ntpath.dirname(configured)
    return ntpath.join(directory, filename) if directory else filename


def _local_datetime(timestamp):
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.get_current_timezone())


def _transfer_audit_path(container):
    directory = Path(settings.MEDIA_ROOT) / "translogic_transfer_audit"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"container_{container.pk}.jsonl"


def _record_transfer_audit(container, user, kind, source, destination, result, replaced_name=""):
    record = {
        "timestamp": timezone.localtime().isoformat(),
        "kind": kind,
        "container": container.identifier,
        "user_id": user.pk,
        "source": str(source),
        "destination": str(destination),
        "replaced": bool(result.get("replaced")),
        "replaced_name": replaced_name,
        "sha256": result.get("destination_sha256", ""),
        "size": result.get("size", 0),
        "result": "verified",
    }
    with _transfer_audit_path(container).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def _latest_transfer_audit(container, kind):
    path = Path(settings.MEDIA_ROOT) / "translogic_transfer_audit" / f"container_{container.pk}.jsonl"
    if not path.is_file():
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except (TypeError, ValueError):
            continue
        if record.get("kind") == kind:
            try:
                record["timestamp_dt"] = datetime.fromisoformat(record.get("timestamp", ""))
            except (TypeError, ValueError):
                record["timestamp_dt"] = None
            return record
    return None


def _upstock_transfer_status(container):
    source_path = Path(_configured_upstockserial_path())
    direct_dir = _direct_translogic_import_dir()
    destination_path = direct_dir / "UPStockSerial.csv" if direct_dir else None
    latest = container.generated_exports.filter(kind="UPSTOCK_SERIAL").first()
    received_batch, moves_import, reconciliation = _stage2_data(container)
    stale = _export_stale(
        latest,
        getattr(received_batch, "confirmed_at", None),
        getattr(moves_import, "imported_at", None),
    )
    if container.status == "CLOSED":
        stale = False
    current_ready = bool(latest and not stale and reconciliation and reconciliation.get("ready"))
    source_matches = False
    source_hash = ""
    if latest and source_path.is_file():
        try:
            source_hash = sha256_file(source_path)
            source_matches = source_hash == latest.sha256
        except OSError:
            source_matches = False
    destination_exists = bool(destination_path and destination_path.is_file())
    destination_modified = None
    if destination_exists:
        try:
            destination_modified = _local_datetime(destination_path.stat().st_mtime)
        except OSError:
            destination_modified = None
    if not settings.PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED:
        reason = "Direct Translogic destination was not verified by the installer; the existing Download/manual transfer flow remains active."
    elif not direct_dir:
        reason = "The verified Translogic destination mount is currently unavailable to PON."
    elif not latest:
        reason = "Download/review the current UPStockSerial file before copying it to Translogic."
    elif not current_ready:
        reason = "The stored UPStockSerial is not current against the confirmed First Scan / PRODUCT_MOVES reconciliation. Download the current file before transfer."
    elif not source_path.is_file():
        reason = "The reviewed UPStockSerial working file is not currently present in the configured source path."
    elif not source_matches:
        reason = "The working UPStockSerial file does not match the latest generated PON audit copy; download it again before transfer."
    else:
        reason = ""
    return {
        "direct_enabled": bool(settings.PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED),
        "destination_accessible": bool(direct_dir),
        "source_path": source_path,
        "source_display": settings.PON_UPSTOCK_WORKING_DISPLAY,
        "source_exists": source_path.is_file(),
        "source_matches_latest": source_matches,
        "source_sha256": source_hash,
        "destination_path": destination_path,
        "destination_display": settings.PON_UPSTOCK_FINAL_DISPLAY,
        "destination_exists": destination_exists,
        "destination_modified": destination_modified,
        "latest": latest,
        "can_copy": bool(direct_dir and current_ready and source_path.is_file() and source_matches),
        "current_ready": current_ready,
        "reason": reason,
        "last_transfer": _latest_transfer_audit(container, "UPSTOCK_SERIAL"),
    }


def _new_product_transfer_status(container):
    latest = container.generated_exports.filter(kind="NEW_PRODUCT").first()
    direct_dir = _direct_translogic_import_dir()
    discovery = discover_numbered_import_set(direct_dir) if direct_dir else {
        "available": False, "pattern": "", "extension": "", "files": [], "oldest": None,
        "reason": "The Translogic import directory is not directly accessible to PON."
    }
    expected_extension = Path(latest.original_name).suffix.lower() if latest else ""
    format_matches = bool(latest and discovery.get("available") and expected_extension == discovery.get("extension", "").lower())
    oldest = discovery.get("oldest")
    if oldest:
        oldest = dict(oldest)
        oldest["modified_at"] = _local_datetime(oldest.get("mtime"))
    files = []
    for item in discovery.get("files", []):
        row = dict(item)
        row["modified_at"] = _local_datetime(row.get("mtime"))
        files.append(row)
    if not settings.PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED:
        reason = "Direct Translogic import-folder access was not verified by the installer; existing Download remains available."
    elif not direct_dir:
        reason = "The verified Translogic import mount is currently unavailable to PON."
    elif not discovery.get("available"):
        reason = discovery.get("reason") or "The real numbered Translogic file pattern could not be identified safely."
    elif not latest:
        reason = "Download and review New Product Import first; PON will never create a replacement file automatically."
    elif not format_matches:
        reason = (
            f"Format mismatch: PON generated {expected_extension or 'an unknown extension'}, but the real Translogic numbered files use "
            f"{discovery.get('extension') or 'an unknown extension'}. No conversion or replacement will be attempted."
        )
    else:
        reason = ""
    return {
        "direct_enabled": bool(settings.PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED),
        "destination_accessible": bool(direct_dir),
        "latest": latest,
        "pattern": discovery.get("pattern", ""),
        "extension": discovery.get("extension", ""),
        "expected_extension": expected_extension,
        "files": files,
        "oldest": oldest,
        "format_matches": format_matches,
        "can_copy": bool(direct_dir and latest and discovery.get("available") and format_matches and oldest),
        "reason": reason,
        "last_transfer": _latest_transfer_audit(container, "NEW_PRODUCT"),
    }


def _workflow_redirect(request, pk, default_name, anchor=""):
    """Return to the guided container workflow when an action originated there."""
    if request.POST.get("return_to") == "workspace":
        url = reverse("receiving:container_detail", args=[pk])
        if anchor:
            url += f"#{anchor}"
        return redirect(url)
    return redirect(default_name, pk=pk)


def _export_stale(export, *timestamps):
    if not export:
        return False
    return any(timestamp and export.generated_at < timestamp for timestamp in timestamps)


def _filename_mentions_container(filename, container_identifier):
    """Return True when a filename visibly includes the current Container ID.

    This is only an operator aid. A filename mismatch must never block a file
    that passes the existing workbook/content validation.
    """
    expected = "".join(ch for ch in str(container_identifier or "").upper() if ch.isalnum())
    candidate = "".join(ch for ch in Path(str(filename or "")).stem.upper() if ch.isalnum())
    return bool(expected and expected in candidate)


def _closed_container_guard(request, container):
    if container.status != "CLOSED":
        return None
    messages.warning(
        request,
        f"Container {container.identifier} is Complete. Reopen it from the workflow before changing source data or refreshing downloadable outputs.",
    )
    return redirect("receiving:container_detail", pk=container.pk)


def _activate_product_moves(container, user, content, original_name="PRODUCT_MOVES.CSV", source_path=""):
    rows = parse_product_moves_csv(io.BytesIO(content))
    digest = hashlib.sha256(content).hexdigest()
    existing = ProductMovesImport.objects.filter(container=container, sha256=digest).first()
    with transaction.atomic():
        ProductMovesImport.objects.filter(container=container, active=True).exclude(pk=getattr(existing, "pk", None)).update(active=False)
        if existing:
            record = existing
            record.active = True
            record.source_path = source_path or record.source_path
            record.row_count = len(rows)
            record.imported_by = user
            if not record.file:
                record.file.save(original_name, ContentFile(content), save=False)
            record.save()
            if not record.rows.exists():
                ProductMovement.objects.bulk_create(
                    [ProductMovement(import_batch=record, **row) for row in rows]
                )
        else:
            record = ProductMovesImport(
                container=container,
                original_name=original_name,
                source_path=source_path,
                sha256=digest,
                row_count=len(rows),
                active=True,
                imported_by=user,
            )
            record.file.save(original_name, ContentFile(content), save=False)
            record.save()
            ProductMovement.objects.bulk_create(
                [ProductMovement(import_batch=record, **row) for row in rows]
            )
    return record



def _client_report_data(container):
    client_batch = ImportBatch.objects.filter(
        source_file__container=container,
        source_file__kind="CLIENT",
        status="CONFIRMED",
    ).first()
    received_batch = ImportBatch.objects.filter(
        source_file__container=container,
        source_file__kind="RECEIVED",
        status="CONFIRMED",
    ).first()
    catalog = _active_catalog_for_customer(container.customer)
    rows = []
    if client_batch and received_batch and catalog:
        codes = {
            str(code or "").strip().upper()
            for code in list(client_batch.lines.values_list("code", flat=True))
            + list(received_batch.lines.values_list("code", flat=True))
            if str(code or "").strip()
        }
        definitions = ProductDefinition.objects.filter(code__in=codes)
        status_rows = {item.code: item.was_new for item in container.product_statuses.filter(code__in=codes)}
        catalog_entries = list(catalog.entries.all())
        classifications = classify_product_codes(codes, catalog_entries, target_customer=container.customer.code)
        rows = build_client_report_rows(
            client_batch.lines.all(),
            received_batch.lines.all(),
            catalog_entries,
            definitions,
            product_statuses=status_rows,
            product_classifications=classifications,
            target_customer=container.customer.code,
        )
    return client_batch, received_batch, catalog, rows


def _stage2_data(container):
    received_batch = ImportBatch.objects.filter(
        source_file__container=container,
        source_file__kind="RECEIVED",
        status="CONFIRMED",
    ).first()
    moves_import = ProductMovesImport.objects.filter(container=container, active=True).first()
    reconciliation = None
    if received_batch and moves_import:
        movement_rows = list(moves_import.rows.values("source_row", "product", "movement"))
        reconciliation = reconcile_product_movements(received_batch.lines.all(), movement_rows)
    return received_batch, moves_import, reconciliation


def _container_workspace_data(container):
    """Build the compact, guided status used by the single container workflow page."""
    client_batch = ImportBatch.objects.filter(
        source_file__container=container, source_file__kind="CLIENT", status="CONFIRMED"
    ).select_related("source_file").first()
    received_batch = ImportBatch.objects.filter(
        source_file__container=container, source_file__kind="RECEIVED", status="CONFIRMED"
    ).select_related("source_file").first()

    comparison_rows = compare_lines(
        client_batch.lines.all() if client_batch else [],
        received_batch.lines.all() if received_batch else [],
    )
    expected_units = sum(row["expected"] for row in comparison_rows)
    received_units = sum(row["received"] for row in comparison_rows)
    variance = received_units - expected_units
    exception_count = sum(1 for row in comparison_rows if row["status"] != "MATCH")

    catalog, _, product_rows, product_summary = _persisted_product_check_data(container, received_batch)
    import_rows = _original_import_rows(container, product_rows, recover=False)
    new_codes = sorted({row["code"] for row in import_rows if row["is_new"]})
    migration_rows_by_code = {
        row["code"]: row for row in import_rows if row.get("is_pbp_to_pon")
    }
    _prefer_current_pon_data(catalog, migration_rows_by_code)
    migration_rows = list(migration_rows_by_code.values())
    migration_codes = sorted(migration_rows_by_code)
    definition_required_codes = sorted(
        set(new_codes)
        | {row["code"] for row in migration_rows if not (row.get("pbp_to_pon_data") or {}).get("valid")}
    )
    definitions = {
        item.code: item
        for item in ProductDefinition.objects.filter(code__in=definition_required_codes, confirmed=True)
    }
    pending_new_codes = [code for code in definition_required_codes if code not in definitions]
    group1_rules = list(Group1Family.objects.filter(active=True).order_by("-priority", "family_name"))
    migration_group1_ready = all(
        resolve_group1_family(
            (row.get("pbp_to_pon_data") or {}).get("long_name")
            or getattr(definitions.get(row["code"]), "full_name", ""),
            "PON",
            group1_rules,
        ).get("resolved")
        for row in migration_rows
        if (row.get("pbp_to_pon_data") or {}).get("valid") or definitions.get(row["code"])
    )
    classified_codes = {row["code"] for row in product_rows if row.get("classification")}
    received_codes = {code.strip().upper() for code in received_batch.lines.values_list("code", flat=True)} if received_batch else set()
    products_ready = bool(received_batch and catalog and received_codes.issubset(classified_codes) and not pending_new_codes and migration_group1_ready)

    product_check_download_ready = bool(catalog and received_batch)
    new_product_import_download_ready = False
    import_codes_present = bool(new_codes or migration_codes)
    if container.container_date and product_check_download_ready and import_codes_present and not pending_new_codes:
        tl_customer = (
            AppSetting.objects.filter(key="TL_CUSTOMER").values_list("value", flat=True).first()
            or EXPORT_DEFAULTS["TL_CUSTOMER"]
        )
        normal_new_group1_ready = all(
            resolve_group1_family(definitions[code].full_name, tl_customer, group1_rules).get("resolved")
            for code in new_codes
        )
        new_product_import_download_ready = normal_new_group1_ready and migration_group1_ready

    stage2_received, moves_import, reconciliation = _stage2_data(container)
    moves_product_count = 0
    if moves_import:
        moves_product_count = moves_import.rows.values("product").distinct().count()

    latest_product_check = container.generated_exports.filter(kind="PRODUCT_CHECK").first()
    latest_new_product_import = container.generated_exports.filter(kind="NEW_PRODUCT").first()
    latest_upstock = container.generated_exports.filter(kind="UPSTOCK_SERIAL").first()
    latest_report = container.generated_exports.filter(kind="CLIENT_REPORT").first()

    upstock_stale = _export_stale(
        latest_upstock,
        getattr(stage2_received, "confirmed_at", None),
        getattr(moves_import, "imported_at", None),
    )

    newest_definition = None
    if definition_required_codes:
        newest_definition = ProductDefinition.objects.filter(code__in=definition_required_codes).order_by("-updated_at").first()
    report_stale = _export_stale(
        latest_report,
        getattr(client_batch, "confirmed_at", None),
        getattr(received_batch, "confirmed_at", None),
        getattr(catalog, "uploaded_at", None),
        getattr(newest_definition, "updated_at", None),
    )

    # A completed container is an historical snapshot. Global catalogue/name changes
    # made for later containers must not make its already-approved outputs look stale.
    # Reopening the container turns live dependency checks back on.
    if container.status == "CLOSED":
        upstock_stale = False
        report_stale = False

    upstock_ready = bool(latest_upstock and not upstock_stale and reconciliation and reconciliation.get("ready"))
    report_ready = bool(latest_report and not report_stale)
    step1_complete = bool(client_batch and received_batch)
    step2_complete = bool(step1_complete and products_ready)
    step3_complete = bool(step2_complete and upstock_ready)
    ready_to_complete = bool(step3_complete and report_ready)

    if container.status == "CLOSED":
        current_step = 4
    elif not step1_complete:
        current_step = 1
    elif not step2_complete:
        current_step = 2
    elif not step3_complete:
        current_step = 3
    else:
        current_step = 4

    client_source = (
        getattr(client_batch, "source_file", None)
        if client_batch
        else container.source_files.filter(kind="CLIENT").first()
    )
    received_source = (
        getattr(received_batch, "source_file", None)
        if received_batch
        else container.source_files.filter(kind="RECEIVED").first()
    )

    upstock_transfer = _upstock_transfer_status(container)
    new_product_transfer = _new_product_transfer_status(container)
    direct_moves = _direct_product_moves_path()

    return {
        "client_batch": client_batch,
        "received_batch": received_batch,
        "client_source": client_source,
        "received_source": received_source,
        "expected_units": expected_units,
        "received_units": received_units,
        "variance": variance,
        "exception_count": exception_count,
        "catalog": catalog,
        "product_rows": product_rows,
        "product_summary": product_summary,
        "new_product_count": len(new_codes),
        "pbp_to_pon_count": len(migration_codes),
        "pending_new_codes": pending_new_codes,
        "products_ready": products_ready,
        "product_check_download_ready": product_check_download_ready,
        "new_product_import_download_ready": new_product_import_download_ready,
        "moves_import": moves_import,
        "reconciliation": reconciliation,
        "moves_product_count": moves_product_count,
        "latest_product_check": latest_product_check,
        "latest_new_product_import": latest_new_product_import,
        "latest_upstock": latest_upstock,
        "latest_report": latest_report,
        "upstock_stale": upstock_stale,
        "report_stale": report_stale,
        "upstock_ready": upstock_ready,
        "report_ready": report_ready,
        "upstock_download_ready": bool(stage2_received and moves_import and reconciliation and reconciliation.get("ready")),
        "report_download_ready": bool(client_batch and received_batch and catalog),
        "step1_complete": step1_complete,
        "step2_complete": step2_complete,
        "step3_complete": step3_complete,
        "ready_to_complete": ready_to_complete,
        "current_step": current_step,
        "product_moves_available": Path(_configured_product_moves_path()).is_file(),
        "product_moves_direct": bool(direct_moves),
        "product_moves_refresh_mode": "Direct Translogic source" if direct_moves else "Local working copy fallback",
        "upstock_parent_available": Path(_configured_upstockserial_path()).parent.exists(),
        "upstock_transfer": upstock_transfer,
        "new_product_transfer": new_product_transfer,
        "report_dir_available": Path(_configured_client_report_dir()).exists(),
        "paths": {
            "moves_source": settings.PON_PRODUCT_MOVES_SOURCE_DISPLAY,
            "moves_working": settings.PON_PRODUCT_MOVES_WORKING_DISPLAY,
            "upstock_working": settings.PON_UPSTOCK_WORKING_DISPLAY,
            "upstock_final": settings.PON_UPSTOCK_FINAL_DISPLAY,
            "report_working": settings.PON_CLIENT_REPORT_WORKING_DISPLAY,
            "report_final": settings.PON_CLIENT_REPORT_FINAL_DISPLAY,
        },
    }



def _recent_container_rows(limit=20, active_container=None):
    """Return the shared Recent Containers sidebar data used by dashboard and container detail."""
    recent_containers = list(Container.objects.select_related("customer").all()[:limit])
    if active_container and all(item.pk != active_container.pk for item in recent_containers):
        recent_containers.insert(0, active_container)
    batches = ImportBatch.objects.filter(
        source_file__container_id__in=[item.pk for item in recent_containers],
        source_file__kind="CLIENT", status="CONFIRMED",
    ).select_related("source_file")
    by_container = {}
    for batch in batches:
        by_container.setdefault(batch.source_file.container_id, batch)
    recent_rows = []
    for recent_container in recent_containers:
        client_batch = by_container.get(recent_container.pk)
        recent_rows.append({
            "container": recent_container,
            "manifest_uploaded": bool(client_batch),
            "advised": client_batch.total_units if client_batch else 0,
            "manifest_name": client_batch.source_file.original_name if client_batch else recent_container.manifest_source_name,
        })
    return recent_containers, recent_rows

def _refresh_customer_product_checks(customer):
    """Persist classification during explicit master synchronization only."""
    containers = Container.objects.filter(
        customer=customer, source_files__kind="RECEIVED",
        source_files__batches__status="CONFIRMED",
    ).exclude(status="CLOSED").distinct().select_related("customer")
    for container in containers:
        _product_check_data(container)


def _activate_product_catalog(file_handle, original_name, digest, user, customer):
    existing = ProductCatalog.objects.filter(customer=customer, sha256=digest).first()
    if existing:
        ProductCatalog.objects.filter(customer=customer).exclude(pk=existing.pk).update(active=False)
        existing.active = True
        if not existing.name_dictionary:
            existing.name_dictionary = build_name_dictionary(
                existing.entries.only("long_name", "short_name")
            )
            existing.save(update_fields=["active", "name_dictionary"])
        else:
            existing.save(update_fields=["active"])
        existing.sync_short_name_rules()
        _refresh_customer_product_checks(customer)
        return existing, False

    catalog = ProductCatalog(
        customer=customer,
        original_name=original_name,
        sha256=digest,
        uploaded_by=user,
    )
    catalog.file.save(original_name, File(file_handle), save=True)
    try:
        parsed_rows = parse_product_catalog(catalog.file.path)
    except Exception:
        catalog.file.delete(save=False)
        catalog.delete()
        raise

    name_dictionary = build_name_dictionary(parsed_rows)
    with transaction.atomic():
        ProductCatalog.objects.filter(customer=customer).exclude(pk=catalog.pk).update(active=False)
        ProductCatalogEntry.objects.bulk_create(
            [ProductCatalogEntry(catalog=catalog, **row) for row in parsed_rows],
            batch_size=2000,
        )
        catalog.row_count = len(parsed_rows)
        catalog.name_dictionary = name_dictionary
        catalog.active = True
        catalog.save(update_fields=["row_count", "name_dictionary", "active"])
        catalog.sync_short_name_rules()
    _refresh_customer_product_checks(customer)
    return catalog, True


@login_required
def dashboard(request):
    if not Customer.objects.exists():
        Customer.objects.create(
            code="PON",
            name="Pon.Bike",
            product_catalog_source_path=settings.PON_PRODUCT_CATALOG_SOURCE_DISPLAY,
            product_catalog_app_path=_configured_product_catalog_path(),
        )

    customers = list(Customer.objects.order_by("name"))

    if request.method == "POST":
        form = ContainerForm(request.POST)
        if form.is_valid():
            container = form.save(commit=False)
            container.created_by = request.user
            container.save()
            messages.success(request, f"Container {container.identifier} created.")
            return redirect("receiving:container_detail", pk=container.pk)
    else:
        initial = {"container_date": timezone.localdate()}
        if customers:
            initial["customer"] = customers[0].pk
        form = ContainerForm(initial=initial)
    customer_catalogs = {}
    for customer in customers:
        paths = _customer_catalog_paths(customer)
        active_catalog = _active_catalog_for_customer(customer)
        customer_catalogs[str(customer.pk)] = {
            "code": customer.code,
            "name": customer.name,
            "filename": paths["filename"],
            "source_path": paths["source_path"],
            "app_path": paths["app_path"],
            "available": paths["available"],
            "active_name": active_catalog.original_name if active_catalog else "",
            "active_rows": active_catalog.row_count if active_catalog else 0,
            "active_loaded": timezone.localtime(active_catalog.uploaded_at).strftime("%d/%m/%Y %H:%M") if active_catalog else "",
        }

    recent_containers, recent_rows = _recent_container_rows()

    return render(
        request,
        "receiving/dashboard.html",
        {
            "form": form,
            "containers": recent_containers,
            "recent_rows": recent_rows,
            "customers": customers,
            "customer_catalogs": customer_catalogs,
            "catalog_form": ProductCatalogUploadForm(),
        },
    )


@login_required
def upload_product_catalog(request):
    if request.method != "POST":
        raise Http404
    customer_id = request.POST.get("customer_id")
    customer = Customer.objects.filter(pk=customer_id).first() if customer_id else None
    customer = customer or Customer.objects.filter(code__iexact="PON").first() or Customer.objects.first()
    if not customer:
        messages.error(request, "Configure a customer in Django Admin first.")
        return redirect("receiving:dashboard")
    form = ProductCatalogUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Select an Excel .xls product master file.")
        return redirect("receiving:dashboard")
    uploaded = request.FILES["file"]
    original_name = Path(uploaded.name).name
    if not PRODUCT_CATALOG_PATTERN.fullmatch(original_name):
        messages.error(request, "Only supported product-master files are accepted; use .xls for the current process.")
        return redirect("receiving:dashboard")
    if uploaded.size > settings.MAX_UPLOAD_SIZE:
        messages.error(request, "The product catalogue exceeds the configured upload size limit.")
        return redirect("receiving:dashboard")
    try:
        catalog, created = _activate_product_catalog(uploaded, original_name, file_sha256(uploaded), request.user, customer)
    except Exception as exc:
        messages.error(request, f"The product catalogue could not be imported: {exc}")
    else:
        action = "imported" if created else "already current and was reactivated"
        messages.success(request, f"{customer.code}: {catalog.original_name} {action}: {catalog.row_count} product row(s).")
    return redirect("receiving:dashboard")


@login_required
def sync_product_catalog(request):
    if request.method != "POST":
        raise Http404
    customer_id = request.POST.get("customer_id")
    customer = Customer.objects.filter(pk=customer_id).first() if customer_id else None
    customer = customer or Customer.objects.filter(code__iexact="PON").first() or Customer.objects.first()
    if not customer:
        messages.error(request, "Configure a customer in Django Admin first.")
        return redirect("receiving:dashboard")
    paths = _customer_catalog_paths(customer)
    path = Path(paths["app_path"]) if paths["app_path"] else None
    if not path or not PRODUCT_CATALOG_PATTERN.fullmatch(path.name) or not path.is_file():
        messages.error(request, f"The configured product master for {customer.code} is unavailable: {paths['app_path'] or 'not configured'}")
        return redirect("receiving:dashboard")
    try:
        with path.open("rb") as handle:
            catalog, created = _activate_product_catalog(handle, path.name, path_sha256(path), request.user, customer)
    except Exception as exc:
        messages.error(request, f"The product catalogue could not be synchronized: {exc}")
    else:
        action = "synchronized" if created else "has not changed"
        messages.success(request, f"{customer.code}: {catalog.original_name} {action}: {catalog.row_count} product row(s).")
    return redirect("receiving:dashboard")


@login_required
def container_detail(request, pk):
    container = get_object_or_404(Container.objects.select_related("customer"), pk=pk)
    server_files, server_available = available_server_files(_configured_root(), container.identifier)
    workspace = _container_workspace_data(container)
    recent_containers, recent_rows = _recent_container_rows(active_container=container)
    return render(
        request,
        "receiving/container_detail.html",
        {
            "container": container,
            "workspace": workspace,
            "upload_form": SourceUploadForm(),
            "moves_upload_form": ProductMovesUploadForm(),
            "source_files": container.source_files.prefetch_related("batches"),
            "server_files": server_files,
            "server_available": server_available,
            "configured_root": _configured_root(),
            "recent_containers": recent_containers,
            "recent_rows": recent_rows,
        },
    )


@login_required
def edit_container(request, pk):
    container = get_object_or_404(Container, pk=pk)
    form = ContainerForm(request.POST or None, instance=container)
    if request.method == "POST" and form.is_valid():
        updated = form.save()
        if updated.status == "PENDING" and updated.job_order:
            updated.status = "OPEN"
            updated.save(update_fields=["status"])
        messages.success(request, f"Container {updated.identifier} updated.")
        return redirect("receiving:container_detail", pk=updated.pk)
    return render(
        request,
        "receiving/simple_form.html",
        {"form": form, "title": f"Edit container {container.identifier}"},
    )


@login_required
def import_server_source(request, pk):
    container = get_object_or_404(Container, pk=pk)
    closed_redirect = _closed_container_guard(request, container)
    if closed_redirect:
        return closed_redirect
    if request.method != "POST":
        raise Http404
    relative_path = request.POST.get("relative_path", "")
    kind = request.POST.get("kind", "")
    if kind not in dict(SourceFile.KIND_CHOICES):
        messages.error(request, "Select a valid file type.")
        return redirect("receiving:container_detail", pk=pk)
    if kind == "RECEIVED" and not container.job_order:
        messages.error(request, "Assign a unique Job Order before starting the operational First Scan.")
        return redirect("receiving:container_detail", pk=pk)
    try:
        path = resolve_server_file(_configured_root(), relative_path)
    except (OSError, ValueError) as exc:
        messages.error(request, f"The server file could not be opened: {exc}")
        return redirect("receiving:container_detail", pk=pk)

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if SourceFile.objects.filter(container=container, kind=kind, sha256=digest).exists():
        messages.warning(request, "This exact server file has already been imported for this container and type.")
        return redirect("receiving:container_detail", pk=pk)

    with path.open("rb") as handle:
        source = SourceFile(
            container=container,
            kind=kind,
            original_name=path.name,
            sha256=digest,
            uploaded_by=request.user,
        )
        source.file.save(path.name, File(handle), save=True)
    messages.success(request, "A controlled copy of the server file was created. Review its mapping.")
    return redirect("receiving:configure_import", source_id=source.pk)


@login_required
def upload_source(request, pk):
    container = get_object_or_404(Container, pk=pk)
    closed_redirect = _closed_container_guard(request, container)
    if closed_redirect:
        return closed_redirect
    if request.method != "POST":
        raise Http404
    form = SourceUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Select an Excel .xlsx or .xlsm file and its type.")
        return redirect("receiving:container_detail", pk=pk)

    kind = form.cleaned_data["kind"]
    if kind == "RECEIVED" and not container.job_order:
        messages.error(request, "Assign a unique Job Order before starting the operational First Scan.")
        return redirect("receiving:container_detail", pk=pk)

    uploaded = request.FILES["file"]
    if uploaded.size > settings.MAX_UPLOAD_SIZE:
        messages.error(request, "The file exceeds the configured upload size limit.")
        return redirect("receiving:container_detail", pk=pk)
    if Path(uploaded.name).suffix.lower() not in {".xlsx", ".xlsm"}:
        messages.error(request, "This MVP accepts .xlsx and .xlsm files only.")
        return redirect("receiving:container_detail", pk=pk)

    digest = file_sha256(uploaded)
    if SourceFile.objects.filter(container=container, kind=kind, sha256=digest).exists():
        messages.warning(request, "This exact file has already been uploaded for this container and type.")
        return redirect("receiving:container_detail", pk=pk)

    source = form.save(commit=False)
    source.container = container
    source.original_name = uploaded.name
    source.sha256 = digest
    source.uploaded_by = request.user
    source.save()
    if not _filename_mentions_container(source.original_name, container.identifier):
        messages.warning(
            request,
            f"Filename does not contain the expected Container ID {container.identifier}. "
            "The upload was not blocked; confirm the detected mapping and workbook content before continuing.",
        )
    messages.success(request, "File uploaded. Review the detected mapping before confirming it.")
    return redirect("receiving:configure_import", source_id=source.pk)


@login_required
def stage2(request, pk):
    container = get_object_or_404(Container.objects.select_related("customer"), pk=pk)
    received_batch, moves_import, reconciliation = _stage2_data(container)
    product_moves_path = _configured_product_moves_path()
    upstock_path = _configured_upstockserial_path()
    product_moves_available = Path(product_moves_path).is_file()
    direct_moves = _direct_product_moves_path()
    upstock_parent_available = Path(upstock_path).parent.exists()
    latest_export = container.generated_exports.filter(kind="UPSTOCK_SERIAL").first()
    upstock_transfer = _upstock_transfer_status(container)
    client_batch, client_received_batch, client_report_catalog, client_report_rows = _client_report_data(container)
    latest_client_report = container.generated_exports.filter(kind="CLIENT_REPORT").first()
    return render(
        request,
        "receiving/stage2.html",
        {
            "container": container,
            "received_batch": received_batch,
            "moves_import": moves_import,
            "reconciliation": reconciliation,
            "product_moves_path": product_moves_path,
            "product_moves_available": product_moves_available,
            "product_moves_direct": bool(direct_moves),
            "product_moves_refresh_mode": "Direct Translogic source" if direct_moves else "Local working copy fallback",
            "moves_source_display": settings.PON_PRODUCT_MOVES_SOURCE_DISPLAY,
            "moves_working_display": settings.PON_PRODUCT_MOVES_WORKING_DISPLAY,
            "upstock_path": upstock_path,
            "upstock_parent_available": upstock_parent_available,
            "upstock_working_display": settings.PON_UPSTOCK_WORKING_DISPLAY,
            "upstock_final_display": settings.PON_UPSTOCK_FINAL_DISPLAY,
            "upload_form": ProductMovesUploadForm(),
            "latest_export": latest_export,
            "upstock_transfer": upstock_transfer,
            "stage2_exports": container.generated_exports.filter(kind="UPSTOCK_SERIAL")[:10],
            "client_report_inputs_ready": bool(client_batch and client_received_batch),
            "client_report_catalog_available": bool(client_report_catalog),
            "client_report_ready": bool(client_batch and client_received_batch and client_report_catalog),
            "client_report_rows": client_report_rows,
            "latest_client_report": latest_client_report,
            "client_report_exports": container.generated_exports.filter(kind="CLIENT_REPORT")[:10],
        },
    )


@login_required
@transaction.atomic
def sync_product_moves(request, pk):
    if request.method != "POST":
        raise Http404
    container = get_object_or_404(Container, pk=pk)
    closed_redirect = _closed_container_guard(request, container)
    if closed_redirect:
        return closed_redirect
    source_path = Path(_configured_product_moves_path())
    if not source_path.is_file():
        messages.error(
            request,
            "PRODUCT_MOVES.CSV is not visible from the configured source. The existing local working-copy/manual-upload fallback remains available.",
        )
        return _workflow_redirect(request, pk, "receiving:stage2", "translogic")
    try:
        content = source_path.read_bytes()
        record = _activate_product_moves(
            container,
            request.user,
            content,
            original_name=source_path.name,
            source_path=(settings.PON_PRODUCT_MOVES_SOURCE_DISPLAY if _direct_product_moves_path() else str(source_path)),
        )
    except (OSError, ValueError) as exc:
        messages.error(request, f"PRODUCT_MOVES.CSV could not be imported: {exc}")
        return _workflow_redirect(request, pk, "receiving:stage2", "translogic")
    messages.success(request, f"PRODUCT_MOVES.CSV imported: {record.row_count} movement row(s).")
    return _workflow_redirect(request, pk, "receiving:stage2", "translogic")


@login_required
@transaction.atomic
def upload_product_moves(request, pk):
    if request.method != "POST":
        raise Http404
    container = get_object_or_404(Container, pk=pk)
    closed_redirect = _closed_container_guard(request, container)
    if closed_redirect:
        return closed_redirect
    form = ProductMovesUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Choose a valid PRODUCT_MOVES.CSV file.")
        return _workflow_redirect(request, pk, "receiving:stage2", "translogic")
    uploaded = form.cleaned_data["file"]
    if uploaded.size > settings.MAX_UPLOAD_SIZE:
        messages.error(request, "The CSV exceeds the configured upload size limit.")
        return _workflow_redirect(request, pk, "receiving:stage2", "translogic")
    if Path(uploaded.name or "").suffix.lower() != ".csv":
        messages.error(request, "PRODUCT_MOVES must be a .csv file.")
        return _workflow_redirect(request, pk, "receiving:stage2", "translogic")
    try:
        content = uploaded.read()
        record = _activate_product_moves(
            container,
            request.user,
            content,
            original_name=uploaded.name or "PRODUCT_MOVES.CSV",
            source_path="manual upload",
        )
    except ValueError as exc:
        messages.error(request, f"PRODUCT_MOVES.CSV could not be imported: {exc}")
        return _workflow_redirect(request, pk, "receiving:stage2", "translogic")
    messages.success(request, f"PRODUCT_MOVES.CSV uploaded: {record.row_count} movement row(s).")
    return _workflow_redirect(request, pk, "receiving:stage2", "translogic")


@login_required
def transfer_upstockserial(request, pk):
    container = get_object_or_404(Container, pk=pk)
    status = _upstock_transfer_status(container)
    if not status["can_copy"]:
        messages.error(request, status["reason"] or "UPStockSerial is not ready for direct Translogic transfer.")
        return redirect(reverse("receiving:container_detail", args=[pk]) + "#translogic")

    destination_path = status["destination_path"]
    if request.method == "POST":
        if request.POST.get("confirmed") != "yes":
            messages.warning(request, "Copy cancelled because operator confirmation was not received.")
            return redirect(reverse("receiving:container_detail", args=[pk]) + "#translogic")
        expected_mtime = request.POST.get("expected_destination_mtime", "")
        current_mtime = str(destination_path.stat().st_mtime_ns) if destination_path.exists() else ""
        if current_mtime != expected_mtime:
            messages.warning(request, "The Translogic destination changed after the confirmation screen was opened. Review it again before copying.")
            return redirect("receiving:transfer_upstockserial", pk=pk)
        try:
            result = copy_file_verified(status["source_path"], destination_path)
            audit = _record_transfer_audit(
                container, request.user, "UPSTOCK_SERIAL", status["source_display"],
                status["destination_display"], result,
                replaced_name=destination_path.name if result.get("replaced") else "",
            )
        except (OSError, FileNotFoundError) as exc:
            messages.error(request, f"UPStockSerial could not be copied to Translogic: {exc}")
            return redirect("receiving:transfer_upstockserial", pk=pk)
        messages.success(
            request,
            f"UPStockSerial.csv copied and verified at {audit['timestamp']} → {status['destination_display']}.",
        )
        return redirect(reverse("receiving:container_detail", args=[pk]) + "#translogic")

    expected_mtime = str(destination_path.stat().st_mtime_ns) if destination_path.exists() else ""
    return render(
        request,
        "receiving/translogic_transfer_confirm.html",
        {
            "container": container,
            "transfer_kind": "UPStockSerial",
            "source_name": "UPStockSerial.csv",
            "source_display": status["source_display"],
            "destination_name": "UPStockSerial.csv",
            "destination_display": status["destination_display"],
            "destination_exists": status["destination_exists"],
            "destination_modified": status["destination_modified"],
            "expected_destination_mtime": expected_mtime,
            "confirm_label": "Confirm replacement and copy" if status["destination_exists"] else "Confirm copy to Translogic",
            "back_url": reverse("receiving:container_detail", args=[pk]) + "#translogic",
        },
    )


@login_required
def transfer_new_product_import(request, pk):
    container = get_object_or_404(Container, pk=pk)
    status = _new_product_transfer_status(container)
    if not status["can_copy"]:
        messages.error(request, status["reason"] or "New Product Import is not ready for direct Translogic transfer.")
        return redirect(reverse("receiving:container_detail", args=[pk]) + "#products")

    oldest = status["oldest"]
    destination_path = Path(oldest["path"])
    source_path = Path(status["latest"].file.path)
    destination_display = _windows_destination_for(oldest["name"])

    if request.method == "POST":
        if request.POST.get("confirmed") != "yes":
            messages.warning(request, "Replacement cancelled because operator confirmation was not received.")
            return redirect(reverse("receiving:container_detail", args=[pk]) + "#products")
        if request.POST.get("target_name") != oldest["name"]:
            messages.warning(request, "The oldest Translogic numbered file changed after the confirmation screen was opened. Review it again before replacing anything.")
            return redirect("receiving:transfer_new_product_import", pk=pk)
        expected_mtime = request.POST.get("expected_destination_mtime", "")
        current_mtime = str(destination_path.stat().st_mtime_ns) if destination_path.exists() else ""
        if current_mtime != expected_mtime:
            messages.warning(request, "The selected Translogic file changed after the confirmation screen was opened. Review the current oldest file again.")
            return redirect("receiving:transfer_new_product_import", pk=pk)
        try:
            result = copy_file_verified(source_path, destination_path)
            audit = _record_transfer_audit(
                container, request.user, "NEW_PRODUCT", status["latest"].original_name,
                destination_display, result, replaced_name=oldest["name"],
            )
        except (OSError, FileNotFoundError) as exc:
            messages.error(request, f"New Product Import could not be copied to Translogic: {exc}")
            return redirect("receiving:transfer_new_product_import", pk=pk)
        messages.success(
            request,
            f"{oldest['name']} replaced with the reviewed New Product Import and verified at {audit['timestamp']}.",
        )
        return redirect(reverse("receiving:container_detail", args=[pk]) + "#products")

    expected_mtime = str(destination_path.stat().st_mtime_ns) if destination_path.exists() else ""
    return render(
        request,
        "receiving/translogic_transfer_confirm.html",
        {
            "container": container,
            "transfer_kind": "New Product Import",
            "source_name": status["latest"].original_name,
            "source_display": status["latest"].original_name + " (PON generated audit copy)",
            "destination_name": oldest["name"],
            "destination_display": destination_display,
            "destination_exists": True,
            "destination_modified": oldest["modified_at"],
            "expected_destination_mtime": expected_mtime,
            "target_name": oldest["name"],
            "numbered_pattern": status["pattern"],
            "numbered_files": status["files"],
            "confirm_label": f"Confirm replacement of {oldest['name']}",
            "back_url": reverse("receiving:container_detail", args=[pk]) + "#products",
        },
    )


def _download_generated_export(export, content_type, download_name=None):
    with export.file.open("rb") as handle:
        content = handle.read()
    response = HttpResponse(content, content_type=content_type)
    safe_name = (download_name or export.original_name).replace('"', "")
    response["Content-Disposition"] = f'attachment; filename="{safe_name}"'
    return response


def _ensure_current_upstockserial(container, user):
    received_batch, moves_import, reconciliation = _stage2_data(container)
    latest = container.generated_exports.filter(kind="UPSTOCK_SERIAL").first()
    stale = _export_stale(
        latest,
        getattr(received_batch, "confirmed_at", None),
        getattr(moves_import, "imported_at", None),
    )
    if container.status == "CLOSED":
        if latest:
            return latest
        raise ValueError("This completed container has no current UPStockSerial file. Reopen it before rebuilding outputs.")

    if not received_batch:
        raise ValueError("Confirm the first-scan / received-bike file before downloading UPStockSerial.csv.")
    if not moves_import:
        raise ValueError("Load PRODUCT_MOVES.CSV before downloading UPStockSerial.csv.")
    if not reconciliation or not reconciliation.get("ready"):
        raise ValueError("Stage 2 reconciliation has exceptions. Resolve them before downloading UPStockSerial.csv.")
    if latest and not stale:
        return latest

    content = build_upstockserial_csv(reconciliation["rows"])
    timestamp = timezone.localtime().strftime("%Y%m%d_%H%M")
    stored_name = f"UPStockSerial_{container.identifier}_{timestamp}.csv"
    export = _store_export(
        container,
        user,
        "UPSTOCK_SERIAL",
        stored_name,
        "csv",
        content,
        reconciliation["matched_units"],
    )

    output_path = Path(_configured_upstockserial_path())
    try:
        if output_path.parent.exists():
            output_path.write_bytes(content)
    except OSError:
        # The download remains available even when the operator-facing working
        # folder is temporarily unavailable to Docker.
        pass
    return export


def _ensure_current_client_report(container, user):
    client_batch, received_batch, catalog, rows = _client_report_data(container)
    latest = container.generated_exports.filter(kind="CLIENT_REPORT").first()
    newest_definition = None
    new_codes = [row.get("code", "") for row in rows if row.get("comment") == "New"]
    if new_codes:
        newest_definition = ProductDefinition.objects.filter(code__in=new_codes).order_by("-updated_at").first()
    stale = _export_stale(
        latest,
        getattr(client_batch, "confirmed_at", None),
        getattr(received_batch, "confirmed_at", None),
        getattr(catalog, "uploaded_at", None),
        getattr(newest_definition, "updated_at", None),
    )
    if container.status == "CLOSED":
        if latest:
            return latest
        raise ValueError("This completed container has no current customer report. Reopen it before rebuilding outputs.")

    if not client_batch or not received_batch:
        raise ValueError("Confirm both the client manifest and first scan before downloading the customer report.")
    if not catalog:
        raise ValueError("Synchronize the Translogic product master before downloading the customer report.")
    if not rows:
        raise ValueError("There are no product rows available for the customer report.")
    if latest and not stale:
        return latest

    content = build_client_receiving_workbook(container.identifier, rows).getvalue()
    timestamp = timezone.localtime().strftime("%Y%m%d_%H%M")
    filename = f"Receiving_Container_Data_{container.identifier}_{timestamp}.xlsx"
    export = _store_export(
        container,
        user,
        "CLIENT_REPORT",
        filename,
        "xlsx",
        content,
        len(rows),
    )
    try:
        report_dir = Path(_configured_client_report_dir())
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / filename).write_bytes(content)
    except OSError:
        pass
    return export


@login_required
@transaction.atomic
def download_current_upstockserial(request, pk):
    container = get_object_or_404(Container, pk=pk)
    try:
        export = _ensure_current_upstockserial(container, request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect(reverse("receiving:container_detail", args=[pk]) + "#translogic")
    return _download_generated_export(export, "text/csv", "UPStockSerial.csv")


@login_required
@transaction.atomic
def download_current_client_report(request, pk):
    container = get_object_or_404(Container, pk=pk)
    try:
        export = _ensure_current_client_report(container, request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect(reverse("receiving:container_detail", args=[pk]) + "#complete")
    return _download_generated_export(
        export,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        f"{container.identifier} Advised.xls",
    )


# Legacy endpoints are kept for bookmarked URLs / older pages. They are no
# longer presented to the operator as Generate / Regenerate actions.
@login_required
@transaction.atomic
def generate_upstockserial(request, pk):
    if request.method != "POST":
        raise Http404
    container = get_object_or_404(Container, pk=pk)
    try:
        _ensure_current_upstockserial(container, request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
    return _workflow_redirect(request, pk, "receiving:stage2", "translogic")


@login_required
def download_upstockserial(request, export_id):
    export = get_object_or_404(GeneratedExport, pk=export_id, kind="UPSTOCK_SERIAL")
    return _download_generated_export(export, "text/csv", "UPStockSerial.csv")


@login_required
@transaction.atomic
def generate_client_report(request, pk):
    if request.method != "POST":
        raise Http404
    container = get_object_or_404(Container, pk=pk)
    try:
        _ensure_current_client_report(container, request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
    return_to = request.POST.get("return_to", "comparison")
    if return_to == "workspace":
        return redirect(reverse("receiving:container_detail", args=[pk]) + "#complete")
    if return_to == "stage2":
        return redirect("receiving:stage2", pk=pk)
    return redirect("receiving:comparison", pk=pk)


@login_required
def download_client_report(request, export_id):
    export = get_object_or_404(GeneratedExport.objects.select_related("container"), pk=export_id, kind="CLIENT_REPORT")
    return _download_generated_export(
        export,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        f"{export.container.identifier} Advised.xls",
    )


@login_required
@transaction.atomic
def mark_container_complete(request, pk):
    if request.method != "POST":
        raise Http404
    container = get_object_or_404(Container, pk=pk)
    workspace = _container_workspace_data(container)
    if not workspace["ready_to_complete"]:
        messages.error(
            request,
            "The container cannot be completed yet. Download the current UPStockSerial and customer report files first.",
        )
        return redirect(reverse("receiving:container_detail", args=[pk]) + "#complete")
    container.status = "CLOSED"
    container.save(update_fields=["status"])
    messages.success(request, f"Container {container.identifier} marked Complete. You can reopen it later if a correction is required.")
    return redirect("receiving:container_detail", pk=pk)


@login_required
@transaction.atomic
def reopen_container(request, pk):
    if request.method != "POST":
        raise Http404
    container = get_object_or_404(Container, pk=pk)
    container.status = "OPEN"
    container.save(update_fields=["status"])
    messages.success(request, f"Container {container.identifier} reopened for review or correction.")
    return redirect("receiving:container_detail", pk=pk)


@login_required
def configure_import(request, source_id):
    source = get_object_or_404(SourceFile.objects.select_related("container__customer"), pk=source_id)
    if request.method == "POST":
        closed_redirect = _closed_container_guard(request, source.container)
        if closed_redirect:
            return closed_redirect
    try:
        sheets = inspect_workbook(source.file.path)
        sheet_names = [item["name"] for item in sheets]
        analysis = _source_mapping_analysis(source)
        suggested = dict(analysis["mapping"])
    except Exception as exc:
        source.status = "ERROR"
        source.save(update_fields=["status"])
        messages.error(request, f"The workbook could not be read: {exc}")
        return redirect("receiving:container_detail", pk=source.container_id)

    # Exact, previously confirmed structure: skip repetitive mapping and go directly to validation preview.
    if request.method == "GET" and analysis.get("profile_match") and request.GET.get("manual") != "1":
        try:
            rows, errors = parse_workbook(source.file.path, suggested)
        except Exception:
            rows, errors = [], [{"message": "Saved profile could not be applied."}]
        if rows and not errors:
            with transaction.atomic():
                source.batches.filter(status="PREVIEW").delete()
                batch = ImportBatch.objects.create(
                    source_file=source,
                    mapping=suggested,
                    total_rows=len(rows),
                    total_units=sum(item["quantity"] for item in rows),
                    created_by=request.user,
                )
                NormalizedLine.objects.bulk_create([NormalizedLine(batch=batch, **item) for item in rows])
                source.status = "PREVIEW"
                source.save(update_fields=["status"])
            messages.success(request, f"Saved mapping profile '{analysis['profile_match']}' recognised. Review the preview.")
            return redirect("receiving:batch_preview", batch_id=batch.pk)

    form = ImportMappingForm(request.POST or None, sheets=sheet_names, initial=suggested)
    selected_sheet_name = form["sheet_name"].value() or suggested.get("sheet_name") or (sheet_names[0] if sheet_names else "")
    selected_sheet = next((item for item in sheets if item["name"] == selected_sheet_name), sheets[0] if sheets else None)
    preview_headers = []
    if selected_sheet:
        preview_headers = [get_column_letter(index) for index in range(1, min(selected_sheet["columns"], 12) + 1)]
    mapping_summary = {
        "code": (form["code_column"].value() or "").upper(),
        "long_code": (form["long_code_column"].value() or "").upper(),
        "description": (form["description_column"].value() or "").upper(),
        "quantity": (form["quantity_column"].value() or "").upper(),
        "container": (form["container_column"].value() or "").upper(),
    }
    mapping_ready = bool(selected_sheet and mapping_summary["code"] and form["start_row"].value())

    if request.method == "POST" and form.is_valid():
        mapping = form.cleaned_data.copy()
        save_profile = mapping.pop("save_profile", False)
        profile_name = mapping.pop("profile_name", "")
        selected_analysis = analysis
        if mapping.get("sheet_name") and mapping.get("sheet_name") != analysis.get("worksheet"):
            selected_analysis = analyse_workbook_mapping(
                source.file.path,
                source.kind,
                known_product_codes=_known_product_codes_for_customer(source.container.customer),
                sheet_name=mapping["sheet_name"],
            )
        mapping["_structure_signature"] = selected_analysis["structure_signature"]
        mapping["_mapping_confidence"] = selected_analysis["confidence"]
        mapping["_header_row"] = selected_analysis["header_row"]
        mapping["_analysis_version"] = "2026.09"
        try:
            rows, errors = parse_workbook(source.file.path, mapping)
        except Exception as exc:
            form.add_error(None, f"The file could not be processed with this mapping: {exc}")
        else:
            if not rows:
                form.add_error(None, "No bike rows were found. Review the worksheet, first row and proposed columns.")
            else:
                with transaction.atomic():
                    source.batches.filter(status="PREVIEW").delete()
                    batch = ImportBatch.objects.create(
                        source_file=source,
                        mapping=mapping,
                        total_rows=len(rows),
                        total_units=sum(item["quantity"] for item in rows),
                        created_by=request.user,
                    )
                    NormalizedLine.objects.bulk_create([NormalizedLine(batch=batch, **item) for item in rows])
                    source.status = "PREVIEW"
                    source.save(update_fields=["status"])
                    if save_profile:
                        ImportProfile.objects.update_or_create(
                            customer=source.container.customer,
                            name=profile_name,
                            kind=source.kind,
                            defaults={"mapping": mapping, "active": True},
                        )
                if errors:
                    messages.warning(request, f"Preview created with {len(errors)} row error(s). Review them before confirming.")
                return redirect("receiving:batch_preview", batch_id=batch.pk)

    detected = []
    current_identifier = normalize_container_identifier(source.container.identifier)
    for item in analysis.get("containers", []):
        row = dict(item)
        row["is_current"] = item["identifier"] == current_identifier
        existing = Container.objects.filter(identifier=item["identifier"]).first()
        row["exists"] = bool(existing)
        row["will_create"] = not existing and not row["is_current"]
        detected.append(row)

    return render(
        request,
        "receiving/configure_import.html",
        {
            "source": source,
            "form": form,
            "sheets": sheets,
            "selected_sheet": selected_sheet,
            "preview_headers": preview_headers,
            "mapping_summary": mapping_summary,
            "mapping_ready": mapping_ready,
            "mapping_analysis": analysis,
            "detected_containers": detected,
        },
    )


@login_required
def batch_preview(request, batch_id):
    batch = get_object_or_404(ImportBatch.objects.select_related("source_file__container__customer"), pk=batch_id)
    groups = _container_preview_groups(batch)
    current_identifier = normalize_container_identifier(batch.container.identifier)
    multi_container = len(groups) > 1
    current_group = next((item for item in groups if item["identifier"] == current_identifier), None)
    current_present = not groups or bool(current_group)
    return render(
        request,
        "receiving/batch_preview.html",
        {
            "batch": batch,
            "lines": batch.lines.all()[:200],
            "container_groups": groups,
            "multi_container": multi_container,
            "current_group": current_group,
            "current_present": current_present,
        },
    )


@login_required
@transaction.atomic
def confirm_batch(request, batch_id):
    if request.method != "POST":
        raise Http404
    batch = get_object_or_404(ImportBatch.objects.select_related("source_file__container__customer"), pk=batch_id, status="PREVIEW")
    closed_redirect = _closed_container_guard(request, batch.source_file.container)
    if closed_redirect:
        return closed_redirect
    source = batch.source_file

    split_result = {"created": [], "linked": [], "current_units": batch.total_units, "legacy_mismatch": ""}
    if source.kind == "CLIENT" and batch.mapping.get("container_column"):
        try:
            split_result = _confirm_multi_container_manifest(batch, request.user)
        except ValueError as exc:
            transaction.set_rollback(True)
            messages.error(request, str(exc))
            return redirect("receiving:batch_preview", batch_id=batch.pk)

    ImportBatch.objects.filter(
        source_file__container=source.container,
        source_file__kind=source.kind,
        status="CONFIRMED",
    ).exclude(pk=batch.pk).update(status="SUPERSEDED")
    batch.status = "CONFIRMED"
    batch.confirmed_at = timezone.now()
    batch.save(update_fields=["status", "confirmed_at", "total_rows", "total_units"])
    source.status = "CONFIRMED"
    source.save(update_fields=["status"])
    if source.kind == "RECEIVED":
        _product_check_data(source.container)

    structure_signature = batch.mapping.get("_structure_signature")
    if structure_signature:
        auto_profile_name = f"Auto {source.kind} {structure_signature[:8]}"
        ImportProfile.objects.update_or_create(
            customer=source.container.customer,
            name=auto_profile_name,
            kind=source.kind,
            defaults={"mapping": batch.mapping, "active": True},
        )

    message = f"Import confirmed: {batch.total_units} bike unit(s) for {source.container.identifier}."
    if split_result["created"]:
        message += " Pending containers created: " + ", ".join(split_result["created"]) + "."
    if split_result["linked"]:
        message += " Existing containers updated: " + ", ".join(split_result["linked"]) + "."
    if split_result.get("legacy_mismatch"):
        message += (
            f" Note: the workbook contained one container reference ({split_result['legacy_mismatch']}) "
            f"that did not match the current container; it was kept with {source.container.identifier} for backward compatibility."
        )
    messages.success(request, message)
    return redirect(reverse("receiving:container_detail", args=[source.container_id]) + "#receive")


@login_required
def comparison(request, pk):
    container = get_object_or_404(Container, pk=pk)
    client_batch = ImportBatch.objects.filter(
        source_file__container=container, source_file__kind="CLIENT", status="CONFIRMED"
    ).select_related("source_file").first()
    received_batch = ImportBatch.objects.filter(
        source_file__container=container, source_file__kind="RECEIVED", status="CONFIRMED"
    ).select_related("source_file").first()
    client_lines = client_batch.lines.all() if client_batch else []
    received_lines = received_batch.lines.all() if received_batch else []
    comparison_rows = compare_lines(client_lines, received_lines)
    _, _, client_report_catalog, client_report_rows = _client_report_data(container)
    totals = {
        "expected": sum(row["expected"] for row in comparison_rows),
        "received": sum(row["received"] for row in comparison_rows),
        "difference": sum(row["difference"] for row in comparison_rows),
        "matches": sum(1 for row in comparison_rows if row["status"] == "MATCH"),
        "exceptions": sum(1 for row in comparison_rows if row["status"] != "MATCH"),
    }
    return render(
        request,
        "receiving/comparison.html",
        {
            "container": container,
            "client_batch": client_batch,
            "received_batch": received_batch,
            "rows": comparison_rows,
            "totals": totals,
            "client_report_rows": client_report_rows,
            "client_report_catalog_available": bool(client_report_catalog),
            "client_report_ready": bool(client_batch and received_batch and client_report_catalog),
            "client_report_exports": container.generated_exports.filter(kind="CLIENT_REPORT")[:10],
        },
    )


def _enrich_pbp_to_pon_rows_from_catalog_file(catalog, rows):
    """Use the already-stored physical Product Master to recover optional historical dimensions in memory."""
    pending = [
        row for row in rows
        if row.get("is_pbp_to_pon") and not (row.get("pbp_to_pon_data") or {}).get("valid")
    ]
    if not pending or not catalog or not getattr(catalog, "file", None):
        return
    try:
        source_path = Path(catalog.file.path)
        if not source_path.is_file():
            return
        parsed_rows = parse_product_catalog(source_path)
    except (OSError, ValueError, RuntimeError):
        return

    pbp_index = {}
    for item in parsed_rows:
        if str(item.get("customer") or "").strip().upper() != "PBP":
            continue
        for field in ("code", "pon_sku", "code2"):
            value = str(item.get(field) or "").strip().upper()
            if value:
                pbp_index.setdefault(value, item)

    for row in pending:
        item = pbp_index.get(str(row.get("code") or "").strip().upper())
        if not item:
            continue
        row.update({
            "catalog_customer": item.get("customer", ""),
            "catalog_code": item.get("code", ""),
            "catalog_pon_sku": item.get("pon_sku", ""),
            "catalog_code2": item.get("code2", ""),
            "catalog_short_name": item.get("short_name", ""),
            "catalog_long_name": item.get("long_name", ""),
            "catalog_group1": item.get("group1", ""),
            "catalog_group2": item.get("group2", ""),
            "catalog_raw_data": dict(item.get("raw_data") or {}),
        })
        row["pbp_to_pon_data"] = pbp_to_pon_product_data(row)


def _persisted_product_check_data(container, received_batch=None):
    """Read stored decisions only. No master parsing, classification or writes."""
    catalog = _active_catalog_for_customer(container.customer)
    if received_batch is None:
        received_batch = ImportBatch.objects.filter(
            source_file__container=container, source_file__kind="RECEIVED", status="CONFIRMED",
        ).first()
    states = {item.code: item for item in container.product_statuses.all()}
    grouped = {}
    if received_batch:
        for line in received_batch.lines.all():
            key = (line.code.strip().upper(), line.location.strip().upper())
            row = grouped.setdefault(key, {"code": key[0], "location": key[1], "long_code": "", "count": 0})
            row["count"] += line.quantity
            row["long_code"] = row["long_code"] or line.long_code.strip().upper()
    definitions = {item.code: item for item in ProductDefinition.objects.filter(code__in=states)}
    rows = []
    for row in grouped.values():
        state = states.get(row["code"])
        history = state.import_history if state else {}
        saved = history.get("_check_row", {})
        classification = saved.get("classification") or (state.import_classification if state else "")
        if state and not classification and state.was_new:
            classification = "NEW"
        rows.append({
            **saved, **row,
            "classification": classification,
            "is_new": classification == "NEW",
            "is_pbp_to_pon": classification == "PBP_TO_PON",
            "status": "PBP → PON" if classification == "PBP_TO_PON" else ("New" if classification == "NEW" else ("Existing" if classification else "Needs Product Check")),
            "tl_code": saved.get("tl_code", ""), "matched_by": saved.get("matched_by", ""),
            "pbp_to_pon_data": saved.get("pbp_to_pon_data", history),
            "definition": definitions.get(row["code"]),
        })
    rows.sort(key=lambda row: (row["location"], row["code"]))
    original_classifications = {
        code: state.import_classification
        for code, state in states.items()
    }
    return catalog, received_batch, rows, product_check_summary(rows, original_classifications)


def _original_import_rows(container, rows, recover=True):
    """Reuse the per-container decision; never let a later master change membership."""
    statuses = {item.code: item for item in container.product_statuses.all()}
    result = []
    for current in rows:
        row = dict(current)
        state = statuses.get(row["code"])
        if state is None:
            continue
        if not state.import_classification and recover:
            # Older versions only stored was_new. Recover the master available at
            # classification time, rather than interpreting a newer PON match.
            original_catalog = ProductCatalog.objects.filter(
                customer=container.customer, uploaded_at__lte=state.classified_at,
            ).order_by("-uploaded_at", "-pk").first()
            if original_catalog is None:
                original_catalog = ProductCatalog.objects.filter(
                    customer__isnull=True, uploaded_at__lte=state.classified_at,
                ).order_by("-uploaded_at", "-pk").first()
            original = compare_products_to_catalog(
                [SimpleNamespace(code=row["code"], location=row["location"],
                                 quantity=row["count"], long_code=row["long_code"])],
                original_catalog.entries.all() if original_catalog else [],
                target_customer=container.customer.code,
            )[0]
            if original_catalog:
                _enrich_pbp_to_pon_rows_from_catalog_file(original_catalog, [original])
            state.import_classification = "NEW" if state.was_new else (
                "PBP_TO_PON" if original_catalog and original["is_pbp_to_pon"] else "EXISTING"
            )
            cached = state.import_history.get("_check_row")
            state.import_history = json.loads(json.dumps(
                original.get("pbp_to_pon_data") or {}, cls=DjangoJSONEncoder,
            ))
            if cached:
                state.import_history["_check_row"] = cached
            state.save(update_fields=["import_classification", "import_history"])
        if recover and state.import_classification == "PBP_TO_PON" and not state.import_history.get("valid"):
            history_row = current if current.get("is_pbp_to_pon") else None
            if history_row is None or not (history_row.get("pbp_to_pon_data") or {}).get("valid"):
                matches = ProductCatalogEntry.objects.filter(
                    Q(code=state.code) | Q(pon_sku=state.code) | Q(code2=state.code),
                    customer__iexact="PBP",
                ).filter(Q(catalog__customer=container.customer) | Q(catalog__customer__isnull=True))
                entry = matches.filter(catalog__uploaded_at__lte=state.classified_at).order_by("-catalog__uploaded_at", "source_row").first()
                if entry:
                    history_row = compare_products_to_catalog(
                        [SimpleNamespace(code=row["code"], location=row["location"], quantity=row["count"], long_code=row["long_code"])],
                        [entry], target_customer=container.customer.code,
                    )[0]
                    _enrich_pbp_to_pon_rows_from_catalog_file(entry.catalog, [history_row])
            if history_row and (history_row.get("pbp_to_pon_data") or {}).get("valid"):
                cached = state.import_history.get("_check_row")
                state.import_history = json.loads(json.dumps(history_row["pbp_to_pon_data"], cls=DjangoJSONEncoder))
                if cached:
                    state.import_history["_check_row"] = cached
                state.save(update_fields=["import_history"])
        row["classification"] = state.import_classification
        row["is_new"] = state.import_classification == "NEW"
        row["is_pbp_to_pon"] = state.import_classification == "PBP_TO_PON"
        row["pbp_to_pon_data"] = state.import_history
        result.append(row)
    return result


def _prefer_current_pon_data(catalog, migration_rows_by_code):
    """Use the current PON row without changing historical classification."""
    if not catalog or not migration_rows_by_code:
        return
    codes = set(migration_rows_by_code)
    entries = ProductCatalogEntry.objects.filter(
        catalog=catalog,
        customer__iexact="PON",
    ).filter(
        Q(code__in=codes) | Q(pon_sku__in=codes) | Q(code2__in=codes)
    ).order_by("source_row", "pk")
    preferred = {}
    for entry in entries:
        for value in (entry.code, entry.pon_sku, entry.code2):
            normalized = str(value or "").strip().upper()
            if normalized in codes:
                preferred.setdefault(normalized, entry)

    for code, row in migration_rows_by_code.items():
        entry = preferred.get(code)
        if not entry:
            continue
        pon_data = pbp_to_pon_product_data({
            "is_pbp_to_pon": True,
            "code": code,
            "catalog_code": entry.code,
            "catalog_pon_sku": entry.pon_sku,
            "catalog_code2": entry.code2,
            "catalog_short_name": entry.short_name,
            "catalog_long_name": entry.long_name,
            "catalog_raw_data": dict(entry.raw_data or {}),
        })
        row["pbp_to_pon_data"] = pon_data


def _product_check_data(container):
    catalog = _active_catalog_for_customer(container.customer)
    received_batch = ImportBatch.objects.filter(
        source_file__container=container,
        source_file__kind="RECEIVED",
        status="CONFIRMED",
    ).first()
    rows = []
    if catalog and received_batch:
        rows = compare_products_to_catalog(received_batch.lines.all(), catalog.entries.all(), target_customer=container.customer.code)
        _enrich_pbp_to_pon_rows_from_catalog_file(catalog, rows)
        existing_codes = set(container.product_statuses.values_list("code", flat=True))
        status_records = [
            ContainerProductStatus(
                container=container, code=row["code"], was_new=row["is_new"],
                import_classification=row["classification"],
                import_history=json.loads(json.dumps(row.get("pbp_to_pon_data") or {}, cls=DjangoJSONEncoder)),
            )
            for row in rows
            if row["code"] not in existing_codes
        ]
        if status_records:
            ContainerProductStatus.objects.bulk_create(status_records, ignore_conflicts=True)
        client_batch = ImportBatch.objects.filter(
            source_file__container=container, source_file__kind="CLIENT", status="CONFIRMED"
        ).first()
        client_values = {}
        if client_batch:
            for line in client_batch.lines.all():
                item = client_values.setdefault(line.code.strip().upper(), {"description": "", "long_code": ""})
                if line.description and not item["description"]:
                    item["description"] = line.description.strip()
                if line.long_code and not item["long_code"]:
                    item["long_code"] = line.long_code.strip().upper()
        definitions = {item.code: item for item in ProductDefinition.objects.filter(code__in={r["code"] for r in rows})}
        for row in rows:
            source = client_values.get(row["code"], {})
            row["description"] = source.get("description", "")
            row["long_code"] = row["long_code"] or source.get("long_code", "")
            row["definition"] = definitions.get(row["code"])
    if rows:
        states = {item.code: item for item in container.product_statuses.all()}
        updated = {}
        for row in rows:
            state = states[row["code"]]
            history = dict(state.import_history)
            if state.import_classification == "PBP_TO_PON" and not history.get("valid") and row.get("is_pbp_to_pon") and row["pbp_to_pon_data"].get("valid"):
                history.update(json.loads(json.dumps(row["pbp_to_pon_data"], cls=DjangoJSONEncoder)))
            history["_check_row"] = json.loads(json.dumps({
                key: value for key, value in row.items()
                if key not in {"definition", "count", "location"}
            }, cls=DjangoJSONEncoder))
            state.import_history = history
            updated[state.pk] = state
        ContainerProductStatus.objects.bulk_update(list(updated.values()), ["import_history"])
        # Recover legacy decisions only during explicit classification.
        _original_import_rows(container, rows)
    product_codes = {row["code"] for row in rows}
    original_classifications = dict(
        container.product_statuses.filter(code__in=product_codes).values_list(
            "code", "import_classification"
        )
    )
    return catalog, received_batch, rows, product_check_summary(rows, original_classifications)


@login_required
def product_check(request, pk):
    container = get_object_or_404(Container.objects.select_related("customer"), pk=pk)
    if request.method == "POST":
        closed_redirect = _closed_container_guard(request, container)
        if closed_redirect:
            return closed_redirect
    catalog, received_batch, rows, summary = _product_check_data(container)
    unique_new_rows = []
    seen = set()
    for row in rows:
        requires_definition = row["is_new"] or (
            row.get("is_pbp_to_pon") and not (row.get("pbp_to_pon_data") or {}).get("valid")
        )
        if requires_definition and row["code"] not in seen:
            unique_new_rows.append(row)
            seen.add(row["code"])

    name_dictionary = catalog.effective_name_dictionary() if catalog else {}
    export_configuration = _export_configuration()
    group1_rules = list(Group1Family.objects.filter(active=True).order_by("-priority", "family_name"))
    group1_rules_by_id = {rule.pk: rule for rule in group1_rules}
    product_forms = []
    all_valid = True
    unresolved_group1_count = 0

    for index, row in enumerate(unique_new_rows):
        definition = row.get("definition")
        initial = {}
        if not definition:
            history = row.get("pbp_to_pon_data") or {}
            full_name = history.get("long_name") or row.get("description") or row["code"]
            historical_short_name = history.get("short_name") or ""
            try:
                short_name = historical_short_name or suggest_translogic_name(full_name, name_dictionary=name_dictionary)
            except ValueError:
                short_name = ""
            initial = {
                "long_code": history.get("pon_sku") or history.get("code2") or row.get("long_code", ""),
                "short_name": short_name,
                "full_name": full_name,
            }
            for form_key, history_key in (("length_cm", "length_mm"), ("height_cm", "height_mm"), ("width_cm", "width_mm")):
                if history.get(history_key):
                    initial[form_key] = float(history[history_key]) / 10
            if history.get("weight_kg"):
                initial["weight_kg"] = history["weight_kg"]

        form = ProductDefinitionForm(
            request.POST or None,
            prefix=f"product-{index}",
            instance=definition,
            initial=initial,
        )
        form_valid = True
        if request.method == "POST":
            form_valid = form.is_valid()
            if not form_valid:
                all_valid = False

        if request.method == "POST" and form_valid:
            candidate_long_name = form.cleaned_data.get("full_name", "")
        elif definition:
            candidate_long_name = definition.full_name
        else:
            candidate_long_name = initial.get("full_name", "")

        group1_resolution = resolve_group1_family(
            candidate_long_name,
            export_configuration["TL_CUSTOMER"],
            group1_rules,
        )
        if not group1_resolution.get("resolved"):
            unresolved_group1_count += 1
            if request.method == "POST" and form_valid:
                form.add_error("full_name", group1_resolution["message"])
                all_valid = False
        elif definition and definition.group1 and request.method != "POST":
            # Show the currently configured relation; exports also revalidate it.
            group1_resolution["stored_group1"] = definition.group1

        product_forms.append(
            {
                "row": row,
                "form": form,
                "saved": bool(definition and definition.confirmed),
                "group1": group1_resolution.get("group1", ""),
                "group1_family": group1_resolution.get("family_name", ""),
                "group1_resolution": group1_resolution,
            }
        )

    if request.method == "POST":
        if not unique_new_rows:
            messages.info(request, "There are no products requiring manual Translogic data.")
        elif all_valid:
            with transaction.atomic():
                for item in product_forms:
                    product = item["form"].save(commit=False)
                    product.code = item["row"]["code"]
                    product.group1 = item["group1"]
                    rule_id = item["group1_resolution"].get("id")
                    product.group1_family = group1_rules_by_id.get(rule_id)
                    if not product.pk:
                        product.created_by = request.user
                    product.updated_by = request.user
                    product.confirmed = True
                    product.save()
            messages.success(request, "Translogic product names, Group1, dimensions and weights were saved permanently.")
            return redirect("receiving:product_check", pk=pk)
        else:
            messages.error(
                request,
                "Correct the highlighted fields. Products without a clear Group1 relation cannot be saved; add or adjust the relation in Django Administration.",
            )

    missing_definitions = [item["row"]["code"] for item in product_forms if not item["row"].get("definition")]
    saved_definition_count = sum(1 for item in product_forms if item["saved"])
    pending_definition_count = len(product_forms) - saved_definition_count
    return render(
        request,
        "receiving/product_check.html",
        {
            "container": container,
            "catalog": catalog,
            "received_batch": received_batch,
            "rows": rows,
            "summary": summary,
            "product_forms": product_forms,
            "missing_definitions": missing_definitions,
            "saved_definition_count": saved_definition_count,
            "pending_definition_count": pending_definition_count,
            "unresolved_group1_count": unresolved_group1_count,
            "export_configuration": export_configuration,
            "generated_exports": container.generated_exports.all()[:20],
            "name_dictionary_exact_count": len(name_dictionary.get("exact", {})),
            "name_dictionary_rule_count": len(name_dictionary.get("rules", [])),
        },
    )


@login_required
def export_product_check(request, pk):
    container = get_object_or_404(Container, pk=pk)
    catalog, received_batch, rows, summary = _product_check_data(container)
    if not catalog or not received_batch:
        messages.error(request, "Synchronize the product catalogue and confirm the received-bike file before exporting.")
        return redirect("receiving:product_check", pk=pk)
    workbook = build_product_check_workbook(container.identifier, rows)
    timestamp = timezone.localtime().strftime("%Y%m%d_%H%M")
    base_name = f"PON_Product_Check_{container.identifier}_{timestamp}"
    # This workbook contains embedded PNG barcodes. BIFF7 conversion drops
    # drawings, so the printable report must remain XLSX. TL_EXPORT_FORMAT is
    # reserved for files that are actually imported into Translogic.
    content, extension, content_type = convert_excel_output(workbook, base_name, "xlsx")
    filename = f"{base_name}{extension}"
    _store_export(container, request.user, "PRODUCT_CHECK", filename, "xlsx", content, len(rows))
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def export_new_products(request, pk):
    container = get_object_or_404(Container, pk=pk)
    if not container.container_date:
        messages.error(request, "Enter the container date before generating New Product Import.")
        return redirect("receiving:container_detail", pk=pk)
    catalog, received_batch, rows, summary = _persisted_product_check_data(container)
    if any(not row.get("classification") for row in rows):
        catalog, received_batch, rows, summary = _product_check_data(container)
    if not catalog or not received_batch:
        messages.error(request, "Synchronize the product catalogue and confirm the received-bike file first.")
        return redirect("receiving:product_check", pk=pk)

    rows = _original_import_rows(container, rows)
    new_rows_by_code = {row["code"]: row for row in rows if row["is_new"]}
    migration_rows_by_code = {row["code"]: row for row in rows if row.get("is_pbp_to_pon")}
    _prefer_current_pon_data(catalog, migration_rows_by_code)
    import_codes = sorted(set(new_rows_by_code) | set(migration_rows_by_code))
    definition_required_codes = sorted(
        set(new_rows_by_code)
        | {
            code for code, row in migration_rows_by_code.items()
            if not (row.get("pbp_to_pon_data") or {}).get("valid")
        }
    )
    definitions = {
        item.code: item
        for item in ProductDefinition.objects.filter(code__in=definition_required_codes, confirmed=True).order_by("code")
    }
    missing = [code for code in definition_required_codes if code not in definitions]
    if missing:
        messages.error(request, f"Complete names, Group1, dimensions and weight for: {', '.join(missing)}.")
        return redirect("receiving:product_check", pk=pk)
    if not import_codes:
        messages.warning(request, "There are no New or PBP → PON products to import into Translogic.")
        return redirect("receiving:product_check", pk=pk)

    configuration = _export_configuration()
    group1_rules = list(Group1Family.objects.filter(active=True).order_by("-priority", "family_name"))
    rules_by_id = {rule.pk: rule for rule in group1_rules}
    unresolved = []
    changed = []
    export_items = []

    for code in import_codes:
        if code in new_rows_by_code:
            definition = definitions[code]
            resolution = resolve_group1_family(definition.full_name, configuration["TL_CUSTOMER"], group1_rules)
            if not resolution.get("resolved"):
                unresolved.append(code)
                continue
            rule_id = resolution.get("id")
            family = rules_by_id.get(rule_id)
            if definition.group1 != resolution["group1"] or definition.group1_family_id != rule_id:
                definition.group1 = resolution["group1"]
                definition.group1_family = family
                changed.append(definition)
            export_items.append(definition)
            continue

        row = migration_rows_by_code[code]
        history = row.get("pbp_to_pon_data") or {}
        fallback = definitions.get(code)
        full_name = history.get("long_name") or getattr(fallback, "full_name", "")
        short_name = history.get("short_name") or getattr(fallback, "short_name", "")
        resolution = resolve_group1_family(full_name, "PON", group1_rules)
        if not resolution.get("resolved"):
            unresolved.append(code)
            continue

        if history.get("valid"):
            length_mm = history["length_mm"]
            height_mm = history["height_mm"]
            width_mm = history["width_mm"]
            weight_kg = history["weight_kg"]
            cubic_override = history["cubic"]
        else:
            length_mm = fallback.length_mm
            height_mm = fallback.height_mm
            width_mm = fallback.width_mm
            weight_kg = fallback.weight_kg
            cubic_override = None

        export_items.append(SimpleNamespace(
            code=history.get("code") or code,
            long_code=history.get("pon_sku") or history.get("code2") or getattr(fallback, "long_code", "") or row.get("long_code", ""),
            short_name=short_name,
            full_name=full_name,
            group1=resolution["group1"],
            length_mm=length_mm,
            height_mm=height_mm,
            width_mm=width_mm,
            weight_kg=weight_kg,
            cubic_override=cubic_override,
            customer_override="PON",
            status_override="L",
            quantity_override=1,
            pallet_override=0,
            lift_override=1,
            outer_override=1,
            is_pbp_to_pon=True,
            source_pon_sku=history.get("pon_sku", ""),
            source_code2=history.get("code2", ""),
        ))

    if unresolved:
        messages.error(
            request,
            "Group1 could not be resolved for: " + ", ".join(unresolved) + ". Add or adjust the relation in Administration → Group1 family mappings, then review the products again.",
        )
        return redirect("receiving:product_check", pk=pk)
    if changed:
        ProductDefinition.objects.bulk_update(changed, ["group1", "group1_family"])

    timestamp = timezone.localtime().strftime("%Y%m%d_%H%M")
    base_name = f"NewProductImport_{container.identifier}_{timestamp}"
    try:
        workbook = build_new_product_workbook(export_items, configuration, container.container_date)
        content, extension, content_type = convert_excel_output(workbook, base_name, configuration["TL_EXPORT_FORMAT"])
    except (ValueError, RuntimeError) as exc:
        messages.error(request, str(exc))
        return redirect("receiving:product_check", pk=pk)
    filename = f"{base_name}{extension}"
    _store_export(container, request.user, "NEW_PRODUCT", filename, configuration["TL_EXPORT_FORMAT"], content, len(export_items))
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
