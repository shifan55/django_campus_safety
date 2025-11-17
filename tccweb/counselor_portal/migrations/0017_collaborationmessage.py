from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0016_report_collaboration_fields"),
        ("counselor_portal", "0016_merge_20251108_2107"),
    ]

    operations = [
        migrations.CreateModel(
            name="CollaborationMessage",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("report", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="collaboration_messages", to="core.report")),
                ("sender", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="collaboration_messages", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="collaborationmessage",
            index=models.Index(fields=["report"], name="collab_msg_report_idx"),
        ),
        migrations.AddIndex(
            model_name="collaborationmessage",
            index=models.Index(fields=["created_at"], name="collab_msg_created_idx"),
        ),
    ]