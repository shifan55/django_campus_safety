from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="report",
            name="tracking_code",
            field=models.CharField(max_length=12, null=True, blank=True, editable=False),
        ),
    ]
