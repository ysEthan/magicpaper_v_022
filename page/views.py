from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, F, Q
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
import json
from gallery.models import SKU
from trade.models import Order
from procurement.models import PurchaseOrder
from logistics.models import Package

@login_required
def index_view(request):
    # 使用缓存，缓存时间设为5分钟
    cache_key = 'dashboard_data'
    dashboard_data = cache.get(cache_key)
    
    if dashboard_data is None:
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
        ).aggregate(
            total=Sum('total_amount')
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
        pending_packages = packages.filter(pkg_status_code__in=['0', '1', '2']).count()
        processing_packages = packages.filter(pkg_status_code='1').count()
        today_packages = packages.filter(created_at__date=today.date()).count()
        week_packages = packages.filter(created_at__gte=week_start).count()
        month_shipping_cost = packages.filter(
            created_at__gte=month_start
        ).aggregate(
            total=Sum('carrier_cost')
        )['total'] or 0
        
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
            
            'pending_packages': pending_packages,
            'processing_packages': processing_packages,
            'today_packages': today_packages,
            'week_packages': week_packages,
            'month_shipping_cost': month_shipping_cost,
            'logistics_trend': json.dumps(logistics_trend_data),
            
            'current_month': today.strftime('%Y年%m月')
        }
        
        # 设置缓存，5分钟过期
        cache.set(cache_key, dashboard_data, 300)
    
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
