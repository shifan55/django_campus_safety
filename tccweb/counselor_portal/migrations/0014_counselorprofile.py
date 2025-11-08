# Generated manually because Django isn't available in the execution environment.
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("counselor_portal", "0013_chatmessage_attachment"),
    ]

    operations = [
        migrations.CreateModel(
            name="CounselorProfile",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("specialization", models.CharField(choices=[
                    ("general", "General Support"),
                    ("academic", "Academic Guidance"),
                    ("emotional", "Emotional Wellness"),
                    ("disciplinary", "Disciplinary & Safety"),
                ], default="general", max_length=32)),
                ("max_active_cases", models.PositiveIntegerField(default=25)),
                ("auto_assign_enabled", models.BooleanField(default=True)),
                ("last_auto_assigned_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="counselor_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name="counselorprofile",
            index=models.Index(fields=["specialization"], name="cns_profile_spec_idx"),
        ),
        migrations.AddIndex(
            model_name="counselorprofile",
            index=models.Index(fields=["auto_assign_enabled"], name="cns_profile_auto_idx"),
        ),
    ]