from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Brand, Category, SPU, SKU
from .forms import BrandForm, CategoryForm, SPUForm, SKUForm
from .sync import ProductSync
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import Lower
from django.utils import timezone

# Brand views
@login_required
def brand_list(request):
    brands = Brand.objects.all()
    return render(request, 'gallery/brand/list.html', {
        'brands': brands,
        'active_menu': 'gallery',
        'active_submenu': 'brand'
    })

@login_required
def brand_detail(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    return render(request, 'gallery/brand/detail.html', {
        'brand': brand,
        'active_menu': 'gallery',
        'active_submenu': 'brand'
    })

@login_required
def brand_edit(request, pk=None):
    brand = None if pk is None else get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        form = BrandForm(request.POST, instance=brand)
        if form.is_valid():
            form.save()
            messages.success(request, '品牌保存成功！')
            return redirect('gallery:brand_list')
    else:
        form = BrandForm(instance=brand)
    
    return render(request, 'gallery/brand/edit.html', {
        'form': form,
        'brand': brand,
        'active_menu': 'gallery',
        'active_submenu': 'brand'
    })

@login_required
def brand_delete(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        brand.delete()
        messages.success(request, '品牌删除成功！')
        return redirect('gallery:brand_list')
    return render(request, 'gallery/brand/delete.html', {
        'brand': brand,
        'active_menu': 'gallery',
        'active_submenu': 'brand'
    })

# Category views
@login_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'gallery/category/list.html', {
        'categories': categories,
        'active_menu': 'gallery',
        'active_submenu': 'category'
    })

@login_required
def category_detail(request, pk):
    category = get_object_or_404(Category, pk=pk)
    return render(request, 'gallery/category/detail.html', {
        'category': category,
        'active_menu': 'gallery',
        'active_submenu': 'category'
    })

@login_required
def category_edit(request, pk=None):
    category = None if pk is None else get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, '分类保存成功！')
            return redirect('gallery:category_list')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'gallery/category/edit.html', {
        'form': form,
        'category': category,
        'active_menu': 'gallery',
        'active_submenu': 'category'
    })

@login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, '分类删除成功！')
        return redirect('gallery:category_list')
    return render(request, 'gallery/category/delete.html', {
        'category': category,
        'active_menu': 'gallery',
        'active_submenu': 'category'
    })

# SPU views
@login_required
def spu_list(request):
    spus = SPU.objects.all()
    return render(request, 'gallery/spu/list.html', {
        'spus': spus,
        'active_menu': 'gallery',
        'active_submenu': 'spu'
    })

@login_required
def spu_detail(request, pk):
    spu = get_object_or_404(SPU, pk=pk)
    return render(request, 'gallery/spu/detail.html', {
        'spu': spu,
        'active_menu': 'gallery',
        'active_submenu': 'spu'
    })

@login_required
def spu_edit(request, pk=None):
    spu = None if pk is None else get_object_or_404(SPU, pk=pk)
    if request.method == 'POST':
        form = SPUForm(request.POST, instance=spu)
        if form.is_valid():
            form.save()
            messages.success(request, 'SPU保存成功！')
            return redirect('gallery:spu_list')
    else:
        form = SPUForm(instance=spu)
    
    return render(request, 'gallery/spu/edit.html', {
        'form': form,
        'spu': spu,
        'active_menu': 'gallery',
        'active_submenu': 'spu'
    })

@login_required
def spu_delete(request, pk):
    spu = get_object_or_404(SPU, pk=pk)
    if request.method == 'POST':
        spu.delete()
        messages.success(request, 'SPU删除成功！')
        return redirect('gallery:spu_list')
    return render(request, 'gallery/spu/delete.html', {
        'spu': spu,
        'active_menu': 'gallery',
        'active_submenu': 'spu'
    })

# SKU views
@login_required
def sku_list(request):
    # 获取筛选参数
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category')
    selected_color = request.GET.get('color')
    selected_material = request.GET.get('material')
    selected_plating = request.GET.get('plating')
    selected_product_type = request.GET.get('product_type')

    # 构建查询
    skus = SKU.objects.select_related('spu', 'spu__category').all()

    # 应用筛选条件
    if search_query:
        skus = skus.filter(
            Q(sku_code__icontains=search_query) |
            Q(sku_name__icontains=search_query) |
            Q(spu__spu_code__icontains=search_query) |
            Q(spu__spu_name__icontains=search_query)
        )
    
    if category_id:
        skus = skus.filter(spu__category_id=category_id)
    
    if selected_color:
        skus = skus.filter(color=selected_color)
    
    if selected_material:
        skus = skus.filter(material=selected_material)
    
    if selected_plating:
        skus = skus.filter(plating_process=selected_plating)
    
    if selected_product_type:
        skus = skus.filter(spu__product_type=selected_product_type)

    # 获取筛选选项
    categories = Category.objects.annotate(
        sku_count=Count('spu__sku', distinct=True),
        indent=Lower('category_name_en')
    ).order_by('level', 'rank_id')

    colors = SKU.objects.exclude(color='').values_list('color', flat=True).distinct()
    materials = SKU.objects.exclude(material='').values_list('material', flat=True).distinct()
    product_types = (
        SPU.objects.exclude(product_type='')
        .values('product_type')
        .annotate(count=Count('sku'))
        .values('product_type', 'count')
        .filter(product_type__isnull=False)
    )

    # 修改产品类型的数据处理
    product_type_choices = dict(SPU.PRODUCT_TYPE_CHOICES)
    product_types_data = []
    for pt in product_types:
        product_type = pt['product_type']
        if product_type and product_type in product_type_choices:
            product_types_data.append({
                'value': product_type,
                'label': product_type_choices[product_type],
                'count': pt['count']
            })

    # 分页
    paginator = Paginator(skus, 20)  # 每页显示20条
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'skus': page_obj,
        'categories': categories,
        'colors': colors,
        'materials': materials,
        'platings': SKU.PLATING_PROCESS_CHOICES,
        'product_types': product_types_data,
        'search_query': search_query,
        'category_id': int(category_id) if category_id else None,
        'selected_color': selected_color,
        'selected_material': selected_material,
        'selected_plating': selected_plating,
        'selected_product_type': selected_product_type,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
        'paginator': paginator,
        'active_menu': 'gallery',
        'active_submenu': 'sku'
    }

    return render(request, 'gallery/sku/list.html', context)

