from django.db import migrations, models
import django.db.models.deletion


def seed_group1_families(apps, schema_editor):
    Group1Family = apps.get_model("receiving", "Group1Family")
    AppSetting = apps.get_model("receiving", "AppSetting")
    rules = [
        {"family_name": "Focus E-Bikes", "suffix": "FEB", "match_phrases": "focus e bikes\nfocus e bike\nfocus ebike\nfocus e-bike", "priority": 220, "notes": "Specific Focus electric-bike family. Higher priority than general Focus."},
        {"family_name": "Kalkhoff Non E-Bikes", "suffix": "KNE", "match_phrases": "kalkhoff non ebikes\nkalkhoff non ebike\nkalkhoff non e-bikes\nkalkhoff non e-bike", "priority": 220, "notes": "Specific Kalkhoff non-electric family. Higher priority than general Kalkhoff."},
        {"family_name": "Cervelo", "suffix": "CVL", "match_phrases": "cervelo\nC26\nC27", "priority": 100, "notes": "PONCVL / PBPCVL. C26/C27 prefixes are supported by the current XML for complete bicycles; future unknown prefixes must be reviewed."},
        {"family_name": "Santa Cruz", "suffix": "SCZ", "match_phrases": "santa cruz\nSC26\nSC27", "priority": 100, "notes": "Complete Santa Cruz bicycle family: PONSCZ / PBPSCZ. SCP is intentionally not inferred for new bicycles."},
        {"family_name": "Focus", "suffix": "FCS", "match_phrases": "focus\nF26", "priority": 100, "notes": "General/current Focus bicycle family. The current XML consistently maps F26 bicycles to FCS; explicit legacy 'Focus E Bikes' text is handled by FEB."},
        {"family_name": "Kalkhoff", "suffix": "KHF", "match_phrases": "kalkhoff\nK26", "priority": 100, "notes": "General/current Kalkhoff family. K26 is supported by the current XML. Explicit Non E-Bikes are handled by KNE."},
        {"family_name": "Gazelle", "suffix": "GAZ", "match_phrases": "gazelle", "priority": 100, "notes": "PONGAZ in the XML master."},
        {"family_name": "Reserve", "suffix": "RSV", "match_phrases": "reserve", "priority": 100, "notes": "Reserve family: PONRSV / PBPRSV. Included because the XML relation is clear."},
    ]
    for rule in rules:
        Group1Family.objects.update_or_create(family_name=rule["family_name"], defaults=rule)
    AppSetting.objects.filter(key="TL_GROUP1").delete()


def reverse_seed(apps, schema_editor):
    Group1Family = apps.get_model("receiving", "Group1Family")
    Group1Family.objects.filter(family_name__in=[
        "Focus E-Bikes", "Kalkhoff Non E-Bikes", "Cervelo", "Santa Cruz", "Focus", "Kalkhoff", "Gazelle", "Reserve"
    ]).delete()


class Migration(migrations.Migration):
    dependencies = [("receiving", "0005_productcatalogentry_xml_metadata")]
    operations = [
        migrations.CreateModel(
            name="Group1Family",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("family_name", models.CharField(max_length=100, unique=True)),
                ("suffix", models.CharField(help_text="Group1 suffix only, for example CVL, SCZ or KHF. The customer prefix (PON/PBP) is added automatically.", max_length=8, unique=True)),
                ("match_phrases", models.TextField(help_text="One identifying phrase per line. Matching is case-insensitive. More specific families should use a higher priority.")),
                ("priority", models.IntegerField(default=100, help_text="Higher priority wins when a description also matches a broader family rule.")),
                ("active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Group1 family mapping", "verbose_name_plural": "Group1 family mappings", "ordering": ["-priority", "family_name"]},
        ),
        migrations.AddField(
            model_name="productdefinition",
            name="group1",
            field=models.CharField(blank=True, db_index=True, max_length=20),
        ),
        migrations.AddField(
            model_name="productdefinition",
            name="group1_family",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="product_definitions", to="receiving.group1family"),
        ),
        migrations.RunPython(seed_group1_families, reverse_seed),
    ]
