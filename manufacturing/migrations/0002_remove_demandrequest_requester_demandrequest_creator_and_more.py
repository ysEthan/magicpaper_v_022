# Generated by Django 4.2.16 on 2025-01-16 12:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gallery', '0002_sku_is_reviewed'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('manufacturing', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='demandrequest',
            name='requester',
        ),
        migrations.AddField(
            model_name='demandrequest',
            name='creator',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='created_demands', to=settings.AUTH_USER_MODEL, verbose_name='创建者'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='demandrequest',
            name='sku',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='demands', to='gallery.sku', verbose_name='关联SKU'),
        ),
        migrations.AlterField(
            model_name='demandrequest',
            name='handler',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='handled_demands', to=settings.AUTH_USER_MODEL, verbose_name='处理人'),
        ),
    ]
