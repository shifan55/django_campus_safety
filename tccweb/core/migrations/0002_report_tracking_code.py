from django.db import migrations, models
import tccweb.core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='tracking_code',
            field=models.CharField(default=tccweb.core.models.generate_tracking_code, editable=False, max_length=12, unique=True),
        ),
    ]
