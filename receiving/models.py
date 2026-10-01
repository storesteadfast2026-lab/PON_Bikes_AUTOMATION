from django.conf import settings
from django.db import models
from django.utils import timezone


class Customer(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    product_catalog_source_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Operator-facing Windows/network location of this customer's product master file.",
    )
    product_catalog_app_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Path the application reads (for example /data/pon_products/customer.xls in Docker).",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class AppSetting(models.Model):
    key = models.CharField(max_length=80, unique=True)
    value = models.TextField(blank=True)
    description = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key


class Container(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("OPEN", "Open"),
        ("REVIEW", "Under review"),
        ("READY", "Ready for Translogic"),
        ("CLOSED", "Closed"),
    ]

    identifier = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="containers")
    container_date = models.DateField(
        null=True,
        blank=True,
        help_text="Operational container date exported in column AD of New Product Import.",
    )
    year = models.PositiveSmallIntegerField(default=2026)
    job_order = models.CharField(max_length=40, blank=True, db_index=True, help_text="Translogic Job Order used later to find the receiving job.")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="OPEN")
    auto_created_from_manifest = models.BooleanField(default=False)
    manifest_source_name = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_containers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["job_order"],
                condition=~models.Q(job_order=""),
                name="unique_nonblank_container_job_order",
            )
        ]

    def save(self, *args, **kwargs):
        self.job_order = (self.job_order or "").strip().upper()
        if self.status == "PENDING" and self.job_order:
            self.status = "OPEN"
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = list(set(update_fields) | {"job_order", "status"})
        super().save(*args, **kwargs)

    def __str__(self):
        return self.identifier


def source_upload_path(instance, filename):
    safe_container = instance.container.identifier.replace("/", "-").replace("\\", "-")
    return f"containers/{instance.container.year}/{safe_container}/source/{filename}"


def product_catalog_upload_path(instance, filename):
    return f"product_catalogs/{timezone.now():%Y/%m}/{filename}"


def generated_export_path(instance, filename):
    safe_container = instance.container.identifier.replace("/", "-").replace("\\", "-")
    return f"containers/{instance.container.year}/{safe_container}/exports/{filename}"


def product_moves_upload_path(instance, filename):
    safe_container = instance.container.identifier.replace("/", "-").replace("\\", "-")
    return f"containers/{instance.container.year}/{safe_container}/stage2/{filename}"


def first_scan_photo_upload_path(instance, filename):
    container = instance.session.container
    safe_container = container.identifier.replace("/", "-").replace("\\", "-")
    return f"containers/{container.year}/{safe_container}/first_scan_photos/{filename}"


class ProductCatalog(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="product_catalogs",
        null=True,
        blank=True,
        help_text="Customer configuration this imported product master belongs to.",
    )
    file = models.FileField(upload_to=product_catalog_upload_path)
    original_name = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64)
    row_count = models.PositiveIntegerField(default=0)
    name_dictionary = models.JSONField(default=dict, blank=True)
    active = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def effective_name_dictionary(self):
        """Return exact mappings plus the editable/admin-controlled token rules."""
        dictionary = dict(self.name_dictionary or {})
        configured_rules = list(self.short_name_rules.all())
        if configured_rules:
            dictionary["rules"] = [
                rule.as_dictionary_rule()
                for rule in configured_rules
                if rule.active
            ]
        return dictionary

    def sync_short_name_rules(self):
        """Create missing admin rules from the learned JSON without overwriting admin edits."""
        for learned in (self.name_dictionary or {}).get("rules", []):
            source = str(learned.get("source", "") or "").strip().upper()
            target = str(learned.get("target", "") or "").strip()
            if not source or not target:
                continue
            rule, created = self.short_name_rules.get_or_create(
                source=source,
                defaults={
                    "target": target,
                    "occurrence_count": int(learned.get("count", 0) or 0),
                    "confidence": learned.get("confidence", 0) or 0,
                    "saving": int(learned.get("saving", len(source) - len(target)) or 0),
                    "active": True,
                },
            )
            if not created:
                # Preserve target/active because they may have been deliberately changed in Admin.
                rule.occurrence_count = int(learned.get("count", 0) or 0)
                rule.confidence = learned.get("confidence", 0) or 0
                rule.save(update_fields=["occurrence_count", "confidence", "saving", "updated_at"])

    def __str__(self):
        prefix = f"{self.customer.code} · " if self.customer_id else ""
        return f"{prefix}{self.original_name} ({self.row_count} products)"


