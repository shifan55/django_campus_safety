from django.db import migrations


def ensure_casenote_columns(apps, schema_editor):
    """
    Some bundled databases may lack one or more CaseNote columns. Recreate them
    if missing so counselors can load notes without schema errors.
    """

    if schema_editor.connection.vendor != "sqlite":
        # Other databases should be corrected via standard migrations.
        return

    cursor = schema_editor.connection.cursor()
    cursor.execute("PRAGMA table_info(counselor_portal_casenote);")
    existing_columns = {row[1] for row in cursor.fetchall()}

    statements = []
    if "created_at" not in existing_columns:
        statements.append(
            "ALTER TABLE counselor_portal_casenote "
            "ADD COLUMN created_at datetime NOT NULL DEFAULT CURRENT_TIMESTAMP"
        )
    if "note" not in existing_columns:
        statements.append(
            "ALTER TABLE counselor_portal_casenote "
            "ADD COLUMN note TEXT NOT NULL DEFAULT ''"
        )
    if "counselor_id" not in existing_columns:
        statements.append(
            "ALTER TABLE counselor_portal_casenote "
            "ADD COLUMN counselor_id integer REFERENCES auth_user(id)"
        )
    if "report_id" not in existing_columns:
        statements.append(
            "ALTER TABLE counselor_portal_casenote "
            "ADD COLUMN report_id integer REFERENCES core_report(id)"
        )

    for statement in statements:
        cursor.execute(statement)


class Migration(migrations.Migration):

    dependencies = [
        ("counselor_portal", "0017_collaborationmessage"),
    ]

    operations = [migrations.RunPython(ensure_casenote_columns, migrations.RunPython.noop)]