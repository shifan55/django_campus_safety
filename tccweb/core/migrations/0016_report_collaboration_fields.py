from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0015_rename_core_system_user_id_593cbc_idx_systemlog_user_timestamp_idx"),
    ]

    operations = [
        migrations.AddField(
            model_name="report",
            name="collaborating_counselor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="collaborating_reports",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="report",
            name="invited_counselor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="report_invitations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(
                fields=["collaborating_counselor"], name="report_collab_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(
                fields=["invited_counselor"], name="report_invited_idx"
            ),
        ),
    ]