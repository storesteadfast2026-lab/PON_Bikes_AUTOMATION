from django.db import migrations, models


def create_job_order_unique_index(apps, schema_editor):
    Container = apps.get_model("receiving", "Container")
    duplicate = (
        Container.objects.exclude(job_order="")
        .values("job_order")
        .annotate(count=models.Count("id"))
        .filter(count__gt=1)
        .order_by("job_order")
        .first()
    )
    if duplicate:
        # Preserve legacy data rather than rewriting Job Orders during migration.
        # UI/backend validation still prevents new duplicates; 04_VALIDATE reports legacy duplicates.
        return
    table = Container._meta.db_table
    vendor = schema_editor.connection.vendor
    if vendor == "postgresql":
        schema_editor.execute(
            f'CREATE UNIQUE INDEX IF NOT EXISTS unique_nonblank_container_job_order '
            f'ON "{table}" (job_order) WHERE job_order <> \'\''
        )
    elif vendor == "sqlite":
        schema_editor.execute(
            f'CREATE UNIQUE INDEX IF NOT EXISTS unique_nonblank_container_job_order '
            f'ON "{table}" (job_order) WHERE job_order <> \'\''
        )


def drop_job_order_unique_index(apps, schema_editor):
    schema_editor.execute("DROP INDEX IF EXISTS unique_nonblank_container_job_order")


class Migration(migrations.Migration):
    dependencies = [
        ("receiving", "0012_product_master_xls"),
    ]

    operations = [
        migrations.AlterField(
            model_name="container",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("OPEN", "Open"),
                    ("REVIEW", "Under review"),
                    ("READY", "Ready for Translogic"),
                    ("CLOSED", "Closed"),
                ],
                default="OPEN",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="container",
            name="auto_created_from_manifest",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="container",
            name="manifest_source_name",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="normalizedline",
            name="container_identifier",
            field=models.CharField(blank=True, db_index=True, max_length=30),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(create_job_order_unique_index, drop_job_order_unique_index),
            ],
            state_operations=[
                migrations.AddConstraint(
                    model_name="container",
                    constraint=models.UniqueConstraint(
                        fields=("job_order",),
                        condition=~models.Q(job_order=""),
                        name="unique_nonblank_container_job_order",
                    ),
                ),
            ],
        ),
    ]
