from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Sum, F
from django.db import models
from django.utils import timezone
from .models import Warehouse, Inventory, StockIn, StockOut
from .forms import WarehouseForm, StockInForm, StockOutForm
from django.http import JsonResponse
from .services import WDTStockInSyncService

@login_required
def available_inventory_api(request):
    """获取指定仓库和SKU的可用库存批次"""
    warehouse_id = request.GET.get('warehouse')
    sku_id = request.GET.get('sku')
    
    if not warehouse_id or not sku_id:
        return JsonResponse({'error': '缺少必要参数'}, status=400)
    
    # 获取可用库存批次
    inventories = Inventory.objects.filter(
        warehouse_id=warehouse_id,
        sku_id=sku_id,
        quantity__gt=0  # 只返回有库存的批次
    ).values('id', 'batch_code', 'quantity')
    
    return JsonResponse(list(inventories), safe=False)

@login_required
def warehouse_list(request):
    """仓库列表"""
    warehouses = Warehouse.objects.all()
    
    # 搜索功能
    search_query = request.GET.get('search', '')
    if search_query:
        warehouses = warehouses.filter(
            Q(warehouse_code__icontains=search_query) |
            Q(warehouse_name__icontains=search_query)
        )
    
    # 分页
    paginator = Paginator(warehouses, 10)
    page = request.GET.get('page')
    warehouses = paginator.get_page(page)
    
    context = {
        'warehouses': warehouses,
        'search_query': search_query,
        'active_menu': 'storage_warehouse'
    }
    return render(request, 'storage/warehouse/list.html', context)

@login_required
def warehouse_detail(request, pk):
    """仓库详情"""
    warehouse = get_object_or_404(Warehouse, pk=pk)
    
    # 获取仓库的库存统计
    inventories = warehouse.inventories.all()
    total_items = inventories.count()
    
    # 获取最近的出入库记录
    recent_stock_ins = warehouse.stock_ins.all()[:5]
    recent_stock_outs = warehouse.stock_outs.all()[:5]
    
    context = {
        'warehouse': warehouse,
        'total_items': total_items,
        'recent_stock_ins': recent_stock_ins,
        'recent_stock_outs': recent_stock_outs,
        'inventories': inventories,
        'active_menu': 'storage_warehouse'
    }
    return render(request, 'storage/warehouse/detail.html', context)

@login_required
def warehouse_create(request):
    """创建仓库"""
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            warehouse = form.save()
            messages.success(request, '仓库创建成功！')
            return redirect('warehouse_detail', pk=warehouse.pk)
    else:
        form = WarehouseForm()
    
    return render(request, 'storage/warehouse/form.html', {'form': form, 'title': '创建仓库', 'active_menu': 'storage_warehouse'})

@login_required
def warehouse_edit(request, pk):
    """编辑仓库"""
    warehouse = get_object_or_404(Warehouse, pk=pk)
    if request.method == 'POST':
        form = WarehouseForm(request.POST, instance=warehouse)
        if form.is_valid():
            warehouse = form.save()
            messages.success(request, '仓库信息更新成功！')
            return redirect('warehouse_detail', pk=warehouse.pk)
    else:
        form = WarehouseForm(instance=warehouse)
    
    return render(request, 'storage/warehouse/form.html', {'form': form, 'title': '编辑仓库', 'active_menu': 'storage_warehouse'})

@login_required
def inventory_list(request):
    """库存列表"""
    inventories = Inventory.objects.all()
    
    # 过滤条件
    warehouse_id = request.GET.get('warehouse', 'None')
    sku_code = request.GET.get('sku_code', '')
    batch_code = request.GET.get('batch_code', '')
    
    if warehouse_id and warehouse_id != 'None':
        inventories = inventories.filter(warehouse_id=warehouse_id)
    if sku_code and sku_code != 'None':
        inventories = inventories.filter(sku__sku_code__icontains=sku_code)
    if batch_code and batch_code != 'None':
        inventories = inventories.filter(batch_code__icontains=batch_code)
    
    # 分页
    paginator = Paginator(inventories, 10)
    page = request.GET.get('page')
    inventories = paginator.get_page(page)
    
    # 获取所有仓库，用于过滤
    warehouses = Warehouse.objects.all()
    
    context = {
        'inventories': inventories,
        'warehouses': warehouses,
        'warehouse_id': warehouse_id,
        'sku_code': '' if sku_code == 'None' else sku_code,
        'batch_code': '' if batch_code == 'None' else batch_code
    }
    return render(request, 'storage/inventory/list.html', context)

