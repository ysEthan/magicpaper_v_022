from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from django.db import transaction
from .models import DemandRequest, DemandTracking, ProductionOrder
from .forms import DemandRequestForm, DemandTrackingForm, ProductionOrderForm, ProductionUpdateForm
import uuid

@login_required
def demand_list(request):
    """需求申请列表页面"""
    search_term = request.GET.get('search', '')
    status = request.GET.get('status', '')
    request_type = request.GET.get('type', '')
    
    demands = DemandRequest.objects.all()
    
    if search_term:
        demands = demands.filter(
            Q(request_number__icontains=search_term) |
            Q(title__icontains=search_term) |
            Q(description__icontains=search_term)
        )
    
    if status:
        demands = demands.filter(status=status)
        
    if request_type:
        demands = demands.filter(request_type=request_type)
    
    paginator = Paginator(demands, 20)
    page = request.GET.get('page')
    demands = paginator.get_page(page)
    
    context = {
        'demands': demands,
        'search_term': search_term,
        'status': status,
        'request_type': request_type,
        'status_choices': DemandRequest.STATUS_CHOICES,
        'type_choices': DemandRequest.REQUEST_TYPE_CHOICES,
        'active_menu': 'manufacturing',
        'active_submenu': 'demand'
    }
    
    return render(request, 'manufacturing/demand/list.html', context)

@login_required
def demand_create(request):
    """创建需求申请"""
    if request.method == 'POST':
        form = DemandRequestForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                demand = form.save(commit=False)
                demand.creator = request.user
                # 生成需求编号：DR + 年月日 + 4位随机数
                demand.request_number = f"DR{timezone.now().strftime('%Y%m%d')}{str(uuid.uuid4().int)[:4]}"
                demand.save()
            return redirect('manufacturing:demand_list')
    else:
        form = DemandRequestForm()
    
    context = {
        'form': form,
        'title': '新建需求',
        'page_title': '新建供应链需求',
        'active_menu': 'manufacturing',
        'active_submenu': 'demand'
    }
    return render(request, 'manufacturing/demand/form.html', context)

@login_required
def demand_detail(request, pk):
    """需求申请详情页面"""
    demand = get_object_or_404(DemandRequest, pk=pk)
    tracking_records = demand.tracking_records.all()
    production_orders = demand.production_orders.all()
    
    tracking_form = DemandTrackingForm()
    
    context = {
        'demand': demand,
        'page_title': '需求详情',
        'tracking_records': tracking_records,
        'production_orders': production_orders,
        'tracking_form': tracking_form,
        'active_menu': 'manufacturing',
        'active_submenu': 'demand'
    }
    
    return render(request, 'manufacturing/demand/detail.html', context)

@login_required
def demand_edit(request, pk):
    """编辑需求申请"""
    demand = get_object_or_404(DemandRequest, pk=pk)
    
    # 只有需求创建者和跟单员可以编辑
    if request.user != demand.requester and request.user != demand.handler:
        messages.error(request, '您没有权限编辑此需求！')
        return redirect('manufacturing:demand_detail', pk=pk)
    
    if request.method == 'POST':
        form = DemandRequestForm(request.POST, instance=demand)
        if form.is_valid():
            form.save()
            return redirect('manufacturing:demand_list')
    else:
        form = DemandRequestForm(instance=demand)
    
    context = {
        'form': form,
        'title': '编辑需求',
        'page_title': '编辑需求',
        'active_menu': 'manufacturing',
        'active_submenu': 'demand'
    }
    return render(request, 'manufacturing/demand/form.html', context)

@login_required
def demand_delete(request, pk):
    """删除需求申请"""
    demand = get_object_or_404(DemandRequest, pk=pk)
    
    # 只有需求创建者可以删除，且只能删除草稿状态的需求
    if request.user != demand.requester or demand.status != 'draft':
        messages.error(request, '您没有权限删除此需求！')
        return redirect('manufacturing:demand_detail', pk=pk)
    
    if request.method == 'POST':
        demand.delete()
        messages.success(request, '需求申请已删除！')
        return redirect('manufacturing:demand_list')
    
    return render(request, 'manufacturing/demand/delete.html', {
        'demand': demand,
        'active_menu': 'manufacturing',
        'active_submenu': 'demand'
    })