class ShortNameDictionaryRule(models.Model):
    """Editable token-level abbreviation learned from a product master file catalogue."""

    catalog = models.ForeignKey(
        ProductCatalog,
        on_delete=models.CASCADE,
        related_name="short_name_rules",
    )
    source = models.CharField(
        "Original word",
        max_length=100,
        help_text="Original word/token detected in LongName, for example KALKHOFF.",
    )
    target = models.CharField(
        "Abbreviation",
        max_length=100,
        help_text="Abbreviation used when suggesting ShortName, for example KH.",
    )
    occurrence_count = models.PositiveIntegerField(
        "Occurrences",
        default=0,
        help_text="Number of supporting LongName/ShortName examples in this product master catalogue.",
    )
    confidence = models.DecimalField(
        "Confidence",
        max_digits=5,
        decimal_places=4,
        default=0,
        help_text="Agreement ratio learned from the product master, from 0 to 1.",
    )
    saving = models.IntegerField(
        "Characters saved",
        default=0,
        help_text="Characters saved by this abbreviation.",
    )
    active = models.BooleanField(
        default=True,
        help_text="Only active rules are used for new ShortName suggestions.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-saving", "-occurrence_count", "source"]
        constraints = [
            models.UniqueConstraint(
                fields=["catalog", "source"],
                name="unique_short_name_rule_per_catalog_source",
            )
        ]
        verbose_name = "Short name dictionary rule"
        verbose_name_plural = "Short name dictionary"

    def save(self, *args, **kwargs):
        self.source = (self.source or "").strip().upper()
        self.target = (self.target or "").strip()
        self.saving = len(self.source) - len(self.target)
        super().save(*args, **kwargs)

    def as_dictionary_rule(self):
        return {
            "source": self.source,
            "target": self.target,
            "count": self.occurrence_count,
            "confidence": float(self.confidence),
            "saving": self.saving,
        }

    def __str__(self):
        return f"{self.source} → {self.target}"


class ProductCatalogEntry(models.Model):
    catalog = models.ForeignKey(ProductCatalog, on_delete=models.CASCADE, related_name="entries")
    source_row = models.PositiveIntegerField()
    code = models.CharField(max_length=160, blank=True, db_index=True)
    pon_sku = models.CharField(max_length=160, blank=True, db_index=True)
    customer = models.CharField(max_length=80, blank=True, db_index=True)
    code2 = models.CharField(max_length=160, blank=True, db_index=True)
    short_name = models.CharField(max_length=30, blank=True)
    long_name = models.CharField(max_length=255, blank=True)
    group1 = models.CharField(max_length=20, blank=True, db_index=True)
    group2 = models.CharField(max_length=20, blank=True, db_index=True)
    raw_data = models.JSONField(default=dict)

    class Meta:
        ordering = ["source_row", "id"]
        indexes = [
            models.Index(fields=["catalog", "code"]),
            models.Index(fields=["catalog", "pon_sku"]),
            models.Index(fields=["catalog", "code2"]),
        ]

    def __str__(self):
        return self.pon_sku or self.code2 or self.code


class Group1Family(models.Model):
    """Configurable relationship between a product family and its Translogic Group1 suffix."""

    family_name = models.CharField(max_length=100, unique=True)
    suffix = models.CharField(
        max_length=8,
        unique=True,
        help_text="Group1 suffix only, for example CVL, SCZ or KHF. The customer prefix (PON/PBP) is added automatically.",
    )
    match_phrases = models.TextField(
        help_text="One identifying phrase per line. Matching is case-insensitive. More specific families should use a higher priority.",
    )
    priority = models.IntegerField(
        default=100,
        help_text="Higher priority wins when a description also matches a broader family rule.",
    )
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "family_name"]
        verbose_name = "Group1 family mapping"
        verbose_name_plural = "Group1 family mappings"

    def save(self, *args, **kwargs):
        self.suffix = (self.suffix or "").strip().upper()
        super().save(*args, **kwargs)

    @property
    def pon_group1(self):
        return f"PON{self.suffix}" if self.suffix else ""

    @property
    def pbp_group1(self):
        return f"PBP{self.suffix}" if self.suffix else ""

    def __str__(self):
        return f"{self.family_name} → {self.suffix}"


