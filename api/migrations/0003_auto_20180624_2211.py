# Generated by Django 2.0.2 on 2018-06-24 20:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_auto_20180623_2252'),
    ]

    operations = [
        migrations.AlterField(
            model_name='telegramuser',
            name='country',
            field=models.CharField(default='ES', max_length=2),
        ),
    ]
