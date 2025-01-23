from django.db import models
from django.contrib.auth.models import User
from gallery.models import SKU
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class Shop(models.Model):
    """店铺模型"""
    PLATFORM_CHOICES = (
        ('shopify', 'Shopify'),
        ('tiktok', 'Tik Tok'),
        ('etsy', 'Etsy'),
        ('offline', '线下订单'),
    )

    STATUS_CHOICES = (
        (1, '正常'),
        (0, '停用'),
    )

    name = models.CharField(max_length=100, verbose_name='店铺名称')
    platform = models.CharField(
        max_length=20,
        choices=PLATFORM_CHOICES,
        verbose_name='所属平台'
    )
    shop_code = models.CharField(max_length=50, unique=True, verbose_name='店铺编号')
    manager = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='managed_shops',
        verbose_name='店铺管理员'
    )
    status = models.IntegerField(
        choices=STATUS_CHOICES,
        default=1,
        verbose_name='状态'
    )
    description = models.TextField(blank=True, null=True, verbose_name='店铺描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'trade_shop'
        verbose_name = '店铺'
        verbose_name_plural = '店铺列表'
        ordering = ['platform', 'name']

    def __str__(self):
        return f"{self.get_platform_display()}-{self.name}"

class Order(models.Model):
    """订单主表"""
    ORDER_STATUS_CHOICES = (
        ('unpaid', '未支付'),
        ('pending', '待处理'),
        ('picking', '配货中'),
        ('shipped', '已发货'),
        ('cancelled', '已取消'),
    )

    PAYMENT_METHOD_CHOICES = (
        ('online', '在线支付'),
        ('bank_transfer', '银行转账'),
    )

    ORDER_TYPE_CHOICES = (
        ('platform', _('平台订单')),
        ('influencer', _('达人订单')),
        ('offline', _('线下订单')),
        ('requisition', _('员工领用')),
        ('employee', _('员工自购')),
    )

    CURRENCY_CHOICES = (
        ('CNY', '人民币'),
        ('USD', '美元'),
        ('EUR', '欧元'),
        ('GBP', '英镑'),
    )

    order_number = models.CharField(max_length=50, unique=True, verbose_name='订单编号')
    platform_order_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='平台订单号'
    )
    order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        default='normal',
        verbose_name='订单类型'
    )
    exchange_rate_to_usd = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=1.0,
        verbose_name='美元汇率'
    )
    package_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='包裹ID'
    )
    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='所属店铺'
    )
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='pending',
        verbose_name='订单状态'
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='订单总金额'
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='CNY',
        verbose_name='币种'
    )
    shipping_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
        verbose_name='物流运费'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name='支付方式'
    )
    payment_status = models.BooleanField(default=False, verbose_name='支付状态')
    payment_time = models.DateTimeField(null=True, blank=True, verbose_name='支付时间')
    order_place_time = models.DateTimeField(null=True, blank=True, verbose_name='下单时间')
    shipping_address = models.TextField(verbose_name='收货地址')
    shipping_contact = models.CharField(max_length=50, verbose_name='收货人')
    shipping_phone = models.CharField(max_length=20, verbose_name='联系电话')
    postal_code = models.CharField(max_length=20, null=True, blank=True, verbose_name='邮编')
    country = models.CharField(max_length=50, verbose_name='国家', null=True, blank=True)
    state = models.CharField(max_length=50, verbose_name='州省', null=True, blank=True)
    city = models.CharField(max_length=50, verbose_name='城市', null=True, blank=True)
    district = models.CharField(max_length=50, null=True, blank=True, verbose_name='区县')
    system_remark = models.TextField(verbose_name='系统备注', blank=True, default='')
    cs_remark = models.TextField(verbose_name='客服备注', blank=True, default='')
    buyer_remark = models.TextField(verbose_name='买家备注', blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'trade_order'
        verbose_name = '订单'
        verbose_name_plural = '订单列表'
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

class Cart(models.Model):
    """订单商品明细"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='所属订单'
    )
    sku = models.ForeignKey(
        SKU,
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name='商品SKU'
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='数量'
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='单价'
    )
    discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0,
        verbose_name='折扣(%)'
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='小计金额'
    )
    remark = models.TextField(blank=True, null=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'trade_cart'
        verbose_name = '订单商品'
        verbose_name_plural = '订单商品列表'

    def __str__(self):
        return f"{self.order.order_number} - {self.sku.sku_name}"

    def save(self, *args, **kwargs):
        """重写save方法，自动计算总价（考虑折扣）"""
        original_price = self.quantity * self.unit_price
        if self.discount > 0:
            discount_amount = original_price * (self.discount / 100)
            self.total_price = original_price - discount_amount
        else:
            self.total_price = original_price
        super().save(*args, **kwargs)