@login_required
def stock_in_list(request):
    """入库记录列表"""
    stock_ins = StockIn.objects.all().order_by('-stock_in_time')
    warehouses = Warehouse.objects.all()
    
    # 处理筛选
    warehouse_id = request.GET.get('warehouse', '')
    stock_in_code = request.GET.get('stock_in_code', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if warehouse_id and warehouse_id != 'None':
        stock_ins = stock_ins.filter(warehouse_id=warehouse_id)
    if stock_in_code and stock_in_code != 'None':
        stock_ins = stock_ins.filter(stock_in_code__icontains=stock_in_code)
    if date_from:
        stock_ins = stock_ins.filter(stock_in_time__date__gte=date_from)
    if date_to:
        stock_ins = stock_ins.filter(stock_in_time__date__lte=date_to)
    
    # 分页
    paginator = Paginator(stock_ins, 10)  # 每页显示10条记录
    page = request.GET.get('page')
    try:
        stock_ins = paginator.get_page(page)
    except PageNotAnInteger:
        stock_ins = paginator.get_page(1)
    except EmptyPage:
        stock_ins = paginator.get_page(paginator.num_pages)
    
    context = {
        'stock_ins': stock_ins,
        'warehouses': warehouses,
        'warehouse_id': warehouse_id if warehouse_id != 'None' else '',
        'stock_in_code': stock_in_code if stock_in_code != 'None' else '',
        'date_from': date_from,
        'date_to': date_to,
        'active_menu': 'storage_stock_in'
    }
    return render(request, 'storage/stock_in/list.html', context)

@login_required
def stock_in_create(request):
    """创建入库单"""
    if request.method == 'POST':
        form = StockInForm(request.POST)
        if form.is_valid():
            stock_in = form.save(commit=False)
            stock_in.operator = request.user
            
            # 创建库存记录
            inventory = Inventory.objects.create(
                warehouse=stock_in.warehouse,
                sku=stock_in.sku,
                batch_code=stock_in.stock_in_code,  # 使用入库单号作为批次号
                quantity=stock_in.quantity
            )
            stock_in.inventory = inventory
            stock_in.save()
            
            messages.success(request, '入库单创建成功！')
            return redirect('stock_in_list')
    else:
        form = StockInForm()
    
    return render(request, 'storage/stock_in/form.html', {'form': form, 'title': '创建入库单', 'active_menu': 'storage_stock_in'})

@login_required
def stock_out_list(request):
    """出库记录列表"""
    stock_outs = StockOut.objects.all().order_by('-stock_out_time')
    warehouses = Warehouse.objects.all()
    
    # 处理筛选
    warehouse_id = request.GET.get('warehouse', '')
    stock_out_code = request.GET.get('stock_out_code', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if warehouse_id and warehouse_id != 'None':
        stock_outs = stock_outs.filter(warehouse_id=warehouse_id)
    if stock_out_code and stock_out_code != 'None':
        stock_outs = stock_outs.filter(stock_out_code__icontains=stock_out_code)
    if date_from:
        stock_outs = stock_outs.filter(stock_out_time__date__gte=date_from)
    if date_to:
        stock_outs = stock_outs.filter(stock_out_time__date__lte=date_to)
    
    # 分页
    paginator = Paginator(stock_outs, 10)  # 每页显示10条记录
    page = request.GET.get('page')
    try:
        stock_outs = paginator.get_page(page)
    except PageNotAnInteger:
        stock_outs = paginator.get_page(1)
    except EmptyPage:
        stock_outs = paginator.get_page(paginator.num_pages)
    
    context = {
        'stock_outs': stock_outs,
        'warehouses': warehouses,
        'warehouse_id': warehouse_id if warehouse_id != 'None' else '',
        'stock_out_code': stock_out_code if stock_out_code != 'None' else '',
        'date_from': date_from,
        'date_to': date_to,
        'active_menu': 'storage_stock_out'
    }
    return render(request, 'storage/stock_out/list.html', context)

@login_required
def stock_out_create(request):
    """创建出库单"""
    if request.method == 'POST':
        form = StockOutForm(request.POST)
        if form.is_valid():
            stock_out = form.save(commit=False)
            stock_out.operator = request.user
            
            # 检查并更新库存
            inventory = stock_out.inventory
            if inventory.quantity >= stock_out.quantity:
                inventory.quantity -= stock_out.quantity
                inventory.save()
                stock_out.save()
                messages.success(request, '出库单创建成功！')
                return redirect('stock_out_list')
            else:
                messages.error(request, '库存不足！')
    else:
        form = StockOutForm()
    
    return render(request, 'storage/stock_out/form.html', {'form': form, 'title': '创建出库单', 'active_menu': 'storage_stock_out'})

@login_required
def sync_stock_in(request):
    """同步入库单数据"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '不支持的请求方法'}, status=405)
    
    try:
        from .sync import sync_all_stock_in
        success, message = sync_all_stock_in()
        return JsonResponse({'success': success, 'message': message})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'同步失败：{str(e)}'}, status=500)

@login_required
def sync_sales_order(request):
    """同步出库单数据"""
    from .sync import sync_all_stock_outs
    
    try:
        success, message = sync_all_stock_outs()
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
    except Exception as e:
        messages.error(request, f"同步失败：{str(e)}")
    
    return redirect('storage:stock_out_list')

@login_required
def report(request):
    """库存报表页面"""
    # 获取所有仓库
    warehouses = Warehouse.objects.all()
    warehouse_data = []
    
    # 获取当月第一天
    today = timezone.now()
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 获取每个仓库的统计数据
    for warehouse in warehouses:
        # 计算本月出入库数量和金额
        total_in = StockIn.objects.filter(
            warehouse=warehouse,
            stock_in_time__gte=month_start
        ).annotate(
            amount=F('quantity') * F('unit_cost')
        ).aggregate(
            total_qty=Sum('quantity'),
            total_amount=Sum('amount')
        )
        
        # 获取本月出库记录关联的入库单的成本
        total_out = StockOut.objects.filter(
            warehouse=warehouse,
            stock_out_time__gte=month_start
        ).annotate(
            amount=F('quantity') * F('inventory__stock_in__unit_cost')
        ).aggregate(
            total_qty=Sum('quantity'),
            total_amount=Sum('amount')
        )
        
        # 获取当前库存数量和金额
        current_inventory = Inventory.objects.filter(
            warehouse=warehouse,
            quantity__gt=0  # 只计算有库存的记录
        ).annotate(
            amount=F('quantity') * F('stock_in__unit_cost')
        ).aggregate(
            total_qty=Sum('quantity'),
            total_amount=Sum('amount')
        )
        
        # 计算月初库存（当前库存 - 本月入库 + 本月出库）
        initial_qty = (current_inventory['total_qty'] or 0) - (total_in['total_qty'] or 0) + (total_out['total_qty'] or 0)
        initial_amount = (current_inventory['total_amount'] or 0) - (total_in['total_amount'] or 0) + (total_out['total_amount'] or 0)
        
        # 整合该仓库的所有数据
        warehouse_data.append({
            'warehouse_name': warehouse.warehouse_name,
            'initial_quantity': initial_qty,
            'initial_amount': round(initial_amount or 0, 2),
            'total_in': total_in['total_qty'] or 0,
            'total_in_amount': round(total_in['total_amount'] or 0, 2),
            'total_out': total_out['total_qty'] or 0,
            'total_out_amount': round(total_out['total_amount'] or 0, 2),
            'total_inventory': current_inventory['total_qty'] or 0,
            'total_inventory_amount': round(current_inventory['total_amount'] or 0, 2)
        })
    
    # 获取最近的出入库记录
    recent_stock_ins = StockIn.objects.all().order_by('-stock_in_time')[:5]
    recent_stock_outs = StockOut.objects.all().order_by('-stock_out_time')[:5]
    
    context = {
        'warehouses': warehouse_data,
        'recent_stock_ins': recent_stock_ins,
        'recent_stock_outs': recent_stock_outs,
        'active_menu': 'storage_report',
        'current_month': today.strftime('%Y年%m月')
    }
    return render(request, 'storage/report.html', context)
