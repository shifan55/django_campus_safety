from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_add_counselor_notes"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["created_at"], name="core_report_created_at_idx"),
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["status"], name="core_report_status_idx"),
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["reporter"], name="core_report_reporter_idx"),
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["assigned_to"], name="core_report_assigned_to_idx"),
        ),
        migrations.AddIndex(
            model_name="educationalresource",
            index=models.Index(fields=["created_at"], name="core_res_created_at_idx"),
        ),
        migrations.AddIndex(
            model_name="educationalresource",
            index=models.Index(fields=["created_by"], name="core_res_created_by_idx"),
        ),
        migrations.AddIndex(
            model_name="quiz",
            index=models.Index(fields=["created_at"], name="core_quiz_created_at_idx"),
        ),
        migrations.AddIndex(
            model_name="quiz",
            index=models.Index(fields=["created_by"], name="core_quiz_created_by_idx"),
        ),
        migrations.AddIndex(
            model_name="quizquestion",
            index=models.Index(fields=["quiz"], name="core_question_quiz_idx"),
        ),
        migrations.AddIndex(
            model_name="supportcontact",
            index=models.Index(fields=["created_at"], name="core_support_created_at_idx"),
        ),
    ]