class ContainerProductStatus(models.Model):
    """Historical new/existing classification for a product in one receiving container."""

    container = models.ForeignKey(Container, on_delete=models.CASCADE, related_name="product_statuses")
    code = models.CharField(max_length=100)
    was_new = models.BooleanField(default=False)
    import_classification = models.CharField(max_length=20, blank=True)
    import_history = models.JSONField(default=dict, blank=True)
    classified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["container", "code"], name="unique_container_product_status")
        ]
        verbose_name = "Container product status"
        verbose_name_plural = "Container product statuses"

    def __str__(self):
        return f"{self.container.identifier}: {self.code} ({'New' if self.was_new else 'Existing'})"


class ProductDefinition(models.Model):
    """Reusable Translogic product data, stored once per physical product model."""

    code = models.CharField(max_length=100, unique=True)
    long_code = models.CharField(max_length=160, blank=True)
    short_name = models.CharField(max_length=30)
    full_name = models.CharField(max_length=255)
    group1 = models.CharField(max_length=20, blank=True, db_index=True)
    group1_family = models.ForeignKey(
        Group1Family,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="product_definitions",
    )
    length_mm = models.PositiveIntegerField()
    height_mm = models.PositiveIntegerField()
    width_mm = models.PositiveIntegerField()
    weight_kg = models.DecimalField(max_digits=10, decimal_places=3)
    confirmed = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_product_definitions"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="updated_product_definitions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code


class GeneratedExport(models.Model):
    KIND_CHOICES = [
        ("PRODUCT_CHECK", "Product check and barcodes"),
        ("NEW_PRODUCT", "New Product Import"),
        ("UPSTOCK_SERIAL", "UPStockSerial.csv"),
        ("CLIENT_REPORT", "Client receiving report (.xlsx)"),
    ]

    container = models.ForeignKey(Container, on_delete=models.CASCADE, related_name="generated_exports")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    file = models.FileField(upload_to=generated_export_path)
    original_name = models.CharField(max_length=255)
    file_format = models.CharField(max_length=30)
    row_count = models.PositiveIntegerField(default=0)
    sha256 = models.CharField(max_length=64)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return self.original_name


class ProductMovesImport(models.Model):
    """Snapshot of PRODUCT_MOVES.CSV exported by Translogic for one container."""

    container = models.ForeignKey(Container, on_delete=models.CASCADE, related_name="product_moves_imports")
    file = models.FileField(upload_to=product_moves_upload_path)
    original_name = models.CharField(max_length=255, default="PRODUCT_MOVES.CSV")
    source_path = models.CharField(max_length=500, blank=True)
    sha256 = models.CharField(max_length=64, db_index=True)
    row_count = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    imported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-imported_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["container", "sha256"],
                name="unique_product_moves_snapshot_per_container",
            )
        ]
        verbose_name = "PRODUCT_MOVES import"
        verbose_name_plural = "PRODUCT_MOVES imports"

    def __str__(self):
        return f"{self.container.identifier}: {self.original_name} ({self.row_count})"


class ProductMovement(models.Model):
    import_batch = models.ForeignKey(ProductMovesImport, on_delete=models.CASCADE, related_name="rows")
    source_row = models.PositiveIntegerField()
    product = models.CharField(max_length=100, db_index=True)
    movement = models.CharField(max_length=20, db_index=True)

    class Meta:
        ordering = ["source_row", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["import_batch", "movement"],
                name="unique_movement_per_product_moves_import",
            )
        ]

    def __str__(self):
        return f"{self.product} → {self.movement}"


class SourceFile(models.Model):
    KIND_CHOICES = [
        ("CLIENT", "Client manifest"),
        ("RECEIVED", "First scan / received bikes"),
    ]
    STATUS_CHOICES = [
        ("UPLOADED", "Uploaded"),
        ("PREVIEW", "Preview ready"),
        ("CONFIRMED", "Confirmed"),
        ("ERROR", "Error"),
    ]

    container = models.ForeignKey(Container, on_delete=models.CASCADE, related_name="source_files")
    kind = models.CharField(max_length=12, choices=KIND_CHOICES)
    file = models.FileField(upload_to=source_upload_path)
    original_name = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64, db_index=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="UPLOADED")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        constraints = [
            models.UniqueConstraint(fields=["container", "kind", "sha256"], name="unique_source_per_container_kind")
        ]

    def __str__(self):
        return self.original_name