@login_required
def tracking_create(request, pk):
    """添加需求跟进记录"""
    demand = get_object_or_404(DemandRequest, pk=pk)
    
    if request.method == 'POST':
        form = DemandTrackingForm(request.POST)
        if form.is_valid():
            tracking = form.save(commit=False)
            tracking.demand = demand
            tracking.operator = request.user
            tracking.save()
            
            # 如果是状态变更，同时更新需求状态
            if tracking.tracking_type == 'status_change':
                old_status = demand.status
                new_status = request.POST.get('new_status')
                if new_status and new_status != old_status:
                    demand.status = new_status
                    demand.save()
            
            messages.success(request, '跟进记录已添加！')
        else:
            messages.error(request, '表单验证失败，请检查输入！')
    
    return redirect('manufacturing:demand_detail', pk=pk)

@login_required
def production_list(request):
    """生产工单列表页面"""
    search_term = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    orders = ProductionOrder.objects.select_related('sku', 'demand')
    
    if search_term:
        orders = orders.filter(
            Q(order_number__icontains=search_term) |
            Q(sku__sku_code__icontains=search_term) |
            Q(demand__request_number__icontains=search_term)
        )
    
    if status:
        orders = orders.filter(status=status)
    
    paginator = Paginator(orders, 20)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    context = {
        'orders': orders,
        'search_term': search_term,
        'status': status,
        'status_choices': ProductionOrder.ORDER_STATUS_CHOICES,
        'active_menu': 'manufacturing',
        'active_submenu': 'production'
    }
    
    return render(request, 'manufacturing/production/list.html', context)

@login_required
def production_create(request, demand_pk=None):
    """创建生产工单"""
    demand = None
    if demand_pk:
        demand = get_object_or_404(DemandRequest, pk=demand_pk)
        # 检查需求状态是否允许创建工单
        if demand.status not in ['submitted', 'processing']:
            messages.error(request, '当前需求状态不允许创建工单！')
            return redirect('manufacturing:demand_detail', pk=demand_pk)
    
    if request.method == 'POST':
        form = ProductionOrderForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                if demand:
                    order.demand = demand
                # 生成工单编号：PO + 年月日 + 4位随机数
                order.order_number = f"PO{timezone.now().strftime('%Y%m%d')}{str(uuid.uuid4().int)[:4]}"
                order.save()
                
                # 如果关联了需求，更新需求状态
                if demand and demand.status == 'submitted':
                    demand.status = 'processing'
                    demand.save()
                    DemandTracking.objects.create(
                        demand=demand,
                        tracking_type='status_change',
                        content='已创建生产工单，需求状态更新为处理中',
                        operator=request.user
                    )
            
            messages.success(request, '生产工单创建成功！')
            return redirect('manufacturing:production_detail', pk=order.pk)
    else:
        form = ProductionOrderForm()
    
    return render(request, 'manufacturing/production/form.html', {
        'form': form,
        'demand': demand,
        'title': '创建生产工单',
        'active_menu': 'manufacturing',
        'active_submenu': 'production'
    })

@login_required
def production_detail(request, pk):
    """生产工单详情页面"""
    order = get_object_or_404(ProductionOrder.objects.select_related('sku', 'demand'), pk=pk)
    
    if request.method == 'POST':
        form = ProductionUpdateForm(request.POST, instance=order)
        if form.is_valid():
            with transaction.atomic():
                order = form.save()
                
                # 如果工单完成，同时更新需求状态
                if order.status == 'completed' and order.demand:
                    demand = order.demand
                    # 检查是否所有相关工单都已完成
                    all_completed = all(po.status == 'completed' 
                                     for po in demand.production_orders.all())
                    if all_completed:
                        demand.status = 'completed'
                        demand.actual_completion_date = timezone.now().date()
                        demand.save()
                        DemandTracking.objects.create(
                            demand=demand,
                            tracking_type='status_change',
                            content='所有生产工单已完成，需求状态更新为已完成',
                            operator=request.user
                        )
            
            messages.success(request, '生产工单更新成功！')
            return redirect('manufacturing:production_detail', pk=pk)
    else:
        form = ProductionUpdateForm(instance=order)
    
    context = {
        'order': order,
        'form': form,
        'active_menu': 'manufacturing',
        'active_submenu': 'production'
    }
    
    return render(request, 'manufacturing/production/detail.html', context)

