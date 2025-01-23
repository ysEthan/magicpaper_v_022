from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, F, Q
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from decimal import Decimal
import json
from gallery.models import SKU
from storage.models import Inventory, StockIn, StockOut, Warehouse
from trade.models import Order
from procurement.models import PurchaseOrder
from logistics.models import Package
from gallery.models import Brand
from gallery.models import Category
from .forms import GuestOrderForm, GuestOrderQueryForm
from trade.services import WDTOrderSync
from django.contrib import messages
from django.shortcuts import redirect
import uuid
from django.http import JsonResponse
import random  # 添加random模块导入
from django.urls import reverse_lazy, reverse

@login_required
def index_view(request):
    today = timezone.now()
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_start = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 商品统计 - 使用单次查询
    products = SKU.objects.all()
    total_products = products.count()
    new_products_today = products.filter(created_at__date=today.date()).count()
    new_products_month = products.filter(created_at__gte=month_start).count()
    new_products_week = products.filter(created_at__gte=week_start).count()
    
    # 订单统计 - 使用单次查询
    orders = Order.objects.all()
    total_orders = orders.count()
    pending_orders = orders.filter(status__in=['pending', 'picking']).count()
    today_orders = orders.filter(order_place_time__date=today.date()).count()
    week_orders = orders.filter(order_place_time__gte=week_start).count()
    month_sales = orders.filter(
        order_place_time__gte=month_start
    ).annotate(
        usd_amount=F('total_amount') * F('exchange_rate_to_usd')
    ).aggregate(
        total=Sum('usd_amount')
    )['total'] or 0
    
    # 采购统计 - 使用单次查询
    purchase_orders = PurchaseOrder.objects.all()
    active_purchase_orders = purchase_orders.filter(
        status__in=['draft', 'submitted', 'approved', 'processing']
    ).count()
    draft_purchase_orders = purchase_orders.filter(status='draft').count()
    today_purchase_orders = purchase_orders.filter(created_at__date=today.date()).count()
    week_purchase_orders = purchase_orders.filter(created_at__gte=week_start).count()
    month_purchase = purchase_orders.filter(
        created_at__gte=month_start
    ).aggregate(
        total=Sum(F('purchaseorderitem__quantity') * F('purchaseorderitem__unit_price'))
    )['total'] or 0
    
    # 物流统计 - 使用单次查询
    packages = Package.objects.all()
    # 使用 annotate 和 Count 来一次性获取所有状态的包裹数量，排除已取消的包裹
    package_stats = packages.exclude(pkg_status_code='4').values('pkg_status_code').annotate(
        count=Count('id')
    )
    
    # 初始化各状态包裹数量
    pending_shipment_packages = 0  # 待发货 (0)
    waiting_pickup_packages = 0    # 待揽收 (1)
    in_transit_packages = 0        # 转运中 (2)
    delivered_packages = 0         # 已签收 (3)
    
    # 遍历统计结果，分配到对应的变量
    stats_dict = {stat['pkg_status_code']: stat['count'] for stat in package_stats}
    pending_shipment_packages = stats_dict.get('0', 0)  # 待发货
    waiting_pickup_packages = stats_dict.get('1', 0)    # 待揽收
    in_transit_packages = stats_dict.get('2', 0)        # 转运中
    delivered_packages = stats_dict.get('3', 0)         # 已签收
    
    # 计算包裹总数（排除已取消的包裹）
    total_packages = sum(stat['count'] for stat in package_stats)
    
    # 获取本月运费
    month_shipping_cost = packages.filter(
        created_at__gte=month_start
    ).aggregate(
        total=Sum('carrier_cost')
    )['total'] or 0

    # 库存统计 - 使用单次查询
    inventory = Inventory.objects.all()
    total_inventory = inventory.aggregate(total=Sum('quantity'))['total'] or 0
    
    # 从入库单获取本月入库数量
    month_stock_in = StockIn.objects.filter(
        stock_in_time__gte=month_start
    ).aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    # 从出库单获取本月出库数量和成本
    month_stock_out = StockOut.objects.filter(
        stock_out_time__gte=month_start
    ).aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    # 计算库存周转率
    # 1. 获取过去12个月的出库成本总额
    year_start = today - timedelta(days=365)
    annual_stock_out_cost = StockOut.objects.filter(
        stock_out_time__gte=year_start
    ).aggregate(
        total=Sum(F('quantity') * F('inventory__stock_in__unit_cost'))
    )['total'] or 0
    
    # 2. 获取当前库存总值
    current_inventory_value = inventory.select_related('stock_in').aggregate(
        total=Sum(F('quantity') * F('stock_in__unit_cost'))
    )['total'] or 0
    
    # 3. 计算库存周转率（年化）
    inventory_turnover = annual_stock_out_cost / current_inventory_value if current_inventory_value else 0
    
    # 趋势数据 - 优化查询，使用聚合函数
    dates = [(today - timedelta(days=i)).date() for i in range(29, -1, -1)]
    
    # 商品趋势
    product_trend = list(SKU.objects.filter(
        created_at__date__gte=dates[0]
    ).values('created_at__date').annotate(
        count=Count('id')
    ).order_by('created_at__date'))
    
    product_trend_data = [0] * 30
    for item in product_trend:
        index = dates.index(item['created_at__date'])
        product_trend_data[index] = item['count']
    
    # 订单趋势
    order_trend = list(Order.objects.filter(
        order_place_time__date__gte=dates[0]
    ).values('order_place_time__date').annotate(
        count=Count('id')
    ).order_by('order_place_time__date'))
    
    order_trend_data = [0] * 30
    for item in order_trend:
        index = dates.index(item['order_place_time__date'])
        order_trend_data[index] = item['count']
    
    # 采购趋势
    purchase_trend = list(PurchaseOrder.objects.filter(
        created_at__date__gte=dates[0]
    ).values('created_at__date').annotate(
        amount=Sum(F('purchaseorderitem__quantity') * F('purchaseorderitem__unit_price'))
    ).order_by('created_at__date'))
    
    purchase_trend_data = [0] * 30
    for item in purchase_trend:
        index = dates.index(item['created_at__date'])
        purchase_trend_data[index] = float(item['amount'] or 0)
    
    # 物流趋势
    logistics_trend = list(Package.objects.filter(
        created_at__date__gte=dates[0]
    ).values('created_at__date').annotate(
        count=Count('id')
    ).order_by('created_at__date'))
    
    logistics_trend_data = [0] * 30
    for item in logistics_trend:
        index = dates.index(item['created_at__date'])
        logistics_trend_data[index] = item['count']

    # 库存趋势
    inventory_trend = list(Inventory.objects.filter(
        updated_at__date__gte=dates[0]
    ).values('updated_at__date').annotate(
        total=Sum('quantity')
    ).order_by('updated_at__date'))
    
    inventory_trend_data = [0] * 30
    for item in inventory_trend:
        index = dates.index(item['updated_at__date'])
        inventory_trend_data[index] = item['total'] or 0
    
    dashboard_data = {
        'total_products': total_products,
        'new_products_today': new_products_today,
        'new_products_month': new_products_month,
        'new_products_week': new_products_week,
        'product_trend': json.dumps(product_trend_data),
        
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'today_orders': today_orders,
        'week_orders': week_orders,
        'month_sales': month_sales,
        'order_trend': json.dumps(order_trend_data),
        
        'active_purchase_orders': active_purchase_orders,
        'draft_purchase_orders': draft_purchase_orders,
        'today_purchase_orders': today_purchase_orders,
        'week_purchase_orders': week_purchase_orders,
        'month_purchase': month_purchase,
        'purchase_trend': json.dumps(purchase_trend_data),
        
        'total_packages': total_packages,
        'pending_shipment_packages': pending_shipment_packages,
        'waiting_pickup_packages': waiting_pickup_packages,
        'in_transit_packages': in_transit_packages,
        'delivered_packages': delivered_packages,
        'month_shipping_cost': month_shipping_cost,
        'logistics_trend': json.dumps(logistics_trend_data),

        'total_inventory': total_inventory,
        'month_stock_in': month_stock_in,
        'month_stock_out': month_stock_out,
        'total_inventory_value': current_inventory_value,
        'inventory_turnover': round(inventory_turnover, 2),
        'inventory_trend': json.dumps(inventory_trend_data),
        
        'current_month': today.strftime('%Y年%m月')
    }
    
    return render(request, 'page/index.html', dashboard_data)

