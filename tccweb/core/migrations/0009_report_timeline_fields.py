from django.db import migrations, models


def ensure_timestamp_columns(apps, schema_editor):
    """Add assigned/resolved columns when missing without failing on packaged DBs."""

    Report = apps.get_model("core", "Report")
    table = Report._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor, table
            )
        }

    for name in ("assigned_at", "resolved_at"):
        if name in existing_columns:
            continue

        field = models.DateTimeField(blank=True, null=True)
        field.set_attributes_from_name(name)
        schema_editor.add_field(Report, field)


def create_timeline_indexes(apps, schema_editor):
    Report = apps.get_model("core", "Report")
    table = schema_editor.quote_name(Report._meta.db_table)

    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS {name} ON {table} ({column});".format(
            name=schema_editor.quote_name("core_report_assigned_at_idx"),
            table=table,
            column=schema_editor.quote_name("assigned_at"),
        )
    )
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS {name} ON {table} ({column});".format(
            name=schema_editor.quote_name("core_report_resolved_at_idx"),
            table=table,
            column=schema_editor.quote_name("resolved_at"),
        )
    )


def drop_timeline_indexes(apps, schema_editor):
    schema_editor.execute(
        "DROP INDEX IF EXISTS {name};".format(
            name=schema_editor.quote_name("core_report_assigned_at_idx")
        )
    )
    schema_editor.execute(
        "DROP INDEX IF EXISTS {name};".format(
            name=schema_editor.quote_name("core_report_resolved_at_idx")
        )
    )


def populate_timestamps(apps, schema_editor):
    Report = apps.get_model("core", "Report")
    Report.objects.filter(
        assigned_to__isnull=False, assigned_at__isnull=True
    ).update(assigned_at=models.F("updated_at"))
    Report.objects.filter(
        status="resolved", resolved_at__isnull=True
    ).update(resolved_at=models.F("updated_at"))


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_alter_educationalresource_file"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(ensure_timestamp_columns, noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="report",
                    name="assigned_at",
                    field=models.DateTimeField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="report",
                    name="resolved_at",
                    field=models.DateTimeField(blank=True, null=True),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    create_timeline_indexes, drop_timeline_indexes
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="report",
                    index=models.Index(
                        fields=["assigned_at"], name="core_report_assigned_at_idx"
                    ),
                ),
                migrations.AddIndex(
                    model_name="report",
                    index=models.Index(
                        fields=["resolved_at"], name="core_report_resolved_at_idx"
                    ),
                ),
            ],
        ),
        migrations.RunPython(populate_timestamps, noop),
    ]