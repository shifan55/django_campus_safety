from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("counselor_portal", "0002_threaded_encrypted_messages"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatmessage",
            name="is_read",
            field=models.BooleanField(default=False),
        ),
    ]