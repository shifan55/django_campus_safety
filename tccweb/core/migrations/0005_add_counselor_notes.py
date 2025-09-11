from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_alter_report_tracking_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="report",
            name="counselor_notes",
            field=models.TextField(blank=True),
        ),
    ]