from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("receiving", "0017_second_scan_operational"),
    ]

    operations = [
        migrations.AddField(
            model_name="container",
            name="first_scan_code_mode",
            field=models.CharField(
                blank=True,
                choices=[("ONE_CODE", "1 CODE"), ("TWO_CODES", "2 CODES")],
                help_text="Container-wide First Scan bike mode, selected once before scanning.",
                max_length=10,
            ),
        ),
    ]
