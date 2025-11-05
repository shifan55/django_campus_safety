from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "counselor_portal",
            "0012_rename_counselor_p_adminal_created_idx_adm_alert_created_idx_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="chatmessage",
            name="attachment",
            field=models.FileField(
                blank=True,
                help_text="Optional file shared within the conversation.",
                null=True,
                upload_to="chat_attachments/",
            ),
        ),
    ]