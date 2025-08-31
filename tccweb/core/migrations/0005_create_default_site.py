from django.conf import settings
from django.db import migrations


def create_default_site(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    site_id = getattr(settings, 'SITE_ID', 1)
    domain = 'localhost:8000'
    name = 'Campus Safety'
    Site.objects.update_or_create(id=site_id, defaults={'domain': domain, 'name': name})


def remove_default_site(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    site_id = getattr(settings, 'SITE_ID', 1)
    Site.objects.filter(id=site_id, domain='localhost:8000', name='Campus Safety').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_alter_report_status'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(create_default_site, remove_default_site),
    ]