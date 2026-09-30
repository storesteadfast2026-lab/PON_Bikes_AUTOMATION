import django.db.models.deletion
import receiving.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="AppSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=80, unique=True)),
                ("value", models.TextField(blank=True)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20, unique=True)),
                ("name", models.CharField(max_length=120)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Container",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("identifier", models.CharField(max_length=30, unique=True)),
                ("year", models.PositiveSmallIntegerField(default=2026)),
                ("status", models.CharField(choices=[("OPEN", "Open"), ("REVIEW", "Under review"), ("READY", "Ready for Translogic"), ("CLOSED", "Closed")], default="OPEN", max_length=10)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_containers", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="containers", to="receiving.customer")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ImportProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("kind", models.CharField(choices=[("CLIENT", "Client manifest"), ("RECEIVED", "First scan / received bikes")], max_length=12)),
                ("mapping", models.JSONField(default=dict)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="import_profiles", to="receiving.customer")),
            ],
            options={"unique_together": {("customer", "name", "kind")}},
        ),
        migrations.CreateModel(
            name="SourceFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("CLIENT", "Client manifest"), ("RECEIVED", "First scan / received bikes")], max_length=12)),
                ("file", models.FileField(upload_to=receiving.models.source_upload_path)),
                ("original_name", models.CharField(max_length=255)),
                ("sha256", models.CharField(db_index=True, max_length=64)),
                ("status", models.CharField(choices=[("UPLOADED", "Uploaded"), ("PREVIEW", "Preview ready"), ("CONFIRMED", "Confirmed"), ("ERROR", "Error")], default="UPLOADED", max_length=12)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("container", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="source_files", to="receiving.container")),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-uploaded_at"]},
        ),
        migrations.CreateModel(
            name="ImportBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("PREVIEW", "Preview"), ("CONFIRMED", "Confirmed"), ("SUPERSEDED", "Superseded")], default="PREVIEW", max_length=12)),
                ("mapping", models.JSONField(default=dict)),
                ("total_rows", models.PositiveIntegerField(default=0)),
                ("total_units", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("source_file", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="batches", to="receiving.sourcefile")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="NormalizedLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_sheet", models.CharField(max_length=100)),
                ("source_row", models.PositiveIntegerField()),
                ("code", models.CharField(db_index=True, max_length=100)),
                ("long_code", models.CharField(blank=True, max_length=160)),
                ("description", models.TextField(blank=True)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("location", models.CharField(blank=True, max_length=30)),
                ("fill_signature", models.CharField(blank=True, max_length=120)),
                ("raw_data", models.JSONField(default=dict)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="receiving.importbatch")),
            ],
            options={"ordering": ["source_row", "id"]},
        ),
        migrations.AddConstraint(
            model_name="sourcefile",
            constraint=models.UniqueConstraint(fields=("container", "kind", "sha256"), name="unique_source_per_container_kind"),
        ),
    ]
