from django.db import migrations, models
import django.db.models.deletion


PON_SOURCE = r"C:\Docker-Projects\Freight-Calc-v1.6\uploaded_data\products_pon_pbp_auto.xml"
PON_APP = "/data/pon_products/products_pon_pbp_auto.xml"


def seed_customer_catalog_config(apps, schema_editor):
    Customer = apps.get_model("receiving", "Customer")
    ProductCatalog = apps.get_model("receiving", "ProductCatalog")

    pon = Customer.objects.filter(code__iexact="PON").first()
    if pon:
        changed = []
        if not pon.product_catalog_source_path:
            pon.product_catalog_source_path = PON_SOURCE
            changed.append("product_catalog_source_path")
        if not pon.product_catalog_app_path:
            pon.product_catalog_app_path = PON_APP
            changed.append("product_catalog_app_path")
        if changed:
            pon.save(update_fields=changed)
        ProductCatalog.objects.filter(customer__isnull=True).update(customer=pon)

    # PBP currently shares the PON/PBP XML unless/until an administrator gives it
    # a different source. Keeping the paths visible makes that relationship explicit.
    pbp = Customer.objects.filter(code__iexact="PBP").first()
    if pbp:
        changed = []
        if not pbp.product_catalog_source_path:
            pbp.product_catalog_source_path = PON_SOURCE
            changed.append("product_catalog_source_path")
        if not pbp.product_catalog_app_path:
            pbp.product_catalog_app_path = PON_APP
            changed.append("product_catalog_app_path")
        if changed:
            pbp.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [("receiving", "0009_client_receiving_report")]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="product_catalog_source_path",
            field=models.CharField(
                blank=True,
                help_text="Operator-facing Windows/network location of this customer's product XML.",
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name="customer",
            name="product_catalog_app_path",
            field=models.CharField(
                blank=True,
                help_text="Path the application reads (for example /data/pon_products/customer.xml in Docker).",
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name="productcatalog",
            name="customer",
            field=models.ForeignKey(
                blank=True,
                help_text="Customer configuration this imported XML belongs to.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="product_catalogs",
                to="receiving.customer",
            ),
        ),
        migrations.AlterField(
            model_name="productcatalog",
            name="sha256",
            field=models.CharField(max_length=64),
        ),
        migrations.RunPython(seed_customer_catalog_config, migrations.RunPython.noop),
    ]
