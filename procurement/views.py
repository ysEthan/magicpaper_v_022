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


class SupplierDetailView(LoginRequiredMixin, DetailView):
    model = Supplier
    template_name = 'procurement/supplier_detail.html'
    context_object_name = 'supplier'


class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'procurement/supplier_form.html'
    success_url = reverse_lazy('procurement:supplier_list')

    def form_valid(self, form):
        messages.success(self.request, '供应商创建成功！')
        return super().form_valid(form)


class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'procurement/supplier_form.html'
    success_url = reverse_lazy('procurement:supplier_list')

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


class PurchaseOrderDetailView(LoginRequiredMixin, DetailView):
    model = PurchaseOrder
    template_name = 'procurement/purchase_order_detail.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.purchaseorderitem_set.all()
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