class ImportProfile(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="import_profiles")
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=12, choices=SourceFile.KIND_CHOICES)
    mapping = models.JSONField(default=dict)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("customer", "name", "kind")]

    def __str__(self):
        return f"{self.customer.code}: {self.name}"


class ImportBatch(models.Model):
    STATUS_CHOICES = [("PREVIEW", "Preview"), ("CONFIRMED", "Confirmed"), ("SUPERSEDED", "Superseded")]

    source_file = models.ForeignKey(SourceFile, on_delete=models.CASCADE, related_name="batches")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="PREVIEW")
    mapping = models.JSONField(default=dict)
    total_rows = models.PositiveIntegerField(default=0)
    total_units = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def container(self):
        return self.source_file.container


class NormalizedLine(models.Model):
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="lines")
    source_sheet = models.CharField(max_length=100)
    source_row = models.PositiveIntegerField()
    code = models.CharField(max_length=100, db_index=True)
    long_code = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)
    location = models.CharField(max_length=30, blank=True)
    fill_signature = models.CharField(max_length=120, blank=True)
    raw_data = models.JSONField(default=dict)
    container_identifier = models.CharField(max_length=30, blank=True, db_index=True)

    class Meta:
        ordering = ["source_row", "id"]

    def __str__(self):
        return f"{self.code} x {self.quantity}"


class FirstScanSession(models.Model):
    MODE_CHOICES = [
        ("AUTO", "Auto"),
        ("CODE", "Code"),
        ("LONG_CODE", "Long Code"),
    ]
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("PAUSED", "Paused"),
        ("FINISHED", "Finished"),
    ]

    container = models.ForeignKey(Container, on_delete=models.CASCADE, related_name="first_scan_sessions")
    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT, related_name="first_scan_sessions")
    mode = models.CharField(max_length=12, choices=MODE_CHOICES, default="AUTO")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="ACTIVE")
    current_pallet = models.CharField(max_length=30, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["container"],
                condition=models.Q(status__in=["ACTIVE", "PAUSED"]),
                name="unique_open_first_scan_session_per_container",
            )
        ]

    def __str__(self):
        return f"{self.container.identifier} · {self.get_status_display()}"


class FirstScanPause(models.Model):
    session = models.ForeignKey(FirstScanSession, on_delete=models.CASCADE, related_name="pauses")
    started_at = models.DateTimeField(default=timezone.now)
    resumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["started_at", "id"]


class FirstScanEvent(models.Model):
    EVENT_CHOICES = [("PALLET", "Pallet"), ("BIKE", "Bike")]
    INPUT_CHOICES = [("PALLET", "Pallet"), ("CODE", "Code"), ("LONG_CODE", "Long Code")]
    RESULT_CHOICES = [("SUCCESS", "Success"), ("WARNING", "Warning"), ("ERROR", "Error")]

    session = models.ForeignKey(FirstScanSession, on_delete=models.CASCADE, related_name="events")
    normalized_line = models.OneToOneField(
        NormalizedLine,
        on_delete=models.SET_NULL,
        related_name="first_scan_event",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=10, choices=EVENT_CHOICES)
    input_type = models.CharField(max_length=12, choices=INPUT_CHOICES)
    result = models.CharField(max_length=10, choices=RESULT_CHOICES)
    scanned_value = models.CharField(max_length=180)
    resolved_code = models.CharField(max_length=100, blank=True)
    long_code = models.CharField(max_length=160, blank=True)
    pallet = models.CharField(max_length=30, blank=True)
    message = models.CharField(max_length=255, blank=True)
    scanned_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-scanned_at", "-id"]


class FirstScanPhoto(models.Model):
    session = models.ForeignKey(FirstScanSession, on_delete=models.CASCADE, related_name="photos")
    event = models.ForeignKey(
        FirstScanEvent,
        on_delete=models.SET_NULL,
        related_name="photos",
        null=True,
        blank=True,
    )
    file = models.FileField(upload_to=first_scan_photo_upload_path)
    pallet = models.CharField(max_length=30, blank=True)
    captured_at = models.DateTimeField(default=timezone.now)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ["-captured_at", "-id"]
