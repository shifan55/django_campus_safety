from django.db import migrations, models
import secrets
import uuid

def gen_code():
    """Generate a short unique tracking code for anonymous lookups."""
    return uuid.uuid4().hex[:10].upper()

def forwards(apps, schema_editor):
    Report = apps.get_model("core", "Report")
    used = set(
        Report.objects.exclude(tracking_code__isnull=True)
                      .values_list("tracking_code", flat=True)
    )
    for r in Report.objects.all():
        if not r.tracking_code:
            code = gen_code()
            while code in used:
                code = gen_code()
            r.tracking_code = code
            used.add(code)
            r.save(update_fields=["tracking_code"])

def backwards(apps, schema_editor):
    # soften constraint on rollback: make values nullable again
    Report = apps.get_model("core", "Report")
    for r in Report.objects.all():
        r.tracking_code = None
        r.save(update_fields=["tracking_code"])

class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_add_tracking_code_nullable"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name="report",
            name="tracking_code",
            field= models.CharField(max_length=12, null=True, unique=True, editable=False),
        ),
    ]
