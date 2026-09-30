import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.db.models import Count, Max, Q
from django.utils import timezone

from receiving.models import (
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
    ProductMovement,
    ProductMovesImport,
    ShortNameDictionaryRule,
    SourceFile,
)
from receiving.services import (
    EXPORT_DEFAULTS,
    calculate_cubic,
    compare_lines,
    compare_products_to_catalog,
    reconcile_product_movements,
    resolve_group1_family,
)
from receiving.views import (
    _active_catalog_for_customer,
    _configured_product_moves_path,
    _direct_product_moves_path,
    _export_stale,
    _new_product_transfer_status,
    _upstock_transfer_status,
)


def iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        return value.astimezone(timezone.get_current_timezone()).isoformat()
    return str(value)


def read_installed_release():
    state_path = Path(settings.BASE_DIR) / ".update_state" / "last_update.json"
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8-sig"))
        return {
            "release_version": payload.get("release_version", "unknown"),
            "prepared_at": payload.get("prepared_at"),
            "applied_at": payload.get("applied_at"),
            "status": payload.get("status", "unknown"),
        }
    except Exception as exc:
        return {
            "release_version": "unknown",
            "status": "state-file-unavailable",
            "state_error": str(exc),
        }


def latest_activity_for(container):
    candidates = [(container.created_at, "container-created")]
    source = container.source_files.order_by("-uploaded_at").first()
    if source:
        candidates.append((source.uploaded_at, f"source-upload:{source.kind}"))
    batch = ImportBatch.objects.filter(source_file__container=container).order_by("-created_at").first()
    if batch:
        candidates.append((batch.confirmed_at or batch.created_at, f"import-batch:{batch.status}"))
    moves = container.product_moves_imports.order_by("-imported_at").first()
    if moves:
        candidates.append((moves.imported_at, "product-moves-import"))
    export = container.generated_exports.order_by("-generated_at").first()
    if export:
        candidates.append((export.generated_at, f"generated-export:{export.kind}"))
    candidates = [item for item in candidates if item[0] is not None]
    return max(candidates, key=lambda item: item[0]) if candidates else (None, "")


