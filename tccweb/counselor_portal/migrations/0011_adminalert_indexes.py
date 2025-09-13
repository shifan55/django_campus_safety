from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("counselor_portal", "0010_rename_counselor_note_created_at_idx_counselor_p_created_f19058_idx_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="adminalert",
            index=models.Index(fields=["created_at"], name="counselor_p_adminal_created_idx"),
        ),
        migrations.AddIndex(
            model_name="adminalert",
            index=models.Index(fields=["admin"], name="counselor_p_adminal_admin_idx"),
        ),
        migrations.AddIndex(
            model_name="adminalert",
            index=models.Index(fields=["report"], name="counselor_p_adminal_report_idx"),
        ),
    ]