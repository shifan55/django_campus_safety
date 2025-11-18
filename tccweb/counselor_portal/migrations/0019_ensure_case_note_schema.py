from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def ensure_case_note_schema(apps, schema_editor):
    CaseNote = apps.get_model("counselor_portal", "CaseNote")
    UserModel = apps.get_model(settings.AUTH_USER_MODEL)
    Report = apps.get_model("core", "Report")
    connection = schema_editor.connection
    table = CaseNote._meta.db_table

    with connection.cursor() as cursor:
        try:
            description = connection.introspection.get_table_description(cursor, table)
        except Exception:
            schema_editor.create_model(CaseNote)
            description = connection.introspection.get_table_description(cursor, table)

    existing_columns = {column.name for column in description}

    def add_field_if_missing(field_name, field):
        if field_name in existing_columns:
            return
        field.set_attributes_from_name(field_name)
        schema_editor.add_field(CaseNote, field)

    add_field_if_missing("note", models.TextField(default=""))
    add_field_if_missing("created_at", models.DateTimeField(default=timezone.now))
    add_field_if_missing(
        "counselor",
        models.ForeignKey(
            UserModel,
            related_name="case_notes",
            null=True,
            on_delete=models.deletion.CASCADE,
        ),
    )
    add_field_if_missing(
        "report",
        models.ForeignKey(
            Report,
            related_name="notes",
            null=True,
            on_delete=models.deletion.CASCADE,
        ),
    )

    quoted_table = schema_editor.quote_name(table)
    schema_editor.execute(
        f"CREATE INDEX IF NOT EXISTS counselor_p_created_f19058_idx ON {quoted_table} (created_at);"
    )
    schema_editor.execute(
        f"CREATE INDEX IF NOT EXISTS counselor_p_report__0140a5_idx ON {quoted_table} (report_id);"
    )
    schema_editor.execute(
        f"CREATE INDEX IF NOT EXISTS counselor_p_counsel_9b3e91_idx ON {quoted_table} (counselor_id);"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("counselor_portal", "0018_alter_collaborationmessage_id"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0016_report_collaboration_fields"),
    ]

    operations = [
        migrations.RunPython(ensure_case_note_schema, migrations.RunPython.noop),
    ]