@login_required
def sku_detail(request, pk):
    sku = get_object_or_404(SKU, pk=pk)
    return render(request, 'gallery/sku/detail.html', {
        'sku': sku,
        'active_menu': 'gallery',
        'active_submenu': 'sku'
    })

@login_required
def sku_edit(request, pk=None):
    sku = None if pk is None else get_object_or_404(SKU, pk=pk)
    if request.method == 'POST':
        form = SKUForm(request.POST, instance=sku)
        if form.is_valid():
            form.save()
            messages.success(request, 'SKU保存成功！')
            return redirect('gallery:sku_list')
    else:
        form = SKUForm(instance=sku)
    
    return render(request, 'gallery/sku/edit.html', {
        'form': form,
        'sku': sku,
        'active_menu': 'gallery',
        'active_submenu': 'sku'
    })

@login_required
def sku_delete(request, pk):
    sku = get_object_or_404(SKU, pk=pk)
    if request.method == 'POST':
        sku.delete()
        messages.success(request, 'SKU删除成功！')
        return redirect('gallery:sku_list')
    return render(request, 'gallery/sku/delete.html', {
        'sku': sku,
        'active_menu': 'gallery',
        'active_submenu': 'sku'
    })

@login_required
def sync_products(request):
    try:
        sync = ProductSync()
        count = sync.sync_products()
        messages.success(request, f'成功同步 {count} 个商品')
    except Exception as e:
        messages.error(request, f'同步失败：{str(e)}')
    return redirect('gallery:sku_list')

@login_required
def report(request):
    """商品报表页面"""
    today = timezone.now()
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 总体统计
    total_products = SPU.objects.count()
    new_products_today = SPU.objects.filter(created_at__date=today.date()).count()
    new_products_month = SPU.objects.filter(created_at__gte=month_start).count()
    
    # 计算活跃商品（有库存或有销量的商品）
    active_products = SPU.objects.filter(
        Q(sku__inventories__quantity__gt=0) |
        Q(sku__order_items__isnull=False)
    ).distinct().count()
    
    # 计算缺货商品
    out_of_stock = SPU.objects.filter(
        sku__inventories__quantity=0
    ).distinct().count()
    
    # 计算百分比
    active_products_percentage = round((active_products / total_products * 100) if total_products > 0 else 0, 1)
    out_of_stock_percentage = round((out_of_stock / total_products * 100) if total_products > 0 else 0, 1)
    
    # 计算环比（与上月相比的增长率）
    last_month_start = month_start.replace(month=month_start.month-1 if month_start.month > 1 else 12)
    last_month_new = SPU.objects.filter(
        created_at__gte=last_month_start,
        created_at__lt=month_start
    ).count()
    month_over_month = round(
        ((new_products_month - last_month_new) / last_month_new * 100) if last_month_new > 0 else 0,
        1
    )
    
    # 按品牌统计
    brands = Brand.objects.annotate(
        total_products=Count('spu', distinct=True),
        active_products=Count(
            'spu',
            filter=Q(spu__sku__inventories__quantity__gt=0) |
                   Q(spu__sku__order_items__isnull=False),
            distinct=True
        ),
        new_products=Count(
            'spu',
            filter=Q(spu__created_at__gte=month_start),
            distinct=True
        ),
        out_of_stock=Count(
            'spu',
            filter=Q(spu__sku__inventories__quantity=0),
            distinct=True
        )
    )
    
    context = {
        'total_products': total_products,
        'new_products_today': new_products_today,
        'new_products_month': new_products_month,
        'active_products': active_products,
        'active_products_percentage': active_products_percentage,
        'out_of_stock': out_of_stock,
        'out_of_stock_percentage': out_of_stock_percentage,
        'month_over_month': month_over_month,
        'brands': brands,
        'current_month': today.strftime('%Y年%m月'),
        'active_menu': 'gallery',
        'active_submenu': 'report'
    }
    
    return render(request, 'gallery/report.html', context)
