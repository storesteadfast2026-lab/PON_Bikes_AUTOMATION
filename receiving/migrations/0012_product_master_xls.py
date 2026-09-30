from django.db import migrations, models
import django.db.models.deletion


OLD_NAME = "products_pon_pbp_auto.xml"
NEW_NAME = "products_pon_pbp_auto.xls"


def switch_known_catalog_paths_to_xls(apps, schema_editor):
    Customer = apps.get_model("receiving", "Customer")
    for customer in Customer.objects.all():
        changed = []
        for field in ("product_catalog_source_path", "product_catalog_app_path"):
            value = getattr(customer, field, "") or ""
            lower = value.lower()
            pos = lower.find(OLD_NAME.lower())
            if pos >= 0:
                setattr(customer, field, value[:pos] + NEW_NAME + value[pos + len(OLD_NAME):])
                changed.append(field)
        if changed:
            customer.save(update_fields=changed)


def reverse_known_catalog_paths_to_xml(apps, schema_editor):
    Customer = apps.get_model("receiving", "Customer")
    for customer in Customer.objects.all():
        changed = []
        for field in ("product_catalog_source_path", "product_catalog_app_path"):
            value = getattr(customer, field, "") or ""
            lower = value.lower()
            pos = lower.find(NEW_NAME.lower())
            if pos >= 0:
                setattr(customer, field, value[:pos] + OLD_NAME + value[pos + len(NEW_NAME):])
                changed.append(field)
        if changed:
            customer.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [
        ("receiving", "0011_container_job_order"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customer",
            name="product_catalog_source_path",
            field=models.CharField(
                blank=True,
                help_text="Operator-facing Windows/network location of this customer's product master file.",
                max_length=500,
            ),
        ),
        migrations.AlterField(
            model_name="customer",
            name="product_catalog_app_path",
            field=models.CharField(
                blank=True,
                help_text="Path the application reads (for example /data/pon_products/customer.xls in Docker).",
                max_length=500,
            ),
        ),
        migrations.AlterField(
            model_name="productcatalog",
            name="customer",
            field=models.ForeignKey(
                blank=True,
                help_text="Customer configuration this imported product master belongs to.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="product_catalogs",
                to="receiving.customer",
            ),
        ),
        migrations.RunPython(switch_known_catalog_paths_to_xls, reverse_known_catalog_paths_to_xml),
    ]
