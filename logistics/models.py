from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from trade.models import Order

User = get_user_model()


class Carrier(models.Model):
    """物流商模型"""
    id = models.AutoField('ID', primary_key=True)
    name_zh = models.CharField(_('中文名称'), max_length=25)
    name_en = models.CharField(_('英文名称'), max_length=25)
    code = models.CharField(_('物流商代码'), max_length=10, unique=True)
    url = models.URLField(_('官网地址'), blank=True)
    contact = models.CharField(_('联系电话'), max_length=20, blank=True)
    query_key = models.IntegerField(_('查询代码'), null=True, blank=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        verbose_name = _('物流商')
        verbose_name_plural = _('物流商')
        ordering = ['name_zh']
        db_table = 'logistics_carrier'

    def __str__(self):
        return f"{self.name_zh} ({self.name_en})"


class Service(models.Model):
    """物流服务模型"""
    id = models.AutoField('ID', primary_key=True)
    carrier = models.ForeignKey(
        Carrier,
        on_delete=models.CASCADE,
        verbose_name=_('物流商'),
        related_name='services'
    )
    service_name = models.CharField(_('服务名称'), max_length=25)
    service_code = models.CharField(_('服务代码'), max_length=10)
    service_type = models.IntegerField(_('服务类型'))
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        verbose_name = _('物流服务')
        verbose_name_plural = _('物流服务')
        ordering = ['carrier', 'service_name']
        db_table = 'logistics_service'
        unique_together = ['carrier', 'service_code']  # 确保同一物流商下服务代码唯一

    def __str__(self):
        return f"{self.carrier.name_zh} - {self.service_name}"


class Package(models.Model):
    """包裹模型"""
    STATUS_CHOICES = [
        ('0', _('待发货')),
        ('1', _('待揽收')),
        ('2', _('转运中')),
        ('3', _('已签收')),
        ('4', _('已取消')),
    ]

    id = models.AutoField('ID', primary_key=True)
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        verbose_name=_('订单'),
        related_name='package'
    )
    warehouse = models.ForeignKey(
        'storage.Warehouse',
        on_delete=models.PROTECT,
        verbose_name=_('发货仓库'),
        null=True,
        blank=True
    )
    tracking_no = models.CharField(
        _('跟踪号'),
        max_length=30,
        blank=True,
        null=True
    )
    pkg_status_code = models.CharField(
        _('包裹状态码'),
        max_length=4,
        choices=STATUS_CHOICES,
        default='0'
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,  # 使用PROTECT避免误删除物流服务
        verbose_name=_('物流服务'),
        related_name='packages'
    )
    items = models.JSONField(
        _('商品列表'),
        help_text=_('包含SKU、品名、包裹尺寸、重量等信息')
    )
    # 包裹尺寸和重量
    length = models.DecimalField(
        _('长(cm)'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    width = models.DecimalField(
        _('宽(cm)'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    height = models.DecimalField(
        _('高(cm)'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    weight = models.DecimalField(
        _('重量(kg)'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    # 费用相关
    estimated_logistics_cost = models.DecimalField(
        _('预估物流费用'),
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text=_('系统计算的预估物流费用')
    )
    carrier_cost = models.DecimalField(
        _('物流商费用'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('物流商回传的实际费用')
    )
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        verbose_name = _('包裹')
        verbose_name_plural = _('包裹')
        ordering = ['-created_at']
        db_table = 'logistics_package'

    def __str__(self):
        return f"包裹 {self.id} - {self.tracking_no or '未获取跟踪号'}"

    @property
    def carrier_name(self):
        """获取物流商名称"""
        return self.service.carrier.name_zh if self.service else ''

    @property
    def service_name(self):
        """获取服务名称"""
        return self.service.service_name if self.service else ''

    @property
    def volume(self):
        """计算体积(cm³)"""
        if self.length and self.width and self.height:
            return self.length * self.width * self.height
        return None

    @property
    def volume_weight(self):
        """计算体积重(kg)"""
        if self.volume:
            return self.volume / 6000  # 体积重 = 体积 / 6000
        return None


class Tracking(models.Model):
    """包裹物流轨迹"""
    STATUS_CHOICES = [
        (0, _('待发货')),
        (1, _('待揽收')),
        (2, _('转运中')),
        (3, _('已签收')),
        (4, _('已取消')),
    ]

    id = models.AutoField('ID', primary_key=True)
    package = models.ForeignKey(
        Package,
        on_delete=models.CASCADE,
        verbose_name=_('包裹'),
        related_name='tracking_records'
    )
    status = models.IntegerField(
        _('物流状态'),
        choices=STATUS_CHOICES,
        default=0
    )
    location = models.CharField(_('当前位置'), max_length=100)
    description = models.CharField(_('轨迹描述'), max_length=200)
    operator = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_('操作人'),
        null=True,
        blank=True
    )
    tracking_time = models.DateTimeField(_('轨迹时间'))
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        verbose_name = _('物流轨迹')
        verbose_name_plural = _('物流轨迹')
        ordering = ['-tracking_time']
        db_table = 'logistics_tracking'

    def __str__(self):
        return f"{self.package.tracking_no} - {self.get_status_display()}"
