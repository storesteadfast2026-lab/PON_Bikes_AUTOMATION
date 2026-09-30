from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import receiving.models


class Migration(migrations.Migration):

    dependencies = [
        ("receiving", "0007_short_name_dictionary_rule"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="generatedexport",
            name="kind",
            field=models.CharField(
                choices=[
                    ("PRODUCT_CHECK", "Product check and barcodes"),
                    ("NEW_PRODUCT", "New Product Import"),
                    ("UPSTOCK_SERIAL", "UPStockSerial.csv"),
                ],
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="ProductMovesImport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to=receiving.models.product_moves_upload_path)),
                ("original_name", models.CharField(default="PRODUCT_MOVES.CSV", max_length=255)),
                ("source_path", models.CharField(blank=True, max_length=500)),
                ("sha256", models.CharField(db_index=True, max_length=64)),
                ("row_count", models.PositiveIntegerField(default=0)),
                ("active", models.BooleanField(default=True)),
                ("imported_at", models.DateTimeField(auto_now_add=True)),
                (
                    "container",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="product_moves_imports", to="receiving.container"),
                ),
                (
                    "imported_by",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "verbose_name": "PRODUCT_MOVES import",
                "verbose_name_plural": "PRODUCT_MOVES imports",
                "ordering": ["-imported_at"],
            },
        ),
        migrations.CreateModel(
            name="ProductMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_row", models.PositiveIntegerField()),
                ("product", models.CharField(db_index=True, max_length=100)),
                ("movement", models.CharField(db_index=True, max_length=20)),
                (
                    "import_batch",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rows", to="receiving.productmovesimport"),
                ),
            ],
            options={"ordering": ["source_row", "id"]},
        ),
        migrations.AddConstraint(
            model_name="productmovesimport",
            constraint=models.UniqueConstraint(
                fields=("container", "sha256"),
                name="unique_product_moves_snapshot_per_container",
            ),
        ),
        migrations.AddConstraint(
            model_name="productmovement",
            constraint=models.UniqueConstraint(
                fields=("import_batch", "movement"),
                name="unique_movement_per_product_moves_import",
            ),
        ),
    ]