def workflow_row(container):
    """Build workflow state without creating/updating any operational record."""
    activity_at, activity_kind = latest_activity_for(container)
    result = {
        "container_id": container.identifier,
        "job_order": container.job_order or "",
        "customer": container.customer.code,
        "container_date": str(container.container_date or ""),
        "status": container.status,
        "auto_created_from_manifest": container.auto_created_from_manifest,
        "manifest_source_name": container.manifest_source_name or "",
        "created_at": iso(container.created_at),
        "last_activity_at": iso(activity_at),
        "last_activity_kind": activity_kind,
        "warnings": [],
    }
    try:
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

        catalog = _active_catalog_for_customer(container.customer)
        product_rows = []
        if catalog and received_batch:
            product_rows = compare_products_to_catalog(received_batch.lines.all(), catalog.entries.all())
        new_codes = sorted({row["code"] for row in product_rows if row["is_new"]})
        definitions = {
            item.code: item
            for item in ProductDefinition.objects.filter(code__in=new_codes, confirmed=True)
        }
        pending_new_codes = [code for code in new_codes if code not in definitions]
        products_ready = bool(received_batch and catalog and not pending_new_codes)
        product_check_download_ready = bool(catalog and received_batch)

        new_product_import_download_ready = False
        if container.container_date and product_check_download_ready and new_codes and not pending_new_codes:
            tl_customer = (
                AppSetting.objects.filter(key="TL_CUSTOMER").values_list("value", flat=True).first()
                or EXPORT_DEFAULTS["TL_CUSTOMER"]
            )
            group1_rules = list(Group1Family.objects.filter(active=True).order_by("-priority", "family_name"))
            new_product_import_download_ready = all(
                resolve_group1_family(definitions[code].full_name, tl_customer, group1_rules).get("resolved")
                for code in new_codes
            )

        moves_import = ProductMovesImport.objects.filter(container=container, active=True).first()
        reconciliation = None
        if received_batch and moves_import:
            movement_rows = list(moves_import.rows.values("source_row", "product", "movement"))
            reconciliation = reconcile_product_movements(received_batch.lines.all(), movement_rows)
        moves_product_count = moves_import.rows.values("product").distinct().count() if moves_import else 0

        latest_product_check = container.generated_exports.filter(kind="PRODUCT_CHECK").first()
        latest_new_product_import = container.generated_exports.filter(kind="NEW_PRODUCT").first()
        latest_upstock = container.generated_exports.filter(kind="UPSTOCK_SERIAL").first()
        latest_report = container.generated_exports.filter(kind="CLIENT_REPORT").first()

        upstock_stale = _export_stale(
            latest_upstock,
            getattr(received_batch, "confirmed_at", None),
            getattr(moves_import, "imported_at", None),
        )
        newest_definition = ProductDefinition.objects.filter(code__in=new_codes).order_by("-updated_at").first() if new_codes else None
        report_stale = _export_stale(
            latest_report,
            getattr(client_batch, "confirmed_at", None),
            getattr(received_batch, "confirmed_at", None),
            getattr(catalog, "uploaded_at", None),
            getattr(newest_definition, "updated_at", None),
        )
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

        client_source = client_batch.source_file if client_batch else container.source_files.filter(kind="CLIENT").first()
        received_source = received_batch.source_file if received_batch else container.source_files.filter(kind="RECEIVED").first()
        upstock_transfer = _upstock_transfer_status(container)
        new_product_transfer = _new_product_transfer_status(container)
        direct_moves = _direct_product_moves_path()

        result.update(
            {
                "current_step": current_step,
                "step1_complete": step1_complete,
                "step2_complete": step2_complete,
                "step3_complete": step3_complete,
                "ready_to_complete": ready_to_complete,
                "advised_units": expected_units,
                "received_units": received_units,
                "variance": variance,
                "exception_count": exception_count,
                "client_manifest": {
                    "status": getattr(client_source, "status", "NOT_LOADED") if client_source else "NOT_LOADED",
                    "filename": getattr(client_source, "original_name", "") if client_source else "",
                    "uploaded_at": iso(getattr(client_source, "uploaded_at", None)) if client_source else None,
                    "confirmed_at": iso(getattr(client_batch, "confirmed_at", None)) if client_batch else None,
                },
                "first_scan": {
                    "status": getattr(received_source, "status", "NOT_LOADED") if received_source else "NOT_LOADED",
                    "filename": getattr(received_source, "original_name", "") if received_source else "",
                    "uploaded_at": iso(getattr(received_source, "uploaded_at", None)) if received_source else None,
                    "confirmed_at": iso(getattr(received_batch, "confirmed_at", None)) if received_batch else None,
                },
                "product_check": {
                    "download_ready": product_check_download_ready,
                    "products_ready": products_ready,
                    "new_product_count": len(new_codes),
                    "pending_new_codes": pending_new_codes,
                    "last_generated_at": iso(getattr(latest_product_check, "generated_at", None)),
                },
                "new_product_import": {
                    "download_ready": new_product_import_download_ready,
                    "last_generated_at": iso(getattr(latest_new_product_import, "generated_at", None)),
                    "last_filename": getattr(latest_new_product_import, "original_name", "") if latest_new_product_import else "",
                },
                "product_moves": {
                    "loaded": bool(moves_import),
                    "rows": getattr(moves_import, "row_count", 0) if moves_import else 0,
                    "products": moves_product_count,
                    "imported_at": iso(getattr(moves_import, "imported_at", None)),
                    "refresh_mode": "Direct Translogic source" if direct_moves else "Local working copy fallback",
                    "source_available": Path(_configured_product_moves_path()).is_file(),
                    "reconciliation_ready": bool(reconciliation and reconciliation.get("ready")),
                    "reconciliation_message": reconciliation.get("message", "") if isinstance(reconciliation, dict) else "",
                },
                "upstockserial": {
                    "download_ready": bool(received_batch and moves_import and reconciliation and reconciliation.get("ready")),
                    "current": upstock_ready,
                    "stale": bool(upstock_stale),
                    "last_generated_at": iso(getattr(latest_upstock, "generated_at", None)),
                    "last_filename": getattr(latest_upstock, "original_name", "") if latest_upstock else "",
                },
                "customer_report": {
                    "download_ready": bool(client_batch and received_batch and catalog),
                    "current": report_ready,
                    "stale": bool(report_stale),
                    "last_generated_at": iso(getattr(latest_report, "generated_at", None)),
                    "last_filename": getattr(latest_report, "original_name", "") if latest_report else "",
                },
            }
        )
        if not container.job_order:
            result["warnings"].append("Job Order is not assigned.")
        if pending_new_codes:
            result["warnings"].append(f"{len(pending_new_codes)} new product code(s) still need complete Translogic product data.")
        if moves_import and reconciliation and not reconciliation.get("ready"):
            result["warnings"].append(reconciliation.get("message") or "PRODUCT_MOVES reconciliation is not ready.")
        if upstock_transfer.get("reason"):
            result["warnings"].append(str(upstock_transfer.get("reason")))
        if new_product_transfer.get("reason") and latest_new_product_import:
            result["warnings"].append(str(new_product_transfer.get("reason")))
    except Exception as exc:
        result["state_error"] = str(exc)
        result["warnings"].append(f"Could not calculate complete workflow state: {exc}")
    return result


