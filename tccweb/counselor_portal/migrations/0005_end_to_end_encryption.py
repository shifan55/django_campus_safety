from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("counselor_portal", "0004_admin_alerts"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_key", models.TextField()),
                ("private_key", models.TextField()),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=models.CASCADE,
                        related_name="encryption_key",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.RemoveField(
            model_name="chatmessage",
            name="encrypted_body",
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="cipher_for_recipient",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="cipher_for_sender",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
    ]