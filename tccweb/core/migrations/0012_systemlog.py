# Generated manually because the execution environment cannot run makemigrations.
from django.conf import settings
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0011_report_awaiting_response"),
    ]

    operations = [
        migrations.CreateModel(
            name="SystemLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "timestamp",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        help_text="When the action was performed.",
                    ),
                ),
                (
                    "action_type",
                    models.CharField(
                        choices=[
                            ("VIEWED", "Viewed"),
                            ("EDITED", "Edited"),
                            ("CLOSED", "Closed"),
                        ],
                        help_text="High level category describing the action.",
                        max_length=32,
                    ),
                ),
                (
                    "object_type",
                    models.CharField(
                        help_text="Human readable label for the object type (e.g. Report).",
                        max_length=128,
                    ),
                ),
                (
                    "object_id",
                    models.PositiveIntegerField(
                        help_text="Primary key for the affected object.",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional human readable description of what happened.",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        help_text="Structured metadata for integrations or analytics.",
                        null=True,
                    ),
                ),
                (
                    "content_type",
                    models.ForeignKey(
                        help_text="Generic reference to the model for the affected object.",
                        on_delete=models.deletion.CASCADE,
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="Actor who performed the action.",
                        on_delete=models.deletion.CASCADE,
                        related_name="system_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-timestamp"],
                "indexes": [
                    models.Index(
                        fields=["user", "timestamp"],
                        name="systemlog_user_timestamp_idx",
                    ),
                ],
                "verbose_name": "System log entry",
                "verbose_name_plural": "System log entries",
            },
        ),
    ]