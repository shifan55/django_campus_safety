from django.db import migrations, models
from django.conf import settings
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_systemlog"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SecurityLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField(default=django.utils.timezone.now, help_text="When the security event occurred.")),
                ("event_type", models.CharField(choices=[("LOGIN_SUCCESS", "Login success"), ("LOGIN_FAILURE", "Login failure"), ("LOGOUT", "Logout"), ("PERMISSION_GRANTED", "Permission granted"), ("PERMISSION_REVOKED", "Permission revoked")], help_text="Type of security event (login, permission change, etc.).", max_length=32)),
                ("ip_address", models.GenericIPAddressField(blank=True, help_text="Best-effort IP address captured with the event.", null=True)),
                ("user_agent", models.TextField(blank=True, help_text="Recorded User-Agent string for additional context.")),
                ("description", models.TextField(blank=True, help_text="Human readable explanation of what occurred.")),
                ("metadata", models.JSONField(blank=True, help_text="Optional structured payload for downstream analysis.", null=True)),
                ("actor", models.ForeignKey(blank=True, help_text="Authenticated user who triggered the event (if known).", null=True, on_delete=models.SET_NULL, related_name="security_events", to=settings.AUTH_USER_MODEL)),
                ("target_user", models.ForeignKey(blank=True, help_text="Account affected by the change (can differ from actor).", null=True, on_delete=models.SET_NULL, related_name="security_events_target", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Security log entry",
                "verbose_name_plural": "Security log entries",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="securitylog",
            index=models.Index(fields=["timestamp"], name="securitylog_ts_idx"),
        ),
        migrations.AddIndex(
            model_name="securitylog",
            index=models.Index(fields=["event_type", "timestamp"], name="securitylog_event_ts_idx"),
        ),
    ]