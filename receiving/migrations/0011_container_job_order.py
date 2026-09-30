from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("receiving", "0010_customer_product_catalog_configuration"),
    ]

    operations = [
        migrations.AddField(
            model_name="container",
            name="job_order",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Translogic Job Order used later to find the receiving job.",
                max_length=40,
            ),
        ),
    ]
