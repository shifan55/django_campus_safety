"""Add a project-level flag that tracks user-managed 2FA state."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="two_factor_enabled",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "True when the account has completed the project-specific "
                    "two-factor authentication setup process."
                ),
            ),
        ),
    ]