from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Sum, F, Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.decorators import method_decorator
from .models import Order, Shop, Cart
from .services import WDTOrderSync
import logging
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
import json
from django.core.cache import cache
from django.db import models
import xlsxwriter
from io import BytesIO
from django.conf import settings

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
            'shop'
        ).prefetch_related(
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
            try:
                logger.debug(f"- Package: {order.package}")
                if order.package:
                    logger.debug(f"- Warehouse: {order.package.warehouse}")
                    logger.debug(f"- Service: {order.package.service}")
                    if order.package.service:
                        logger.debug(f"- Carrier: {order.package.service.carrier}")
            except Order.package.RelatedObjectDoesNotExist:
                logger.debug("- No package associated")

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
        context['active_menu'] = 'trade'
        context['active_submenu'] = 'order'
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
        context['active_menu'] = 'trade'
        context['active_submenu'] = 'order'
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
        context['active_menu'] = 'trade'
        context['active_submenu'] = 'order'
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
        context['active_menu'] = 'trade'
        context['active_submenu'] = 'order'
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
        ).annotate(
            usd_amount=F('total_amount') * F('exchange_rate_to_usd')
        ).aggregate(
            total=Sum('usd_amount')
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
        ).annotate(
            usd_amount=F('total_amount') * F('exchange_rate_to_usd')
        ).aggregate(
            total=Sum('usd_amount')
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
                amount = type_orders.annotate(
                    usd_amount=F('total_amount') * F('exchange_rate_to_usd')
                ).aggregate(
                    total=Sum('usd_amount')
                )['total'] or 0
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

class SalesDetailView(LoginRequiredMixin, ListView):
    """销售明细视图"""
    model = Cart
    template_name = 'trade/sales_detail.html'
    context_object_name = 'sales'
    paginate_by = 20

    def get_queryset(self):
        # 基础查询
        queryset = Cart.objects.select_related(
            'order', 'sku', 'order__shop', 'sku__spu'
        ).filter(
            ~Q(order__status='cancelled')  # 排除已取消的订单
        )

        # 过滤条件
        shop_id = self.request.GET.get('shop')
        product_type = self.request.GET.get('product_type')
        days = self.request.GET.get('days')

        if shop_id:
            queryset = queryset.filter(order__shop_id=shop_id)
        if product_type:
            queryset = queryset.filter(sku__spu__product_type=product_type)
        if days:
            days = int(days)
            start_date = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(order__created_at__gte=start_date)

        # 按SKU聚合数据
        queryset = queryset.values(
            'sku__sku_code',
            'sku__sku_name',
            'sku__spu__product_type',  # 通过SPU获取商品类型
            'sku__img_url',  # 添加商品图片URL
        ).annotate(
            total_quantity=models.Sum('quantity'),
            total_amount=models.Sum('total_price'),
            avg_price=models.Avg('unit_price'),
            order_count=models.Count('order', distinct=True),
            shop_count=models.Count('order__shop', distinct=True),
            last_sold=models.Max('order__created_at')
        ).order_by('-total_amount')

        # 处理图片URL
        for item in queryset:
            if item['sku__img_url']:
                # 如果是相对路径，添加MEDIA_URL前缀
                if not item['sku__img_url'].startswith(('http://', 'https://')):
                    item['sku__img_url'] = settings.MEDIA_URL + item['sku__img_url']

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 获取所有店铺
        context['shops'] = Shop.objects.filter(status=1)
        
        # 获取商品类型选项
        from gallery.models import SPU
        context['product_types'] = SPU.PRODUCT_TYPE_CHOICES
        
        # 时间范围选项
        context['date_ranges'] = [
            {'days': 7, 'name': '7天'},
            {'days': 14, 'name': '14天'},
            {'days': 30, 'name': '30天'},
            {'days': 90, 'name': '3个月'},
        ]
        
        # 计算统计数据
        sales_data = self.get_queryset()
        context['total_quantity'] = sum(item['total_quantity'] for item in sales_data)
        context['total_amount'] = sum(item['total_amount'] for item in sales_data)
        context['sku_count'] = len(sales_data)  # SKU种类数
        
        # 计算订单总数
        base_queryset = Cart.objects.filter(~Q(order__status='cancelled'))
        if self.request.GET.get('shop'):
            base_queryset = base_queryset.filter(order__shop_id=self.request.GET.get('shop'))
        if self.request.GET.get('product_type'):
            base_queryset = base_queryset.filter(sku__spu__product_type=self.request.GET.get('product_type'))
        if self.request.GET.get('days'):
            days = int(self.request.GET.get('days'))
            start_date = timezone.now() - timedelta(days=days)
            base_queryset = base_queryset.filter(order__created_at__gte=start_date)
        context['total_orders'] = base_queryset.values('order').distinct().count()
        
        # 保存筛选条件
        context['filters'] = {
            'shop': self.request.GET.get('shop', ''),
            'product_type': self.request.GET.get('product_type', ''),
            'days': self.request.GET.get('days', ''),
        }
        
        # 设置当前菜单
        context['active_menu'] = 'trade'
        context['active_submenu'] = 'sales_detail'
        
        return context

@login_required
def export_sales_detail(request):
    """导出销售明细Excel"""
    # 创建一个内存中的Excel文件
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('销售明细')

    # 设置表头样式
    header_format = workbook.add_format({
        'bold': True,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#F4F6F9',
        'border': 1
    })

    # 设置单元格样式
    cell_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })

    # 设置数字格式
    number_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'num_format': '#,##0.00'
    })

    # 设置图片列宽和行高
    worksheet.set_column('A:A', 15)  # 图片列宽
    worksheet.set_default_row(45)    # 默认行高

    # 写入表头
    headers = [
        '商品图片', 'SKU编码', '商品名称', '商品类型', '销售数量', 
        '销售金额', '平均单价', '订单数', '店铺数', '最近销售'
    ]
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)

    # 获取筛选条件
    shop_id = request.GET.get('shop')
    product_type = request.GET.get('product_type')
    days = request.GET.get('days')

    # 构建查询
    queryset = Cart.objects.select_related(
        'order', 'sku', 'order__shop', 'sku__spu'
    ).filter(
        ~Q(order__status='cancelled')
    )

    if shop_id:
        queryset = queryset.filter(order__shop_id=shop_id)
    if product_type:
        queryset = queryset.filter(sku__spu__product_type=product_type)
    if days:
        days = int(days)
        start_date = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(order__created_at__gte=start_date)

    # 按SKU聚合数据
    sales_data = queryset.values(
        'sku__sku_code',
        'sku__sku_name',
        'sku__spu__product_type',
        'sku__img_url',
    ).annotate(
        total_quantity=models.Sum('quantity'),
        total_amount=models.Sum('total_price'),
        avg_price=models.Avg('unit_price'),
        order_count=models.Count('order', distinct=True),
        shop_count=models.Count('order__shop', distinct=True),
        last_sold=models.Max('order__created_at')
    ).order_by('-total_amount')

    # 获取商品类型选项字典
    from gallery.models import SPU
    product_types_dict = dict(SPU.PRODUCT_TYPE_CHOICES)

    # 写入数据
    import os
    import requests
    from urllib.parse import urlparse
    from django.conf import settings

    for row, item in enumerate(sales_data, start=1):
        # 处理图片
        if item['sku__img_url']:
            img_url = item['sku__img_url']
            if not img_url.startswith(('http://', 'https://')):
                img_url = settings.MEDIA_URL.rstrip('/') + '/' + img_url.lstrip('/')
                # 如果MEDIA_URL是相对路径，添加域名
                if not img_url.startswith(('http://', 'https://')):
                    img_url = request.build_absolute_uri(img_url)
            
            try:
                # 下载图片
                response = requests.get(img_url)
                if response.status_code == 200:
                    # 插入图片到Excel
                    worksheet.insert_image(row, 0, 'image.png', {
                        'image_data': BytesIO(response.content),
                        'x_scale': 0.5,
                        'y_scale': 0.5,
                        'positioning': 1
                    })
            except Exception as e:
                logger.error(f"下载图片失败: {str(e)}")

        # 写入其他数据
        worksheet.write(row, 1, item['sku__sku_code'], cell_format)
        worksheet.write(row, 2, item['sku__sku_name'], cell_format)
        worksheet.write(row, 3, product_types_dict.get(item['sku__spu__product_type'], '-'), cell_format)
        worksheet.write(row, 4, item['total_quantity'], cell_format)
        worksheet.write(row, 5, item['total_amount'], number_format)
        worksheet.write(row, 6, item['avg_price'], number_format)
        worksheet.write(row, 7, item['order_count'], cell_format)
        worksheet.write(row, 8, item['shop_count'], cell_format)
        worksheet.write(row, 9, item['last_sold'].strftime('%Y-%m-%d %H:%M'), cell_format)

    workbook.close()
    output.seek(0)

    # 生成下载文件名
    filename = f'销售明细_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
