from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("receiving", "0008_stage2_product_moves")]

    operations = [
        migrations.CreateModel(
            name="ContainerProductStatus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=100)),
                ("was_new", models.BooleanField(default=False)),
                ("classified_at", models.DateTimeField(auto_now_add=True)),
                (
                    "container",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="product_statuses", to="receiving.container"),
                ),
            ],
            options={
                "verbose_name": "Container product status",
                "verbose_name_plural": "Container product statuses",
                "ordering": ["code"],
            },
        ),
        migrations.AddConstraint(
            model_name="containerproductstatus",
            constraint=models.UniqueConstraint(fields=("container", "code"), name="unique_container_product_status"),
        ),
        migrations.AlterField(
            model_name="generatedexport",
            name="kind",
            field=models.CharField(
                choices=[
                    ("PRODUCT_CHECK", "Product check and barcodes"),
                    ("NEW_PRODUCT", "New Product Import"),
                    ("UPSTOCK_SERIAL", "UPStockSerial.csv"),
                    ("CLIENT_REPORT", "Client receiving report (.xlsx)"),
                ],
                max_length=20,
            ),
        ),
    ]
