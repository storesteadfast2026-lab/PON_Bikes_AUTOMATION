from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


def populate_rules(apps, schema_editor):
    ProductCatalog = apps.get_model("receiving", "ProductCatalog")
    Rule = apps.get_model("receiving", "ShortNameDictionaryRule")

    pending = []
    for catalog in ProductCatalog.objects.all().iterator():
        dictionary = catalog.name_dictionary or {}
        for learned in dictionary.get("rules", []):
            source = str(learned.get("source", "") or "").strip().upper()
            target = str(learned.get("target", "") or "").strip()
            if not source or not target:
                continue
            confidence = learned.get("confidence", 0) or 0
            pending.append(
                Rule(
                    catalog_id=catalog.pk,
                    source=source,
                    target=target,
                    occurrence_count=int(learned.get("count", 0) or 0),
                    confidence=Decimal(str(confidence)),
                    saving=len(source) - len(target),
                    active=True,
                )
            )
    if pending:
        Rule.objects.bulk_create(pending, batch_size=1000, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ("receiving", "0006_group1_family_mapping"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShortNameDictionaryRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(help_text="Original word/token detected in LongName, for example KALKHOFF.", max_length=100, verbose_name="Original word")),
                ("target", models.CharField(help_text="Abbreviation used when suggesting ShortName, for example KH.", max_length=100, verbose_name="Abbreviation")),
                ("occurrence_count", models.PositiveIntegerField(default=0, help_text="Number of supporting LongName/ShortName examples in this XML catalogue.", verbose_name="Occurrences")),
                ("confidence", models.DecimalField(decimal_places=4, default=0, help_text="Agreement ratio learned from the XML, from 0 to 1.", max_digits=5, verbose_name="Confidence")),
                ("saving", models.IntegerField(default=0, help_text="Characters saved by this abbreviation.", verbose_name="Characters saved")),
                ("active", models.BooleanField(default=True, help_text="Only active rules are used for new ShortName suggestions.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("catalog", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="short_name_rules", to="receiving.productcatalog")),
            ],
            options={
                "verbose_name": "Short name dictionary rule",
                "verbose_name_plural": "Short name dictionary",
                "ordering": ["-saving", "-occurrence_count", "source"],
            },
        ),
        migrations.AddConstraint(
            model_name="shortnamedictionaryrule",
            constraint=models.UniqueConstraint(fields=("catalog", "source"), name="unique_short_name_rule_per_catalog_source"),
        ),
        migrations.RunPython(populate_rules, migrations.RunPython.noop),
    ]
