from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("receiving", "0003_generatedexport_productdefinition"),
    ]

    operations = [
        migrations.AddField(
            model_name="container",
            name="container_date",
            field=models.DateField(
                blank=True,
                help_text="Operational container date exported in column AD of New Product Import.",
                null=True,
            ),
        ),
    ]
