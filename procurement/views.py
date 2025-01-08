from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from .models import Supplier, PurchaseOrder, PurchaseOrderItem
from .forms import SupplierForm, PurchaseOrderForm, PurchaseOrderItemFormSet
from .sync import sync_all_purchase
from django.db.models import Count, Sum, F, Q
from django.utils import timezone


class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = 'procurement/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_menu'] = 'procurement'
        context['active_submenu'] = 'supplier'
        return context


class SupplierDetailView(LoginRequiredMixin, DetailView):
    model = Supplier
    template_name = 'procurement/supplier_detail.html'
    context_object_name = 'supplier'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_menu'] = 'procurement'
        context['active_submenu'] = 'supplier'
        return context


class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'procurement/supplier_form.html'
    success_url = reverse_lazy('procurement:supplier_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_menu'] = 'procurement'
        context['active_submenu'] = 'supplier'
        return context

    def form_valid(self, form):
        messages.success(self.request, '供应商创建成功！')
        return super().form_valid(form)


class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'procurement/supplier_form.html'
    success_url = reverse_lazy('procurement:supplier_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_menu'] = 'procurement'
        context['active_submenu'] = 'supplier'
        return context

    def form_valid(self, form):
        messages.success(self.request, '供应商更新成功！')
        return super().form_valid(form)


class PurchaseOrderListView(LoginRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = 'procurement/purchase_order_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        status_filter = self.request.GET.get('status', '')
        
        if search_query:
            queryset = queryset.filter(order_number__icontains=search_query)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_menu'] = 'procurement'
        context['active_submenu'] = 'order'
        return context


class PurchaseOrderDetailView(LoginRequiredMixin, DetailView):
    model = PurchaseOrder
    template_name = 'procurement/purchase_order_detail.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.purchaseorderitem_set.all()
        context['active_menu'] = 'procurement'
        context['active_submenu'] = 'order'
        return context


class PurchaseOrderCreateView(LoginRequiredMixin, CreateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'procurement/purchase_order_form.html'
    success_url = reverse_lazy('procurement:purchase_order_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['items_formset'] = PurchaseOrderItemFormSet(self.request.POST)
        else:
            context['items_formset'] = PurchaseOrderItemFormSet()
        context['active_menu'] = 'procurement'
        context['active_submenu'] = 'order'
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context['items_formset']
        if items_formset.is_valid():
            self.object = form.save()
            items_formset.instance = self.object
            items_formset.save()
            messages.success(self.request, '采购订单创建成功！')
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))


class PurchaseOrderUpdateView(LoginRequiredMixin, UpdateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'procurement/purchase_order_form.html'
    success_url = reverse_lazy('procurement:purchase_order_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['items_formset'] = PurchaseOrderItemFormSet(
                self.request.POST, instance=self.object)
        else:
            context['items_formset'] = PurchaseOrderItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context['items_formset']
        if items_formset.is_valid():
            self.object = form.save()
            items_formset.instance = self.object
            items_formset.save()
            messages.success(self.request, '采购订单更新成功！')
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))


@login_required
def sync_purchase_orders(request):
    """同步采购订单数据"""
    try:
        success, message = sync_all_purchase()
        if success:
            messages.success(request, message)
        else:
            messages.error(request, f'同步失败：{message}')
    except Exception as e:
        messages.error(request, f'同步过程中发生错误：{str(e)}')
    
    return redirect('procurement:purchase_order_list')


@login_required
def report(request):
    """采购报表页面"""
    today = timezone.now()
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 总体统计
    total_orders = PurchaseOrder.objects.count()
    new_orders_today = PurchaseOrder.objects.filter(created_at__date=today.date()).count()
    
    # 进行中的采购单（未完成或未关闭的）
    active_orders = PurchaseOrder.objects.filter(
        status__in=['draft', 'submitted', 'approved', 'processing']
    ).count()
    
    # 计算本月采购金额
    month_amount = PurchaseOrder.objects.filter(
        created_at__gte=month_start
    ).aggregate(
        total=Sum(F('purchaseorderitem__quantity') * F('purchaseorderitem__unit_price'))
    )['total'] or 0
    
    # 计算百分比
    active_orders_percentage = round((active_orders / total_orders * 100) if total_orders > 0 else 0, 1)
    
    # 计算环比（与上月相比的增长率）
    last_month_start = month_start.replace(month=month_start.month-1 if month_start.month > 1 else 12)
    last_month_amount = PurchaseOrder.objects.filter(
        created_at__gte=last_month_start,
        created_at__lt=month_start
    ).aggregate(
        total=Sum(F('purchaseorderitem__quantity') * F('purchaseorderitem__unit_price'))
    )['total'] or 0
    month_over_month = round(
        ((month_amount - last_month_amount) / last_month_amount * 100) if last_month_amount > 0 else 0,
        1
    )
    
    # 按供应商统计
    suppliers = Supplier.objects.annotate(
        total_orders=Count('purchaseorder'),
        active_orders=Count(
            'purchaseorder',
            filter=Q(purchaseorder__status__in=['draft', 'submitted', 'approved', 'processing'])
        ),
        month_amount=Sum(
            F('purchaseorder__purchaseorderitem__quantity') * F('purchaseorder__purchaseorderitem__unit_price'),
            filter=Q(purchaseorder__created_at__gte=month_start)
        )
    )
    
    context = {
        'total_orders': total_orders,
        'new_orders_today': new_orders_today,
        'active_orders': active_orders,
        'active_orders_percentage': active_orders_percentage,
        'month_amount': month_amount,
        'month_over_month': month_over_month,
        'suppliers': suppliers,
        'current_month': today.strftime('%Y年%m月'),
        'active_menu': 'procurement',
        'active_submenu': 'report'
    }
    
    return render(request, 'procurement/report.html', context)
