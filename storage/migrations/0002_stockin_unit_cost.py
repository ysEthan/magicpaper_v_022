# Generated by Django 4.2.16 on 2025-01-06 22:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockin',
            name='unit_cost',
            field=models.DecimalField(decimal_places=2, default=0, help_text='入库时的单位成本金额', max_digits=10, verbose_name='单位成本'),
        ),
    ]
