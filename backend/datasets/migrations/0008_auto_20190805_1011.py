# Generated by Django 2.2.4 on 2019-08-05 10:11

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0007_auto_20190801_1541'),
    ]

    operations = [
        migrations.AlterField(
            model_name='analysis',
            name='result',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True),
        ),
    ]
