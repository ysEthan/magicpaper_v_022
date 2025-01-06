# Generated by Django 4.2.16 on 2025-01-06 14:59

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('gallery', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PurchaseOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('order_number', models.CharField(max_length=50, unique=True, verbose_name='订单编号')),
                ('status', models.CharField(choices=[('draft', '草稿'), ('submitted', '已提交'), ('approved', '已审核'), ('processing', '处理中'), ('completed', '已完成'), ('cancelled', '已取消')], default='draft', max_length=20, verbose_name='订单状态')),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='总金额')),
                ('expected_delivery_date', models.DateField(verbose_name='预计交付日期')),
                ('actual_delivery_date', models.DateField(blank=True, null=True, verbose_name='实际交付日期')),
                ('remark', models.TextField(blank=True, verbose_name='备注')),
            ],
            options={
                'verbose_name': '采购订单',
                'verbose_name_plural': '采购订单',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Supplier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('name', models.CharField(max_length=100, verbose_name='供应商名称')),
                ('contact_person', models.CharField(max_length=50, verbose_name='联系人')),
                ('contact_phone', models.CharField(max_length=20, verbose_name='联系电话')),
                ('address', models.CharField(max_length=200, verbose_name='地址')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='邮箱')),
                ('status', models.BooleanField(default=True, verbose_name='状态')),
                ('remark', models.TextField(blank=True, verbose_name='备注')),
            ],
            options={
                'verbose_name': '供应商',
                'verbose_name_plural': '供应商',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PurchaseOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('quantity', models.IntegerField(verbose_name='数量')),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='单价')),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='总价')),
                ('received_quantity', models.IntegerField(default=0, verbose_name='已收货数量')),
                ('remark', models.TextField(blank=True, verbose_name='备注')),
                ('purchase_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='procurement.purchaseorder', verbose_name='采购订单')),
                ('sku', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='gallery.sku', verbose_name='商品')),
            ],
            options={
                'verbose_name': '采购订单明细',
                'verbose_name_plural': '采购订单明细',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='purchaseorder',
            name='supplier',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='procurement.supplier', verbose_name='供应商'),
        ),
    ]