def get_trend_data(model, date_field, days=7):
    """获取趋势数据"""
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    daily_counts = model.objects.filter(**{
        f"{date_field}__gte": start_date,
        f"{date_field}__lt": end_date + timedelta(days=1)
    }).annotate(
        date=TruncDate(date_field)
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # 填充没有数据的日期
    result = []
    current_date = start_date.date()
    counts_dict = {item['date']: item['count'] for item in daily_counts}
    
    while current_date <= end_date.date():
        result.append(counts_dict.get(current_date, 0))
        current_date += timedelta(days=1)
    
    return result

def get_inventory_trend(days=7):
    """获取库存趋势数据"""
    from gallery.models import Inventory
    from django.db.models import Sum
    from django.db.models.functions import TruncDate
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    daily_totals = Inventory.objects.filter(
        updated_at__gte=start_date,
        updated_at__lt=end_date + timedelta(days=1)
    ).annotate(
        date=TruncDate('updated_at')
    ).values('date').annotate(
        total=Sum('quantity')
    ).order_by('date')
    
    # 填充没有数据的日期
    result = []
    current_date = start_date.date()
    totals_dict = {item['date']: item['total'] for item in daily_totals}
    
    while current_date <= end_date.date():
        result.append(totals_dict.get(current_date, 0))
        current_date += timedelta(days=1)
    
    return result

def product_list(request):
    """商品展示页面"""
    # 获取筛选参数
    warehouse_id = request.GET.get('warehouse')
    platform = request.GET.get('platform')
    brand_id = request.GET.get('brand')
    search_query = request.GET.get('search', '').strip()
    category_id = request.GET.get('category')
    
    # 获取所有启用的仓库
    warehouses = Warehouse.objects.filter(status=True).order_by('warehouse_code')
    
    # 获取所有品牌
    brands = Brand.objects.filter(status=True).order_by('name')
    
    # 获取所有启用的二级品类
    categories = Category.objects.filter(
        status=True,  # 状态为启用
        level=2,      # 二级类目
        parent__status=True  # 父类目也必须启用
    ).order_by('category_name_zh')
    
    # 构建查询
    products_query = SKU.objects.filter(status=True).select_related('spu')
    
    # 搜索过滤
    if search_query:
        products_query = products_query.filter(
            Q(sku_code__icontains=search_query) |
            Q(sku_name__icontains=search_query)
        )
    
    # 平台筛选
    if platform:
        products_query = products_query.filter(spu__product_type=platform)
    
    # 品牌筛选
    if brand_id:
        products_query = products_query.filter(spu__brand_id=brand_id)
    
    # 品类筛选
    if category_id:
        try:
            # 获取选中的类目
            selected_category = Category.objects.get(id=category_id)
            
            # 如果是二级类目，获取其所有子类目（包括自身）
            if selected_category.level == 2:
                category_ids = list(Category.objects.filter(
                    Q(id=category_id) |  # 包含所选类目自身
                    Q(parent__id=category_id) |  # 包含直接子类目
                    Q(parent__parent__id=category_id)  # 包含孙子类目
                ).values_list('id', flat=True))
            else:
                category_ids = [category_id]
            
            # 使用所有相关类目ID进行筛选
            products_query = products_query.filter(spu__category_id__in=category_ids)
        except Category.DoesNotExist:
            pass
    
    # 仓库筛选
    if warehouse_id:
        # 如果选择了特定仓库，只统计该仓库的库存和成本
        products = products_query.annotate(
            total_stock=Sum('inventories__quantity', 
                          filter=Q(inventories__warehouse_id=warehouse_id)),
            total_cost=Sum(F('inventories__quantity') * F('inventories__stock_in__unit_cost'),
                          filter=Q(inventories__warehouse_id=warehouse_id))
        ).filter(total_stock__gt=0).order_by('sku_code')
    else:
        # 否则统计所有仓库的总库存和成本
        products = products_query.annotate(
            total_stock=Sum('inventories__quantity'),
            total_cost=Sum(F('inventories__quantity') * F('inventories__stock_in__unit_cost'))
        ).filter(total_stock__gt=0).order_by('sku_code')
    
    # 计算平均成本（显示110%的成本）
    markup_rate = Decimal('1.1')  # 使用Decimal类型的1.1
    for product in products:
        if product.total_stock and product.total_cost:
            actual_avg_cost = product.total_cost / product.total_stock
            product.avg_cost = round(actual_avg_cost * markup_rate, 2)  # 使用Decimal进行计算
        else:
            product.avg_cost = Decimal('0')
    
    # 处理图片URL
    for product in products:
        if product.img_url and not product.img_url.startswith(('http://', 'https://')):
            product.img_url = f"/media/{product.img_url}"
    
    # 产品类型选项
    PRODUCT_TYPE_CHOICES = [
        ('math_design', '设计款'),
        ('ready_made', '现货款'),
        ('raw_material', '材料'),
        ('packing_material', '包材'),
    ]
    
    return render(request, 'page/product_list.html', {
        'products': products,
        'warehouses': warehouses,
        'current_warehouse': warehouse_id,
        'product_types': PRODUCT_TYPE_CHOICES,
        'current_platform': platform,
        'brands': brands,
        'current_brand': brand_id,
        'search_query': search_query,
        'categories': categories,
        'current_category': category_id,
        'page_title': '商品列表',
    })

def products2(request):
    """商品展示页面"""
    # 定义需要排除的品牌和仓库
    excluded_brands = ['hitems', 'Melyn']
    excluded_warehouses = ['员工领用仓', '样品3号仓']
    
    # 获取筛选参数
    warehouse_id = request.GET.get('warehouse')
    platform = request.GET.get('platform')
    brand_id = request.GET.get('brand')
    search_query = request.GET.get('search', '').strip()
    category_id = request.GET.get('category')
    
    # 获取所有启用的仓库（排除特定仓库）
    warehouses = Warehouse.objects.filter(
        status=True
    ).exclude(
        warehouse_name__in=excluded_warehouses
    ).order_by('warehouse_code')
    
    # 获取所有品牌（排除特定品牌）
    brands = Brand.objects.filter(
        status=True
    ).exclude(
        name__in=excluded_brands
    ).order_by('name')
    
    # 获取所有启用的二级品类
    categories = Category.objects.filter(
        status=True,  # 状态为启用
        level=2,      # 二级类目
        parent__status=True  # 父类目也必须启用
    ).order_by('category_name_zh')
    
    # 获取需要排除的品牌ID列表
    excluded_brand_ids = list(Brand.objects.filter(
        name__in=excluded_brands
    ).values_list('id', flat=True))
    
    # 构建基础查询，排除特定品牌的商品
    products_query = SKU.objects.filter(
        status=True
    ).exclude(
        spu__brand_id__in=excluded_brand_ids  # 使用exclude和__in来排除
    ).select_related('spu')
    
    # 搜索过滤
    if search_query:
        products_query = products_query.filter(
            Q(sku_code__icontains=search_query) |
            Q(sku_name__icontains=search_query)
        )
    
    # 平台筛选
    if platform:
        products_query = products_query.filter(spu__product_type=platform)
    
    # 品牌筛选
    if brand_id:
        products_query = products_query.filter(spu__brand_id=brand_id)
    
    # 品类筛选
    if category_id:
        try:
            selected_category = Category.objects.get(id=category_id)
            if selected_category.level == 2:
                category_ids = list(Category.objects.filter(
                    Q(id=category_id) |
                    Q(parent__id=category_id) |
                    Q(parent__parent__id=category_id)
                ).values_list('id', flat=True))
            else:
                category_ids = [category_id]
            products_query = products_query.filter(spu__category_id__in=category_ids)
        except Category.DoesNotExist:
            pass
    
    # 获取需要排除的仓库ID列表
    excluded_warehouse_ids = list(Warehouse.objects.filter(
        warehouse_name__in=excluded_warehouses
    ).values_list('id', flat=True))
    
    # 仓库筛选
    if warehouse_id:
        # 如果选择了特定仓库，只统计该仓库的库存和成本
        products = products_query.annotate(
            total_stock=Sum('inventories__quantity', 
                          filter=Q(inventories__warehouse_id=warehouse_id)),
            total_cost=Sum(F('inventories__quantity') * F('inventories__stock_in__unit_cost'),
                          filter=Q(inventories__warehouse_id=warehouse_id))
        ).filter(total_stock__gt=0).order_by('sku_code')
    else:
        # 否则统计所有仓库的总库存和成本（排除特定仓库）
        products = products_query.annotate(
            total_stock=Sum('inventories__quantity',
                          filter=~Q(inventories__warehouse_id__in=excluded_warehouse_ids)),
            total_cost=Sum(F('inventories__quantity') * F('inventories__stock_in__unit_cost'),
                          filter=~Q(inventories__warehouse_id__in=excluded_warehouse_ids))
        ).filter(total_stock__gt=0).order_by('sku_code')
    
    # 计算平均成本（显示110%的成本）
    markup_rate = Decimal('1.1')
    for product in products:
        if product.total_stock and product.total_cost:
            actual_avg_cost = product.total_cost / product.total_stock
            product.avg_cost = round(actual_avg_cost * markup_rate, 2)
        else:
            product.avg_cost = Decimal('0')
    
    # 处理图片URL
    for product in products:
        if product.img_url and not product.img_url.startswith(('http://', 'https://')):
            product.img_url = f"/media/{product.img_url}"
    
    # 产品类型选项
    PRODUCT_TYPE_CHOICES = [
        ('math_design', '设计款'),
        ('ready_made', '现货款'),
        ('raw_material', '材料'),
        ('packing_material', '包材'),
    ]
    
    return render(request, 'page/product_list.html', {
        'products': products,
        'warehouses': warehouses,
        'current_warehouse': warehouse_id,
        'product_types': PRODUCT_TYPE_CHOICES,
        'current_platform': platform,
        'brands': brands,
        'current_brand': brand_id,
        'search_query': search_query,
        'categories': categories,
        'current_category': category_id,
        'page_title': '商品列表',
    })

def get_sku_price(request):
    """获取SKU价格"""
    sku_code = request.GET.get('sku_code')
    try:
        sku = SKU.objects.get(sku_code=sku_code)
        # 计算SKU的平均成本
        total_stock = sku.inventories.aggregate(total=Sum('quantity'))['total'] or 0
        total_cost = sku.inventories.aggregate(
            total=Sum(F('quantity') * F('stock_in__unit_cost'))
        )['total'] or 0
        
        if total_stock > 0:
            avg_cost = total_cost / total_stock
            # 设置价格为平均成本的110%
            price = round(float(avg_cost * Decimal('1.1')), 2)
        else:
            # 如果没有库存，使用默认价格
            price = 0
        
        # 处理图片URL
        img_url = sku.img_url
        if img_url and not img_url.startswith(('http://', 'https://')):
            img_url = f"/media/{img_url}"
            
        return JsonResponse({
            'success': True,
            'price': price,
            'sku_name': sku.sku_name,
            'img_url': img_url
        })
    except SKU.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '商品不存在'
        })

