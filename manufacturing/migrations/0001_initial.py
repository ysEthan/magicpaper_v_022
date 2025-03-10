# Generated by Django 4.2.16 on 2025-01-15 17:29

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gallery', '0002_sku_is_reviewed'),
    ]

    operations = [
        migrations.CreateModel(
            name='DemandRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_number', models.CharField(max_length=50, unique=True, verbose_name='需求编号')),
                ('request_type', models.CharField(choices=[('sample', '样品生产需求'), ('mass', '量产需求'), ('procurement', '采购需求')], max_length=20, verbose_name='需求类型')),
                ('title', models.CharField(max_length=200, verbose_name='需求标题')),
                ('description', models.TextField(verbose_name='需求描述')),
                ('priority', models.CharField(choices=[('high', '高'), ('medium', '中'), ('low', '低')], default='medium', max_length=10, verbose_name='优先级')),
                ('status', models.CharField(choices=[('draft', '草稿'), ('submitted', '已提交'), ('processing', '处理中'), ('completed', '已完成'), ('cancelled', '已取消')], default='draft', max_length=20, verbose_name='状态')),
                ('expected_completion_date', models.DateField(verbose_name='预期完成日期')),
                ('actual_completion_date', models.DateField(blank=True, null=True, verbose_name='实际完成日期')),
                ('attachments', models.JSONField(blank=True, default=list, verbose_name='附件列表')),
                ('remark', models.TextField(blank=True, verbose_name='备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('handler', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='handled_demands', to=settings.AUTH_USER_MODEL, verbose_name='跟单员')),
                ('requester', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='demand_requests', to=settings.AUTH_USER_MODEL, verbose_name='需求提出人')),
            ],
            options={
                'verbose_name': '需求申请',
                'verbose_name_plural': '需求申请列表',
                'db_table': 'manufacturing_demand_request',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProductionOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_number', models.CharField(max_length=50, unique=True, verbose_name='工单编号')),
                ('quantity', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name='计划生产数量')),
                ('completed_quantity', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)], verbose_name='已完成数量')),
                ('defective_quantity', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)], verbose_name='不良品数量')),
                ('status', models.CharField(choices=[('pending', '待生产'), ('in_progress', '生产中'), ('quality_check', '质检中'), ('completed', '已完成'), ('cancelled', '已取消')], default='pending', max_length=20, verbose_name='状态')),
                ('production_start_date', models.DateField(verbose_name='计划开始日期')),
                ('production_end_date', models.DateField(verbose_name='计划结束日期')),
                ('actual_start_date', models.DateField(blank=True, null=True, verbose_name='实际开始日期')),
                ('actual_end_date', models.DateField(blank=True, null=True, verbose_name='实际结束日期')),
                ('materials', models.JSONField(help_text='包含物料SKU、需求数量等信息', verbose_name='物料清单')),
                ('quality_requirements', models.TextField(blank=True, verbose_name='质量要求')),
                ('production_instructions', models.TextField(blank=True, verbose_name='生产说明')),
                ('remark', models.TextField(blank=True, verbose_name='备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('demand', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='production_orders', to='manufacturing.demandrequest', verbose_name='关联需求')),
                ('sku', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='production_orders', to='gallery.sku', verbose_name='产品SKU')),
            ],
            options={
                'verbose_name': '生产工单',
                'verbose_name_plural': '生产工单列表',
                'db_table': 'manufacturing_production_order',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='DemandTracking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tracking_type', models.CharField(choices=[('status_change', '状态变更'), ('progress_update', '进度更新'), ('problem_report', '问题反馈'), ('solution_proposal', '解决方案'), ('other', '其他')], max_length=20, verbose_name='记录类型')),
                ('content', models.TextField(verbose_name='跟进内容')),
                ('attachments', models.JSONField(blank=True, default=list, verbose_name='附件列表')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('demand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tracking_records', to='manufacturing.demandrequest', verbose_name='关联需求')),
                ('operator', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='demand_tracking_records', to=settings.AUTH_USER_MODEL, verbose_name='操作人')),
            ],
            options={
                'verbose_name': '需求跟进记录',
                'verbose_name_plural': '需求跟进记录列表',
                'db_table': 'manufacturing_demand_tracking',
                'ordering': ['-created_at'],
            },
        ),
    ]
