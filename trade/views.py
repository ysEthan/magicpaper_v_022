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

logger = logging.getLogger(__name__)

class OrderListView(LoginRequiredMixin, ListView):
    """订单列表视图"""
    model = Order
    template_name = 'trade/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20
    ordering = ['-order_place_time']

    def get_queryset(self):
        queryset = super().get_queryset()
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