class Command(BaseCommand):
    help = "Export a read-only JSON state used by the PON Continuity Snapshot tooling."

    def handle(self, *args, **options):
        now = timezone.now()
        installed = read_installed_release()

        migrations = [
            {"app": row.app, "name": row.name, "applied": iso(row.applied)}
            for row in MigrationRecorder.Migration.objects.filter(app="receiving").order_by("applied", "name")
        ]

        duplicate_job_orders = list(
            Container.objects.exclude(job_order="")
            .values("job_order")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
            .order_by("job_order")
        )
        multiple_active_moves = list(
            ProductMovesImport.objects.filter(active=True)
            .values("container__identifier")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
            .order_by("container__identifier")
        )

        containers = list(Container.objects.select_related("customer").order_by("-created_at"))
        workflow_rows = [workflow_row(container) for container in containers]
        recent = workflow_rows[:20]
        all_container_index = [
            {
                "container_id": row["container_id"],
                "job_order": row["job_order"],
                "customer": row["customer"],
                "status": row["status"],
                "current_step": row.get("current_step"),
                "last_activity_at": row.get("last_activity_at"),
            }
            for row in workflow_rows
        ]
        last_processed = None
        activity_rows = [row for row in workflow_rows if row.get("last_activity_at")]
        if activity_rows:
            last_processed = max(activity_rows, key=lambda row: row["last_activity_at"])

        pending_new_codes = sorted(
            {
                code
                for row in workflow_rows
                for code in ((row.get("product_check") or {}).get("pending_new_codes") or [])
            }
        )

        active_catalogs = list(ProductCatalog.objects.filter(active=True).select_related("customer").order_by("customer__code", "-uploaded_at"))
        catalog_rows = []
        historical_exact_total = 0
        for catalog in active_catalogs:
            dictionary = catalog.name_dictionary or {}
            exact_count = len(dictionary.get("exact") or {})
            historical_exact_total += exact_count
            catalog_rows.append(
                {
                    "customer": catalog.customer.code if catalog.customer_id else "",
                    "original_name": catalog.original_name,
                    "sha256": catalog.sha256,
                    "row_count": catalog.row_count,
                    "uploaded_at": iso(catalog.uploaded_at),
                    "historical_name_matches": exact_count,
                    "learned_abbreviation_rules": len(dictionary.get("rules") or []),
                    "configured_active_abbreviation_rules": catalog.short_name_rules.filter(active=True).count(),
                }
            )

        definitions = ProductDefinition.objects.all()
        definition_count = definitions.count()
        dimension_complete = definitions.filter(
            length_mm__gt=0, height_mm__gt=0, width_mm__gt=0, weight_kg__gt=0
        ).count()
        short_name_missing = definitions.filter(Q(short_name="") | Q(short_name__isnull=True)).count()
        long_name_missing = definitions.filter(Q(full_name="") | Q(full_name__isnull=True)).count()
        group1_missing = definitions.filter(Q(group1="") | Q(group1__isnull=True)).count()

        config_values = {item.key: item.value for item in AppSetting.objects.filter(key__in=EXPORT_DEFAULTS.keys())}
        group2_threshold = config_values.get("TL_GROUP2_CUBIC_THRESHOLD") or EXPORT_DEFAULTS["TL_GROUP2_CUBIC_THRESHOLD"]
        group2_large = config_values.get("TL_GROUP2_LARGE") or EXPORT_DEFAULTS["TL_GROUP2_LARGE"]
        group2_default = config_values.get("TL_GROUP2_DEFAULT")
        if group2_default is None:
            group2_default = EXPORT_DEFAULTS["TL_GROUP2_DEFAULT"]
        group2_large_count = 0
        group2_default_count = 0
        try:
            threshold_value = float(group2_threshold)
            for item in definitions.only("length_mm", "height_mm", "width_mm"):
                cubic = float(calculate_cubic(item.length_mm, item.height_mm, item.width_mm))
                if cubic > threshold_value:
                    group2_large_count += 1
                else:
                    group2_default_count += 1
        except Exception:
            pass

        group1_rules = [
            {
                "family_name": row.family_name,
                "suffix": row.suffix,
                "pon_group1": row.pon_group1,
                "pbp_group1": row.pbp_group1,
                "priority": row.priority,
                "active": row.active,
                "match_phrase_count": len([line for line in (row.match_phrases or "").splitlines() if line.strip()]),
                "updated_at": iso(row.updated_at),
            }
            for row in Group1Family.objects.all()
        ]

        active_abbrev_rules = ShortNameDictionaryRule.objects.filter(active=True)
        inactive_abbrev_rules = ShortNameDictionaryRule.objects.filter(active=False)

        source_file_counts = Counter(SourceFile.objects.values_list("kind", flat=True))
        latest_source_by_kind = {}
        for kind in ("CLIENT", "RECEIVED"):
            item = SourceFile.objects.filter(kind=kind).select_related("container").order_by("-uploaded_at").first()
            latest_source_by_kind[kind] = (
                {
                    "container_id": item.container.identifier,
                    "filename": item.original_name,
                    "status": item.status,
                    "uploaded_at": iso(item.uploaded_at),
                    "sha256": item.sha256,
                }
                if item
                else None
            )

        latest_moves = ProductMovesImport.objects.select_related("container").order_by("-imported_at").first()
        latest_catalog = ProductCatalog.objects.select_related("customer").order_by("-uploaded_at").first()

        customer_sources = [
            {
                "customer": customer.code,
                "product_catalog_source_path": customer.product_catalog_source_path or "",
                "product_catalog_app_path": customer.product_catalog_app_path or "",
            }
            for customer in Customer.objects.order_by("code")
        ]

        counts = {
            "customers": Customer.objects.count(),
            "containers": Container.objects.count(),
            "source_files": SourceFile.objects.count(),
            "import_profiles": ImportProfile.objects.count(),
            "import_batches": ImportBatch.objects.count(),
            "normalized_lines": NormalizedLine.objects.count(),
            "product_catalogs": ProductCatalog.objects.count(),
            "active_product_catalogs": ProductCatalog.objects.filter(active=True).count(),
            "product_catalog_entries": ProductCatalogEntry.objects.count(),
            "active_product_catalog_entries": ProductCatalogEntry.objects.filter(catalog__active=True).count(),
            "product_definitions": definition_count,
            "container_product_statuses": ContainerProductStatus.objects.count(),
            "historical_new_classifications": ContainerProductStatus.objects.filter(was_new=True).count(),
            "product_moves_imports": ProductMovesImport.objects.count(),
            "product_movements": ProductMovement.objects.count(),
            "generated_exports": GeneratedExport.objects.count(),
            "short_name_dictionary_rules": ShortNameDictionaryRule.objects.count(),
            "group1_family_rules": Group1Family.objects.count(),
        }

        warnings = []
        if duplicate_job_orders:
            warnings.append("Duplicate non-blank Job Orders exist.")
        if multiple_active_moves:
            warnings.append("More than one active PRODUCT_MOVES import exists for at least one container.")
        for row in recent:
            for warning in row.get("warnings") or []:
                warnings.append(f"{row['container_id']}: {warning}")
        if not settings.PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED:
            warnings.append("Direct Translogic import mount is disabled; Download/manual transfer remains the safe fallback.")
        if not settings.PON_PRODUCT_MOVES_DIRECT_ENABLED:
            warnings.append("Direct PRODUCT_MOVES mount is disabled; local working-copy/manual-upload fallback remains active.")

        payload = {
            "schema_version": 1,
            "snapshot_at": iso(now),
            "application": {
                "project": "PON Bikes Automation",
                "installed_release": installed,
                "base_dir": str(settings.BASE_DIR),
                "timezone": settings.TIME_ZONE,
                "web_port": "8001",
                "paths": {
                    "container_root_runtime": str(settings.PON_CONTAINER_ROOT),
                    "product_catalog_runtime": str(settings.PON_PRODUCT_CATALOG_PATH),
                    "product_catalog_source_display": str(settings.PON_PRODUCT_CATALOG_SOURCE_DISPLAY),
                    "product_moves_runtime": str(settings.PON_PRODUCT_MOVES_PATH),
                    "product_moves_source_display": str(settings.PON_PRODUCT_MOVES_SOURCE_DISPLAY),
                    "product_moves_working_display": str(settings.PON_PRODUCT_MOVES_WORKING_DISPLAY),
                    "upstock_runtime": str(settings.PON_UPSTOCKSERIAL_PATH),
                    "upstock_working_display": str(settings.PON_UPSTOCK_WORKING_DISPLAY),
                    "upstock_final_display": str(settings.PON_UPSTOCK_FINAL_DISPLAY),
                    "client_report_working_display": str(settings.PON_CLIENT_REPORT_WORKING_DISPLAY),
                    "client_report_final_display": str(settings.PON_CLIENT_REPORT_FINAL_DISPLAY),
                },
                "direct_integration": {
                    "translogic_import_enabled": bool(settings.PON_TRANSLOGIC_IMPORT_DIRECT_ENABLED),
                    "translogic_import_runtime_path": str(settings.PON_TRANSLOGIC_IMPORT_DIRECT_PATH),
                    "product_moves_direct_enabled": bool(settings.PON_PRODUCT_MOVES_DIRECT_ENABLED),
                    "product_moves_direct_runtime_path": str(settings.PON_PRODUCT_MOVES_DIRECT_PATH),
                },
            },
            "database": {
                "vendor": connection.vendor,
                "engine": settings.DATABASES["default"].get("ENGINE", ""),
                "migrations": migrations,
                "counts": counts,
                "integrity": {
                    "duplicate_nonblank_job_orders": duplicate_job_orders,
                    "multiple_active_product_moves_imports": multiple_active_moves,
                },
            },
            "workflow": {
                "container_status_counts": dict(Counter(Container.objects.values_list("status", flat=True))),
                "all_containers": all_container_index,
                "recent_containers": recent,
                "last_container_processed": (
                    {
                        "container_id": last_processed["container_id"],
                        "job_order": last_processed["job_order"],
                        "status": last_processed["status"],
                        "last_activity_at": last_processed.get("last_activity_at"),
                        "last_activity_kind": last_processed.get("last_activity_kind"),
                    }
                    if last_processed
                    else None
                ),
                "latest_uploaded_sources": latest_source_by_kind,
                "source_file_counts": dict(source_file_counts),
            },
            "products": {
                "known_active_catalog_entries": ProductCatalogEntry.objects.filter(catalog__active=True).count(),
                "active_catalogs": catalog_rows,
                "latest_product_master": (
                    {
                        "customer": latest_catalog.customer.code if latest_catalog and latest_catalog.customer_id else "",
                        "filename": latest_catalog.original_name,
                        "row_count": latest_catalog.row_count,
                        "sha256": latest_catalog.sha256,
                        "uploaded_at": iso(latest_catalog.uploaded_at),
                    }
                    if latest_catalog
                    else None
                ),
                "historical_new_classifications": ContainerProductStatus.objects.filter(was_new=True).count(),
                "distinct_historical_new_codes": ContainerProductStatus.objects.filter(was_new=True).values("code").distinct().count(),
                "pending_new_codes": pending_new_codes,
                "product_definitions": definition_count,
                "definitions_with_complete_dimensions": dimension_complete,
                "definitions_with_missing_dimensions": max(definition_count - dimension_complete, 0),
                "definitions_missing_short_name": short_name_missing,
                "definitions_missing_long_name": long_name_missing,
                "definitions_missing_group1": group1_missing,
                "group2": {
                    "threshold_cubic_m3": group2_threshold,
                    "large_value": group2_large,
                    "default_value": group2_default,
                    "definitions_above_threshold": group2_large_count,
                    "definitions_at_or_below_threshold": group2_default_count,
                    "note": "Group2 is derived at New Product Import export time; it is not stored on ProductDefinition.",
                },
            },
            "dictionary": {
                "historical_name_matches": historical_exact_total,
                "active_abbreviation_rules": active_abbrev_rules.count(),
                "inactive_abbreviation_rules": inactive_abbrev_rules.count(),
                "catalogs": catalog_rows,
                "group1_rules": group1_rules,
            },
            "source_references": {
                "customer_product_master_paths": customer_sources,
                "product_master_source_display": str(settings.PON_PRODUCT_CATALOG_SOURCE_DISPLAY),
                "product_moves_source_display": str(settings.PON_PRODUCT_MOVES_SOURCE_DISPLAY),
                "product_moves_working_display": str(settings.PON_PRODUCT_MOVES_WORKING_DISPLAY),
                "upstock_working_display": str(settings.PON_UPSTOCK_WORKING_DISPLAY),
                "upstock_final_display": str(settings.PON_UPSTOCK_FINAL_DISPLAY),
                "client_report_working_display": str(settings.PON_CLIENT_REPORT_WORKING_DISPLAY),
                "latest_product_master_imported_at": iso(latest_catalog.uploaded_at) if latest_catalog else None,
                "latest_product_moves_import": (
                    {
                        "container_id": latest_moves.container.identifier,
                        "filename": latest_moves.original_name,
                        "source_path": latest_moves.source_path,
                        "sha256": latest_moves.sha256,
                        "row_count": latest_moves.row_count,
                        "imported_at": iso(latest_moves.imported_at),
                    }
                    if latest_moves
                    else None
                ),
            },
            "known_warnings": sorted(set(warnings)),
        }

        self.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
