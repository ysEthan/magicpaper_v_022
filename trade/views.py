from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Sum, F
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.decorators import method_decorator
from .models import Order, Shop, Cart
from .services import WDTOrderSync
import logging
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import json
from django.core.cache import cache

logger = logging.getLogger(__name__)

class OrderListView(LoginRequiredMixin, ListView):
    """订单列表视图"""
    model = Order
    template_name = 'trade/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20
    ordering = ['-order_place_time']

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'shop',
            'package',
            'package__warehouse',
            'package__service',
            'package__service__carrier'
        ).annotate(
            sku_count=Count('items__sku', distinct=True),
            total_quantity=Sum('items__quantity')
        )
        
        # 添加调试日志
        logger.debug("Querying orders with package info")
        for order in queryset[:5]:  # 只检查前5个订单
            logger.debug(f"Order {order.order_number}:")
            logger.debug(f"- Package: {order.package}")
            if order.package:
                logger.debug(f"- Warehouse: {order.package.warehouse}")
                logger.debug(f"- Service: {order.package.service}")
                if order.package.service:
                    logger.debug(f"- Carrier: {order.package.service.carrier}")

        # 获取过滤参数
        status = self.request.GET.get('status')
        order_type = self.request.GET.get('type')
        shop_id = self.request.GET.get('shop')
        search = self.request.GET.get('search')

        # 应用过滤条件
        if status:
            queryset = queryset.filter(status=status)
        if order_type:
            queryset = queryset.filter(order_type=order_type)
        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)
        if search:
            queryset = queryset.filter(
                order_number__icontains=search
            ) | queryset.filter(
                platform_order_number__icontains=search
            ) | queryset.filter(
                shipping_contact__icontains=search
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['shops'] = Shop.objects.filter(status=1)
        context['order_types'] = Order.ORDER_TYPE_CHOICES
        context['status_choices'] = Order.ORDER_STATUS_CHOICES
        # 获取当前选中的过滤条件
        context['current_status'] = self.request.GET.get('status', '')
        context['current_type'] = self.request.GET.get('type', '')
        context['current_shop'] = self.request.GET.get('shop', '')
        context['search_query'] = self.request.GET.get('search', '')
        # 设置当前菜单
        context['active_menu'] = 'trade_order'
        return context

class OrderDetailView(LoginRequiredMixin, DetailView):
    """订单详情视图"""
    model = Order
    template_name = 'trade/order_detail.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 获取订单商品明细
        context['items'] = self.object.items.all()
        # 设置当前菜单
        context['active_menu'] = 'trade_order'
        return context

class OrderCreateView(LoginRequiredMixin, CreateView):
    """创建订单视图"""
    model = Order
    template_name = 'trade/order_form.html'
    fields = ['order_type', 'shop', 'shipping_contact', 'shipping_phone', 
              'shipping_address', 'postal_code', 'payment_method', 'remark']
    success_url = reverse_lazy('trade:order_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['shops'] = Shop.objects.filter(status=1)
        # 设置当前菜单
        context['active_menu'] = 'trade_order_create'
        return context

    def form_valid(self, form):
        # 设置初始状态为未支付
        form.instance.status = 'unpaid'
        return super().form_valid(form)

class OrderUpdateView(LoginRequiredMixin, UpdateView):
    """更新订单视图"""
    model = Order
    template_name = 'trade/order_form.html'
    fields = ['status', 'shipping_contact', 'shipping_phone', 
              'shipping_address', 'postal_code', 'payment_method', 'remark']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 设置当前菜单
        context['active_menu'] = 'trade_order'
        return context
    
    def get_success_url(self):
        return reverse_lazy('trade:order_detail', kwargs={'pk': self.object.pk})

@login_required
@require_POST
def sync_orders(request):
    """同步旺店通订单"""
    try:
        sync_service = WDTOrderSync()
        result = sync_service.sync_orders()
        
        return JsonResponse({
            'status': 'success',
            'message': f"同步完成。总计: {result['total']}, 新建: {result['created']}, 更新: {result['updated']}, 失败: {result['failed']}",
            'details': result
        })
    except Exception as e:
        logger.error(f"同步订单时出错: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@method_decorator(login_required, name='dispatch')
class SyncOrdersView(View):
    """手动同步订单视图"""
    
    def post(self, request, *args, **kwargs):
        sync_service = WDTOrderSync()
        try:
            result = sync_service.sync_orders()
            messages.success(
                request,
                f"同步完成！总计: {result['total']}, 新建: {result['created']}, 更新: {result['updated']}, 失败: {result['failed']}"
            )
            if result['errors']:
                for error in result['errors']:
                    messages.warning(request, error)
        except Exception as e:
            messages.error(request, f"同步失败: {str(e)}")
            
        return redirect('order_list')

@login_required
def report(request):
    # 使用缓存，缓存时间设为5分钟
    cache_key = 'trade_report_data'
    report_data = cache.get(cache_key)
    
    if report_data is None:
        today = timezone.now()
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 订单统计 - 使用单次查询
        orders = Order.objects.all()
        total_orders = orders.count()
        pending_orders = orders.filter(status__in=['pending', 'picking']).count()
        today_orders = orders.filter(order_place_time__date=today.date()).count()
        month_sales = orders.filter(
            order_place_time__gte=month_start
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # 趋势数据 - 优化查询，使用聚合函数
        dates = [(today - timedelta(days=i)).date() for i in range(20, -1, -1)]
        
        trend_data = list(Order.objects.filter(
            order_place_time__date__gte=dates[0]
        ).values('order_place_time__date').annotate(
            count=Count('id')
        ).order_by('order_place_time__date'))
        
        order_trend = [0] * 21
        for item in trend_data:
            index = dates.index(item['order_place_time__date'])
            order_trend[index] = item['count']
        
        # 计算百分比
        pending_orders_percentage = round((pending_orders / total_orders * 100) if total_orders > 0 else 0, 1)
        
        # 计算环比（与上月相比的增长率）
        last_month_start = month_start.replace(month=month_start.month-1 if month_start.month > 1 else 12)
        last_month_amount = orders.filter(
            order_place_time__gte=last_month_start,
            order_place_time__lt=month_start
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        month_over_month = round(
            ((month_sales - last_month_amount) / last_month_amount * 100) if last_month_amount > 0 else 0,
            1
        )
        
        # 按订单类型统计
        order_types = []
        for type_code, type_name in Order.ORDER_TYPE_CHOICES:
            type_orders = orders.filter(order_type=type_code)
            count = type_orders.count()
            if count > 0:  # 只添加有订单的类型
                amount = type_orders.aggregate(total=Sum('total_amount'))['total'] or 0
                percentage = round((count / total_orders * 100) if total_orders > 0 else 0, 1)
                
                order_types.append({
                    'name': type_name,
                    'count': count,
                    'amount': amount,
                    'percentage': percentage
                })
        
        report_data = {
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'pending_orders_percentage': pending_orders_percentage,
            'new_orders_today': today_orders,
            'month_amount': month_sales,
            'month_over_month': month_over_month,
            'order_types': order_types,
            'trend_dates': json.dumps([d.strftime('%Y-%m-%d') for d in dates]),
            'trend_counts': json.dumps(order_trend),
            'current_month': today.strftime('%Y年%m月'),
            'active_menu': 'trade',
            'active_submenu': 'report'
        }
        
        # 设置缓存，5分钟过期
        cache.set(cache_key, report_data, 300)
    
    return render(request, 'trade/report.html', report_data)
