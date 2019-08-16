# Generated by Django 2.2.4 on 2019-08-12 10:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0009_auto_20190808_1351'),
    ]

    operations = [
        migrations.AlterField(
            model_name='analysis',
            name='snapshot',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='analyses', to='datasets.AnalysisSnapshot'),
        ),
    ]