@login_required
def production_edit(request, pk):
    """编辑生产工单"""
    order = get_object_or_404(ProductionOrder, pk=pk)
    
    # 只能编辑未开始生产的工单
    if order.status != 'pending':
        messages.error(request, '只能编辑未开始生产的工单！')
        return redirect('manufacturing:production_detail', pk=pk)
    
    if request.method == 'POST':
        form = ProductionOrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, '生产工单更新成功！')
            return redirect('manufacturing:production_detail', pk=pk)
    else:
        form = ProductionOrderForm(instance=order)
    
    return render(request, 'manufacturing/production/form.html', {
        'form': form,
        'order': order,
        'title': '编辑生产工单',
        'active_menu': 'manufacturing',
        'active_submenu': 'production'
    })

@login_required
def production_delete(request, pk):
    """删除生产工单"""
    order = get_object_or_404(ProductionOrder, pk=pk)
    
    # 只能删除未开始生产的工单
    if order.status != 'pending':
        messages.error(request, '只能删除未开始生产的工单！')
        return redirect('manufacturing:production_detail', pk=pk)
    
    if request.method == 'POST':
        demand = order.demand
        with transaction.atomic():
            order.delete()
            # 如果关联了需求，且需求没有其他工单，将需求状态改回已提交
            if demand and not demand.production_orders.exists():
                demand.status = 'submitted'
                demand.save()
                DemandTracking.objects.create(
                    demand=demand,
                    tracking_type='status_change',
                    content='生产工单已删除，需求状态更新为已提交',
                    operator=request.user
                )
        
        messages.success(request, '生产工单已删除！')
        return redirect('manufacturing:production_list')
    
    return render(request, 'manufacturing/production/delete.html', {
        'order': order,
        'active_menu': 'manufacturing',
        'active_submenu': 'production'
    })

@login_required
def report(request):
    """生产管理报表页面"""
    today = timezone.now()
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 需求统计
    total_demands = DemandRequest.objects.count()
    active_demands = DemandRequest.objects.filter(
        status__in=['submitted', 'processing']
    ).count()
    completed_demands = DemandRequest.objects.filter(
        status='completed',
        actual_completion_date__gte=month_start
    ).count()
    
    # 工单统计
    total_orders = ProductionOrder.objects.count()
    pending_orders = ProductionOrder.objects.filter(status='pending').count()
    in_progress_orders = ProductionOrder.objects.filter(status='in_progress').count()
    completed_orders = ProductionOrder.objects.filter(
        status='completed',
        actual_end_date__gte=month_start
    ).count()
    
    # 计算平均完成率和不良品率
    production_stats = ProductionOrder.objects.filter(
        status='completed',
        actual_end_date__gte=month_start
    ).aggregate(
        total_quantity=Sum('quantity'),
        total_completed=Sum('completed_quantity'),
        total_defective=Sum('defective_quantity')
    )
    
    if production_stats['total_quantity']:
        completion_rate = round(
            production_stats['total_completed'] / production_stats['total_quantity'] * 100,
            2
        )
        defect_rate = round(
            production_stats['total_defective'] / (production_stats['total_completed'] + production_stats['total_defective']) * 100,
            2
        ) if production_stats['total_completed'] else 0
    else:
        completion_rate = defect_rate = 0
    
    # 按需求类型统计
    demand_types = DemandRequest.objects.filter(
        created_at__gte=month_start
    ).values('request_type').annotate(
        count=Count('id')
    ).order_by('request_type')
    
    context = {
        'total_demands': total_demands,
        'active_demands': active_demands,
        'completed_demands': completed_demands,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'in_progress_orders': in_progress_orders,
        'completed_orders': completed_orders,
        'completion_rate': completion_rate,
        'defect_rate': defect_rate,
        'demand_types': demand_types,
        'current_month': today.strftime('%Y年%m月'),
        'active_menu': 'manufacturing',
        'active_submenu': 'report'
    }
    
    return render(request, 'manufacturing/report.html', context)