def guest_order(request):
    """访客下单页面"""
    if request.method == 'POST':
        form = GuestOrderForm(request.POST)
        if form.is_valid():
            try:
                # 获取表单数据
                data = form.cleaned_data
                items = data['items_json']  # 已经在表单验证中转换为Python对象
                
                # 验证所有SKU是否存在并获取价格
                invalid_skus = []
                order_items = []
                for item in items:
                    try:
                        sku = SKU.objects.get(sku_code=item['sku_code'])
                        # 计算SKU的平均成本
                        total_stock = sku.inventories.aggregate(total=Sum('quantity'))['total'] or 0
                        total_cost = sku.inventories.aggregate(
                            total=Sum(F('quantity') * F('stock_in__unit_cost'))
                        )['total'] or 0
                        
                        if total_stock > 0:
                            avg_cost = total_cost / total_stock
                            # 设置价格为平均成本的110%
                            price = round(float(avg_cost * Decimal('1.1')), 2)
                        else:
                            # 如果没有库存，使用默认价格
                            price = 0
                            
                        order_items.append({
                            "actualNum": item['quantity'],
                            "discount": 1,
                            "giftType": 0,
                            "price": price,
                            "specNo": item['sku_code']
                        })
                    except SKU.DoesNotExist:
                        invalid_skus.append(item['sku_code'])
                
                if invalid_skus:
                    messages.error(request, f'以下商品编码不存在：{", ".join(invalid_skus)}')
                    return render(request, 'page/guest_order.html', {
                        'form': form,
                        'active_menu': 'page',
                        'active_submenu': 'guest_order'
                    })
                
                # 生成订单号
                today = timezone.now().strftime('%y%m%d')
                # 从缓存中获取当天的订单序号
                cache_key = f'guest_order_counter_{today}'
                counter = cache.get(cache_key, 0) + 1
                # 如果超过999，重置为1
                if counter > 999:
                    counter = 1
                # 更新缓存，设置过期时间为48小时（确保跨天时不会出问题）
                cache.set(cache_key, counter, 48*60*60)
                # 生成订单号：GO + 年月日 + 四位随机数 + 三位序号
                random_number = str(random.randint(1000, 9999))  # 生成4位随机数
                order_number = f"GO{today}{random_number}{counter:03d}"
                
                # 获取当前时间
                current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                # 获取48小时后的时间
                over_time = (timezone.now() + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
                
                # 构建旺店通API请求数据
                order_data = [{
                    "baseInfo": {
                        "shopName": "jjewelry",
                        "tid": order_number,
                        "deliveryTerm": 1,
                        "currencyCode": "USD",
                        "tradeTime": current_time,
                        "payTime": current_time,
                        "overTime": over_time,
                        "sellerFullName": "无",
                        "buyerMessage": data['remark'],
                        "csRemark": "",
                        "erpRemark": "",
                        "warehouseName": "义乌仓",
                        "logisticsName": "",
                        "domesticLogisticsName": "",
                        "paid": 0,
                        "postAmount": 0,
                        "discount": 1
                    },
                    "goods": order_items,
                    "receiverInfo": {
                        "receiverName": data['name'],
                        "buyerNick": "",
                        "idCardType": "",
                        "idCard": "",
                        "receiverMobile": data['phone'],
                        "receiverTelno": "",
                        "buyerEmail": "",
                        "receiverCountryName": "",
                        "receiverProvince": "",
                        "receiverCity": "",
                        "receiverDistrict": "",
                        "receiverZip": "",
                        "receiverAddress": data['address'],
                        "receiverAddress2": "",
                        "receiverAddress3": ""
                    }
                }]
                
                # 打印请求数据
                print("\n=== 旺店通API请求数据 ===")
                print(json.dumps(order_data, indent=2, ensure_ascii=False))
                
                # 调用旺店通API创建订单
                sync_service = WDTOrderSync()
                response = sync_service.create_order(order_data)
                
                # 打印API响应
                print("\n=== 旺店通API响应数据 ===")
                print(json.dumps(response, indent=2, ensure_ascii=False))
                
                # 检查响应状态
                if isinstance(response, dict) and response.get('code') == 0:
                    messages.success(request, f'订单提交成功！订单号：{order_number}')
                    
                    # 立即触发订单同步，只同步最近1分钟的订单
                    try:
                        # 获取1分钟前的时间
                        start_time = (timezone.now() - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
                        sync_result = sync_service.sync_orders(start_date=start_time)
                        print("\n=== 订单同步结果 ===")
                        print(json.dumps(sync_result, indent=2, ensure_ascii=False))
                    except Exception as e:
                        print(f"\n=== 订单同步异常 ===\n{str(e)}")
                    
                    # 使用reverse生成正确的URL
                    query_url = f"{reverse('page:guest_order_query')}?phone={data['phone']}"
                    return redirect(query_url)
                else:
                    error_msg = response.get('message', '未知错误') if isinstance(response, dict) else str(response)
                    messages.error(request, f'订单提交失败：{error_msg}')
                    print(f"\n=== 订单提交失败 ===\n错误信息：{error_msg}")
                    return render(request, 'page/guest_order.html', {
                        'form': form,
                        'active_menu': 'page',
                        'page_title': '游客下单',
                        'active_submenu': 'guest_order'
                    })
                    
                return redirect('page:guest_order')
            except Exception as e:
                print(f"\n=== 发生异常 ===\n{str(e)}")
                messages.error(request, f'订单提交失败：{str(e)}')
    else:
        form = GuestOrderForm()
    
    return render(request, 'page/guest_order.html', {
        'form': form,
        'active_menu': 'page',
        'active_submenu': 'guest_order',
        'page_title': '游客下单页面',

    })

def guest_order_query(request):
    """访客订单查询页面"""
    form = GuestOrderQueryForm(request.GET or None)
    orders = []
    
    if form.is_valid():
        phone = form.cleaned_data['phone']
        # 从数据库中查询订单，预加载package和items关联数据
        try:
            orders = Order.objects.select_related('package').prefetch_related('items__sku').filter(
                shipping_phone=phone
            ).order_by('-order_place_time')  # 按下单时间倒序排列
            
            # 打印查询结果，用于调试
            print(f"\n=== 查询结果 ===")
            print(f"电话号码: {phone}")
            print(f"订单数量: {orders.count()}")
            for order in orders:
                print(f"订单号: {order.order_number}, 类型: {order.order_type}, 电话: {order.shipping_phone}")
                print(f"物流单号: {order.package.tracking_no if order.package else '-'}")
            
            if not orders:
                messages.info(request, '未找到相关订单')
        except Exception as e:
            messages.error(request, f'查询失败：{str(e)}')
    
    return render(request, 'page/guest_order_query.html', {
        'form': form,
        'page_title': '游客订单查询',
        'orders': orders,
        'active_menu': 'page',
        'active_submenu': 'guest_order_query'
    })
