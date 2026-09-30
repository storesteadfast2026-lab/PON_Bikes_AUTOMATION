from django.contrib import admin

from .models import (
    AppSetting,
    Container,
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
    ShortNameDictionaryRule,
    SourceFile,
)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "catalog_filename", "product_catalog_source_path"]
    search_fields = ["code", "name", "product_catalog_source_path", "product_catalog_app_path"]
    fieldsets = [
        ("Customer", {"fields": ["code", "name"]}),
        ("Product master (Excel .xls)", {"fields": ["product_catalog_source_path", "product_catalog_app_path"]}),
    ]

    @admin.display(description="Product master")
    def catalog_filename(self, obj):
        import ntpath
        value = obj.product_catalog_source_path or obj.product_catalog_app_path
        return ntpath.basename(value.replace("/", "\\")) if value else "Not configured"


@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ["job_order", "identifier", "customer", "container_date", "year", "status", "auto_created_from_manifest", "created_at"]
    list_filter = ["container_date", "year", "status", "customer", "auto_created_from_manifest"]
    search_fields = ["identifier", "job_order"]


@admin.register(SourceFile)
class SourceFileAdmin(admin.ModelAdmin):
    list_display = ["original_name", "container", "kind", "status", "uploaded_at"]
    list_filter = ["kind", "status"]
    readonly_fields = ["sha256", "uploaded_at"]


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ["source_file", "status", "total_rows", "total_units", "created_at"]
    list_filter = ["status"]


admin.site.register(AppSetting)
admin.site.register(ImportProfile)
admin.site.register(NormalizedLine)


@admin.register(ProductCatalog)
class ProductCatalogAdmin(admin.ModelAdmin):
    list_display = ["customer", "original_name", "row_count", "active", "uploaded_at", "uploaded_by"]
    list_filter = ["customer", "active", "uploaded_at"]
    readonly_fields = ["sha256", "row_count", "uploaded_at"]
    exclude = ["name_dictionary"]


@admin.register(ShortNameDictionaryRule)
class ShortNameDictionaryRuleAdmin(admin.ModelAdmin):
    list_display = [
        "source",
        "target",
        "occurrence_count",
        "confidence_percent",
        "saving",
        "active",
        "catalog",
    ]
    list_filter = ["active", "catalog"]
    search_fields = ["source", "target"]
    list_editable = ["target", "active"]
    ordering = ["-saving", "-occurrence_count", "source"]
    list_per_page = 100

    @admin.display(description="Confidence", ordering="confidence")
    def confidence_percent(self, obj):
        return f"{float(obj.confidence) * 100:.1f}%"

    def get_readonly_fields(self, request, obj=None):
        learned_fields = ["occurrence_count", "confidence", "saving", "created_at", "updated_at"]
        if obj:
            # Keep the learned source/catalog stable; target and Active remain editable.
            return ["source", "catalog", *learned_fields]
        return learned_fields

    def has_delete_permission(self, request, obj=None):
        # Deactivate a rule instead of deleting its product-master-derived audit trail.
        return False


@admin.register(ProductCatalogEntry)
class ProductCatalogEntryAdmin(admin.ModelAdmin):
    list_display = ["pon_sku", "code", "code2", "customer", "short_name", "group1", "group2", "catalog", "source_row"]
    list_filter = ["customer", "group1", "group2", "catalog"]
    search_fields = ["pon_sku", "code", "code2", "short_name", "long_name"]


@admin.register(Group1Family)
class Group1FamilyAdmin(admin.ModelAdmin):
    list_display = ["family_name", "suffix", "pon_value", "pbp_value", "priority", "active", "updated_at"]
    list_filter = ["active"]
    search_fields = ["family_name", "suffix", "match_phrases", "notes"]
    ordering = ["-priority", "family_name"]

    @admin.display(description="PON Group1")
    def pon_value(self, obj):
        return obj.pon_group1

    @admin.display(description="PBP Group1")
    def pbp_value(self, obj):
        return obj.pbp_group1


@admin.register(ProductDefinition)
class ProductDefinitionAdmin(admin.ModelAdmin):
    list_display = ["code", "short_name", "group1", "group1_family", "length_mm", "height_mm", "width_mm", "weight_kg", "confirmed", "updated_at"]
    list_filter = ["group1", "group1_family", "confirmed", "updated_at"]
    search_fields = ["code", "long_code", "short_name", "full_name", "group1"]


@admin.register(GeneratedExport)
class GeneratedExportAdmin(admin.ModelAdmin):
    list_display = ["original_name", "container", "kind", "file_format", "row_count", "generated_by", "generated_at"]
    list_filter = ["kind", "file_format", "generated_at"]
    readonly_fields = ["sha256", "generated_at"]


@admin.register(ProductMovesImport)
class ProductMovesImportAdmin(admin.ModelAdmin):
    list_display = ["container", "original_name", "row_count", "active", "imported_by", "imported_at"]
    list_filter = ["active", "imported_at"]
    search_fields = ["container__identifier", "original_name", "sha256", "source_path"]
    readonly_fields = ["sha256", "row_count", "imported_at"]


@admin.register(ProductMovement)
class ProductMovementAdmin(admin.ModelAdmin):
    list_display = ["product", "movement", "import_batch", "source_row"]
    search_fields = ["product", "movement", "import_batch__container__identifier"]
    list_filter = ["import_batch__container"]
    readonly_fields = ["import_batch", "source_row", "product", "movement"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
