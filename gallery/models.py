from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
import uuid
import os
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User

def category_image_path(instance, filename):
    """为分类图片生成上传路径"""
    ext = filename.split('.')[-1]
    new_filename = f"category_{instance.pk}_{instance.category_name_en}.{ext}"
    return os.path.join('categories', new_filename)

class Brand(models.Model):
    name = models.CharField(max_length=100, verbose_name='品牌名称')
    description = models.TextField(blank=True, null=True, verbose_name='品牌描述')
    logo_url = models.CharField(max_length=255, null=True, blank=True, verbose_name='logoURL')
    status = models.BooleanField(default=True, verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'gallery_brand'
        verbose_name = '品牌'
        verbose_name_plural = '品牌列表'
        ordering = ['name']

    def __str__(self):
        return self.name

class Category(models.Model):
    STATUS_CHOICES = (
        (1, '启用'),
        (0, '禁用'),
    )
    
    LEVEL_CHOICES = (
        (1, '一级分类'),
        (2, '二级分类'),
        (3, '三级分类'),
        (4, '四级分类'),
        (5, '五级分类'),
        (6, '六级分类'),
        (7, '七级分类'),
    )

    id = models.AutoField(primary_key=True, verbose_name='分类ID')
    category_name_en = models.CharField(max_length=100, verbose_name='英文名称')
    category_name_zh = models.CharField(max_length=100, verbose_name='中文名称')
    description = models.TextField(blank=True, null=True, verbose_name='分类描述')
    image = models.ImageField(
        upload_to=category_image_path, 
        blank=True, 
        null=True, 
        verbose_name='分类图片'
    )
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children',
        verbose_name='父分类'
    )
    rank_id = models.IntegerField(default=0, verbose_name='排序ID')
    original_data = models.TextField('原始数据', blank=True, null=True)
    level = models.IntegerField(
        choices=LEVEL_CHOICES,
        default=1,
        verbose_name='分类层级'
    )
    is_last_level = models.BooleanField(
        default=False, 
        verbose_name='是否最后一级'
    )
    status = models.IntegerField(
        choices=STATUS_CHOICES,
        default=1,
        verbose_name='状态'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'gallery_category'
        verbose_name = '分类'
        verbose_name_plural = '分类'
        ordering = ['rank_id', 'id']

    def __str__(self):
        return f"{self.category_name_zh} ({self.category_name_en})"

    def clean(self):
        if self.parent:
            # 检查层级深度
            current_parent = self.parent
            depth = 1
            while current_parent.parent:
                depth += 1
                current_parent = current_parent.parent
                
            if depth >= 7:
                raise ValidationError('分类层级不能超过7级')
                
            if self.level <= self.parent.level:
                raise ValidationError('子类目的层级必须大于父类目的层级')
        elif self.level != 1:
            raise ValidationError('没有父类目时，必须是一级分类')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        
        if self.image and not self.image.name.startswith(f'categories/category_{self.pk}_'):
            old_path = self.image.path
            filename = os.path.basename(self.image.name)
            ext = filename.split('.')[-1]
            
            new_filename = f"category_{self.pk}_{self.category_name_en}.{ext}"
            new_path = os.path.join('categories', new_filename)
            
            self.image.name = new_path
            super().save(update_fields=['image'])
            
            if os.path.exists(old_path):
                new_full_path = os.path.join(settings.MEDIA_ROOT, new_path)
                os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
                os.rename(old_path, new_full_path)

    @property
    def full_name(self):
        if self.parent:
            return f"{self.parent.full_name} > {self.category_name_zh}"
        return self.category_name_zh

    def get_level_display(self):
        return dict(self.LEVEL_CHOICES).get(self.level, '')

    def get_ancestors(self):
        """获取所有上级分类"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors[::-1]  # 反转列表，从最上级开始

    def get_descendants(self):
        """获取所有下级分类"""
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants

class SPU(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('math_design', '设计款'),
        ('ready_made', '现货款'),
        ('raw_material', '材料'),
        ('packing_material', '包材'),
    ]

    spu_code = models.CharField(max_length=50, unique=True, verbose_name='SPU编码')
    spu_name = models.CharField(max_length=100, verbose_name='SPU名称')
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, verbose_name='产品类型')
    spu_remark = models.TextField(blank=True, null=True, verbose_name='备注')
    sales_channel = models.CharField(max_length=20, blank=True, null=True, verbose_name='销售渠道')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='品牌')
    poc = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='专员')
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT,
        verbose_name='类目',
        null=False,
        blank=False
    )
    status = models.BooleanField(default=True, verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'gallery_spu'
        verbose_name = 'SPU'
        verbose_name_plural = 'SPU列表'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.spu_code} - {self.spu_name}"

class SKU(models.Model):
    PLATING_PROCESS_CHOICES = (
        ('none', '无电镀'),
        ('gold', '镀金'),
        ('silver', '镀银'),
        ('nickel', '镀镍'),
        ('chrome', '镀铬'),
        ('copper', '镀铜'),
        ('other', '其他'),
    )
    
    sku_code = models.CharField(max_length=50, unique=True, verbose_name='SKU编码')
    sku_name = models.CharField(max_length=100, verbose_name='SKU名称')
    spu = models.ForeignKey(SPU, on_delete=models.CASCADE, verbose_name='所属SPU', null=True)
    material = models.CharField(max_length=50, verbose_name='材质')
    color = models.CharField(max_length=50, verbose_name='颜色')
    plating_process = models.CharField(max_length=20, choices=PLATING_PROCESS_CHOICES, verbose_name='电镀工艺')
    surface_treatment = models.CharField(max_length=100, null=True, blank=True, verbose_name='表面处理')
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='重量(g)')
    length = models.IntegerField(null=True, blank=True, verbose_name='长(mm)')
    width = models.IntegerField(null=True, blank=True, verbose_name='宽(mm)')
    height = models.IntegerField(null=True, blank=True, verbose_name='高(mm)')
    other_dimensions = models.CharField(max_length=25, null=True, blank=True, verbose_name='其他尺寸')
    suppliers_list = models.TextField(verbose_name='供应商列表', default='[]', blank=True)
    img_url = models.CharField(max_length=255, null=True, blank=True, verbose_name='图片URL')
    is_reviewed = models.BooleanField(default=False, verbose_name='是否已审核')
    status = models.BooleanField(default=True, verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'gallery_sku'
        verbose_name = 'SKU'
        verbose_name_plural = 'SKU列表'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sku_code} - {self.sku_name}"
