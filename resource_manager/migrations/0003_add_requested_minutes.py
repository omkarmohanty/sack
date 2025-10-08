"""Add requested_minutes to ResourceQueue"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resource_manager', '0002_userprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='resourcequeue',
            name='requested_minutes',
            field=models.PositiveIntegerField(default=60),
        ),
    ]
