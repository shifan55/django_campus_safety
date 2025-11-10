from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import tccweb.accounts.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(blank=True, max_length=255)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("bio", models.TextField(blank=True)),
                ("location", models.CharField(blank=True, max_length=255)),
                ("timezone", models.CharField(blank=True, max_length=64)),
                ("avatar", models.ImageField(blank=True, null=True, upload_to=tccweb.accounts.models.avatar_upload_to)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["user"], name="profile_user_idx"),
                ],
            },
        ),
    ]