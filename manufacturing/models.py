from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator
from gallery.models import SKU

class DemandRequest(models.Model):
    """需求申请模型"""
    REQUEST_TYPE_CHOICES = [
        ('sample', '样品生产需求'),
        ('mass', '量产需求'),
        ('procurement', '采购需求'),
    ]

    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('submitted', '已提交'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]

    PRIORITY_CHOICES = [
        ('high', '高'),
        ('medium', '中'),
        ('low', '低'),
    ]

    request_number = models.CharField('需求编号', max_length=50, unique=True)
    request_type = models.CharField('需求类型', max_length=20, choices=REQUEST_TYPE_CHOICES)
    title = models.CharField('需求标题', max_length=200)
    description = models.TextField('需求描述')
    priority = models.CharField(
        '优先级',
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    status = models.CharField(
        '状态',
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_demands',
        verbose_name='创建者'
    )
    handler = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handled_demands',
        verbose_name='处理人'
    )
    expected_completion_date = models.DateField('预期完成日期')
    actual_completion_date = models.DateField('实际完成日期', null=True, blank=True)
    attachments = models.JSONField('附件列表', default=list, blank=True)
    remark = models.TextField('备注', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '需求申请'
        verbose_name_plural = '需求申请列表'
        ordering = ['-created_at']
        db_table = 'manufacturing_demand_request'

    def __str__(self):
        return f"{self.request_number} - {self.title}"

class DemandTracking(models.Model):
    """需求跟进记录模型"""
    TRACKING_TYPE_CHOICES = [
        ('status_change', '状态变更'),
        ('progress_update', '进度更新'),
        ('problem_report', '问题反馈'),
        ('solution_proposal', '解决方案'),
        ('other', '其他'),
    ]

    demand = models.ForeignKey(
        DemandRequest,
        on_delete=models.CASCADE,
        related_name='tracking_records',
        verbose_name='关联需求'
    )
    tracking_type = models.CharField('记录类型', max_length=20, choices=TRACKING_TYPE_CHOICES)
    content = models.TextField('跟进内容')
    operator = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='demand_tracking_records',
        verbose_name='操作人'
    )
    attachments = models.JSONField('附件列表', default=list, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '需求跟进记录'
        verbose_name_plural = '需求跟进记录列表'
        ordering = ['-created_at']
        db_table = 'manufacturing_demand_tracking'

    def __str__(self):
        return f"{self.demand.request_number} - {self.get_tracking_type_display()}"

class ProductionOrder(models.Model):
    """生产工单模型"""
    ORDER_STATUS_CHOICES = [
        ('pending', '待生产'),
        ('in_progress', '生产中'),
        ('quality_check', '质检中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]

    order_number = models.CharField('工单编号', max_length=50, unique=True)
    demand = models.ForeignKey(
        DemandRequest,
        on_delete=models.PROTECT,
        related_name='production_orders',
        verbose_name='关联需求'
    )
    sku = models.ForeignKey(
        SKU,
        on_delete=models.PROTECT,
        related_name='production_orders',
        verbose_name='产品SKU'
    )
    quantity = models.IntegerField(
        '计划生产数量',
        validators=[MinValueValidator(1)]
    )
    completed_quantity = models.IntegerField(
        '已完成数量',
        default=0,
        validators=[MinValueValidator(0)]
    )
    defective_quantity = models.IntegerField(
        '不良品数量',
        default=0,
        validators=[MinValueValidator(0)]
    )
    status = models.CharField(
        '状态',
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='pending'
    )
    production_start_date = models.DateField('计划开始日期')
    production_end_date = models.DateField('计划结束日期')
    actual_start_date = models.DateField('实际开始日期', null=True, blank=True)
    actual_end_date = models.DateField('实际结束日期', null=True, blank=True)
    materials = models.JSONField(
        '物料清单',
        help_text='包含物料SKU、需求数量等信息'
    )
    quality_requirements = models.TextField('质量要求', blank=True)
    production_instructions = models.TextField('生产说明', blank=True)
    remark = models.TextField('备注', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '生产工单'
        verbose_name_plural = '生产工单列表'
        ordering = ['-created_at']
        db_table = 'manufacturing_production_order'

    def __str__(self):
        return f"{self.order_number} - {self.sku.sku_name}"

    @property
    def completion_rate(self):
        """计算完成率"""
        return round(self.completed_quantity / self.quantity * 100, 2) if self.quantity > 0 else 0

    @property
    def defect_rate(self):
        """计算不良品率"""
        total_produced = self.completed_quantity + self.defective_quantity
        return round(self.defective_quantity / total_produced * 100, 2) if total_produced > 0 else 0
