from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("receiving", "0004_container_container_date"),
    ]

    operations = [
        migrations.AddField(model_name="productcatalog", name="name_dictionary", field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name="productcatalogentry", name="short_name", field=models.CharField(blank=True, max_length=30)),
        migrations.AddField(model_name="productcatalogentry", name="long_name", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="productcatalogentry", name="group1", field=models.CharField(blank=True, db_index=True, max_length=20)),
        migrations.AddField(model_name="productcatalogentry", name="group2", field=models.CharField(blank=True, db_index=True, max_length=20)),
    ]
