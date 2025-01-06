from django.db import models
from django.utils import timezone
from gallery.models import SKU


class BaseModel(models.Model):
    """基础模型类"""
    created_at = models.DateTimeField('创建时间', default=timezone.now)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        abstract = True


class Supplier(BaseModel):
    """供应商模型"""
    name = models.CharField('供应商名称', max_length=100)
    contact_person = models.CharField('联系人', max_length=50)
    contact_phone = models.CharField('联系电话', max_length=20)
    address = models.CharField('地址', max_length=200)
    email = models.EmailField('邮箱', blank=True)
    status = models.BooleanField('状态', default=True)
    remark = models.TextField('备注', blank=True)

    class Meta:
        verbose_name = '供应商'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class PurchaseOrder(BaseModel):
    """采购订单模型"""
    ORDER_STATUS_CHOICES = (
        ('draft', '草稿'),
        ('submitted', '已提交'),
        ('approved', '已审核'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    )

    order_number = models.CharField('订单编号', max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, verbose_name='供应商')
    status = models.CharField('订单状态', max_length=20, choices=ORDER_STATUS_CHOICES, default='draft')
    total_amount = models.DecimalField('总金额', max_digits=10, decimal_places=2, default=0)
    expected_delivery_date = models.DateField('预计交付日期')
    actual_delivery_date = models.DateField('实际交付日期', null=True, blank=True)
    remark = models.TextField('备注', blank=True)

    class Meta:
        verbose_name = '采购订单'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number


class PurchaseOrderItem(BaseModel):
    """采购订单明细模型"""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, verbose_name='采购订单')
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, verbose_name='商品')
    quantity = models.IntegerField('数量')
    unit_price = models.DecimalField('单价', max_digits=10, decimal_places=2)
    total_price = models.DecimalField('总价', max_digits=10, decimal_places=2)
    received_quantity = models.IntegerField('已收货数量', default=0)
    remark = models.TextField('备注', blank=True)

    class Meta:
        verbose_name = '采购订单明细'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.purchase_order.order_number} - {self.sku.name}"

    def save(self, *args, **kwargs):
        # 计算总价
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
