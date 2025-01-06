from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from gallery.models import SKU
from django.utils import timezone

class Warehouse(models.Model):
    """仓库模型"""
    warehouse_code = models.CharField(max_length=50, unique=True, verbose_name='仓库编码')
    warehouse_name = models.CharField(max_length=100, verbose_name='仓库名称')
    location = models.CharField(max_length=200, verbose_name='仓库地址')
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_warehouses',
        verbose_name='仓库管理员'
    )
    contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='联系电话')
    remark = models.TextField(blank=True, null=True, verbose_name='备注')
    status = models.BooleanField(default=True, verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'storage_warehouse'
        verbose_name = '仓库'
        verbose_name_plural = '仓库列表'
        ordering = ['warehouse_code']

    def __str__(self):
        return f"{self.warehouse_code} - {self.warehouse_name}"

class Inventory(models.Model):
    """库存记录模型，每个入库批次对应一条记录"""
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='inventories',
        verbose_name='所属仓库'
    )
    sku = models.ForeignKey(
        SKU,
        on_delete=models.CASCADE,
        related_name='inventories',
        verbose_name='商品SKU'
    )
    batch_code = models.CharField(max_length=50, unique=True, verbose_name='批次编号')
    quantity = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name='剩余数量'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'storage_inventory'
        verbose_name = '库存'
        verbose_name_plural = '库存列表'
        ordering = ['created_at']  # 按创建时间正序排序，用于FIFO

    def __str__(self):
        return f"{self.batch_code} - {self.sku.sku_code} ({self.quantity})"

    @property
    def is_empty(self):
        """判断批次是否已空"""
        return self.quantity <= 0

class StockIn(models.Model):
    """入库记录"""
    STOCK_IN_TYPE_CHOICES = [
        ('purchase', '采购入库'),
        ('return', '退货入库'),
        ('transfer', '调拨入库'),
    ]

    stock_in_code = models.CharField(max_length=50, unique=True, verbose_name='入库单号')
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='stock_ins',
        verbose_name='入库仓库'
    )
    sku = models.ForeignKey(
        SKU,
        on_delete=models.PROTECT,
        related_name='stock_ins',
        verbose_name='商品SKU'
    )
    inventory = models.OneToOneField(
        Inventory,
        on_delete=models.PROTECT,
        related_name='stock_in',
        verbose_name='库存批次'
    )
    stock_in_type = models.CharField(
        max_length=20,
        choices=STOCK_IN_TYPE_CHOICES,
        verbose_name='入库类型'
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='入库数量'
    )
    source_order = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='来源单号'
    )
    operator = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='operated_stock_ins',
        verbose_name='操作人'
    )
    remark = models.TextField(blank=True, null=True, verbose_name='备注')
    stock_in_time = models.DateTimeField(default=timezone.now, verbose_name='入库时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'storage_stock_in'
        verbose_name = '入库记录'
        verbose_name_plural = '入库记录列表'
        ordering = ['-stock_in_time']

    def __str__(self):
        return f"{self.stock_in_code} - {self.get_stock_in_type_display()}"

class StockOut(models.Model):
    """出库记录"""
    STOCK_OUT_TYPE_CHOICES = [
        ('sales', '销售出库'),
        ('return', '退货出库'),
        ('transfer', '调拨出库'),
    ]

    stock_out_code = models.CharField(max_length=50, unique=True, verbose_name='出库单号')
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='stock_outs',
        verbose_name='出库仓库'
    )
    sku = models.ForeignKey(
        SKU,
        on_delete=models.PROTECT,
        related_name='stock_outs',
        verbose_name='商品SKU'
    )
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.PROTECT,
        related_name='stock_outs',
        verbose_name='库存批次'
    )
    stock_out_type = models.CharField(
        max_length=20,
        choices=STOCK_OUT_TYPE_CHOICES,
        verbose_name='出库类型'
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='出库数量'
    )
    related_order = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='关联单号'
    )
    operator = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='operated_stock_outs',
        verbose_name='操作人'
    )
    remark = models.TextField(blank=True, null=True, verbose_name='备注')
    stock_out_time = models.DateTimeField(default=timezone.now, verbose_name='出库时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'storage_stock_out'
        verbose_name = '出库记录'
        verbose_name_plural = '出库记录列表'
        ordering = ['-stock_out_time']

    def __str__(self):
        return f"{self.stock_out_code} - {self.get_stock_out_type_display()}"
