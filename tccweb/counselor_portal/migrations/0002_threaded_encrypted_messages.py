from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('counselor_portal', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='chatmessage',
            old_name='message',
            new_name='encrypted_body',
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.CASCADE, related_name='replies', to='counselor_portal.chatmessage'),
        ),
    ]