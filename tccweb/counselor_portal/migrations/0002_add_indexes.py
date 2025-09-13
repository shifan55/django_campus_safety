from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("counselor_portal", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="casenote",
            index=models.Index(fields=["created_at"], name="counselor_note_created_at_idx"),
        ),
        migrations.AddIndex(
            model_name="casenote",
            index=models.Index(fields=["report"], name="counselor_note_report_idx"),
        ),
        migrations.AddIndex(
            model_name="casenote",
            index=models.Index(fields=["counselor"], name="counselor_note_counselor_idx"),
        ),
        migrations.AddIndex(
            model_name="chatmessage",
            index=models.Index(fields=["timestamp"], name="counselor_msg_timestamp_idx"),
        ),
        migrations.AddIndex(
            model_name="chatmessage",
            index=models.Index(fields=["report"], name="counselor_msg_report_idx"),
        ),
        migrations.AddIndex(
            model_name="chatmessage",
            index=models.Index(fields=["sender"], name="counselor_msg_sender_idx"),
        ),
        migrations.AddIndex(
            model_name="chatmessage",
            index=models.Index(fields=["recipient"], name="counselor_msg_recipient_idx"),
        ),
    ]