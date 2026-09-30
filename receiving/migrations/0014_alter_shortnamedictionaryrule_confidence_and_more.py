from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("receiving", "0013_multi_container_job_order"),
    ]

    operations = [
        migrations.AlterField(
            model_name="shortnamedictionaryrule",
            name="confidence",
            field=models.DecimalField(
                "Confidence",
                decimal_places=4,
                default=0,
                help_text="Agreement ratio learned from the product master, from 0 to 1.",
                max_digits=5,
            ),
        ),
        migrations.AlterField(
            model_name="shortnamedictionaryrule",
            name="occurrence_count",
            field=models.PositiveIntegerField(
                "Occurrences",
                default=0,
                help_text="Number of supporting LongName/ShortName examples in this product master catalogue.",
            ),
        ),
    ]
