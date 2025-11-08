from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("counselor_portal", "0014_counselorprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatmessage",
            name="emotion",
            field=models.CharField(
                choices=[
                    ("anxious", "Anxious"),
                    ("angry", "Angry"),
                    ("stressed", "Stressed"),
                    ("calm", "Calm"),
                    ("neutral", "Neutral"),
                ],
                default="neutral",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="emotion_confidence",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="emotion_explanation",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="emotion_score",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="risk_level",
            field=models.CharField(
                choices=[
                    ("normal", "Stable"),
                    ("elevated", "Elevated"),
                    ("critical", "Critical"),
                ],
                default="normal",
                max_length=16,
            ),
        ),
        migrations.AddIndex(
            model_name="chatmessage",
            index=models.Index(fields=["risk_level"], name="chat_msg_risk_idx"),
        ),
    ]