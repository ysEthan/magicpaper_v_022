from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
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
    warehouse_id = request.GET.get('warehouse')
    sku_code = request.GET.get('sku_code')
    batch_code = request.GET.get('batch_code')
    
    if warehouse_id:
        inventories = inventories.filter(warehouse_id=warehouse_id)
    if sku_code:
        inventories = inventories.filter(sku__sku_code__icontains=sku_code)
    if batch_code:
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
        'sku_code': sku_code,
        'batch_code': batch_code
    }
    return render(request, 'storage/inventory/list.html', context)

@login_required
def stock_in_list(request):
    """入库记录列表"""
    stock_ins = StockIn.objects.all().order_by('-stock_in_time')
    warehouses = Warehouse.objects.all()
    
    # 处理筛选
    warehouse_id = request.GET.get('warehouse')
    stock_in_code = request.GET.get('stock_in_code')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if warehouse_id:
        stock_ins = stock_ins.filter(warehouse_id=warehouse_id)
    if stock_in_code:
        stock_ins = stock_ins.filter(stock_in_code__icontains=stock_in_code)
    if date_from:
        stock_ins = stock_ins.filter(stock_in_time__date__gte=date_from)
    if date_to:
        stock_ins = stock_ins.filter(stock_in_time__date__lte=date_to)
    
    return render(request, 'storage/stock_in/list.html', {
        'stock_ins': stock_ins,
        'warehouses': warehouses,
        'warehouse_id': warehouse_id,
        'stock_in_code': stock_in_code,
        'date_from': date_from,
        'date_to': date_to,
        'active_menu': 'storage_stock_in'
    })

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
    warehouse_id = request.GET.get('warehouse')
    stock_out_code = request.GET.get('stock_out_code')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if warehouse_id:
        stock_outs = stock_outs.filter(warehouse_id=warehouse_id)
    if stock_out_code:
        stock_outs = stock_outs.filter(stock_out_code__icontains=stock_out_code)
    if date_from:
        stock_outs = stock_outs.filter(stock_out_time__date__gte=date_from)
    if date_to:
        stock_outs = stock_outs.filter(stock_out_time__date__lte=date_to)
    
    return render(request, 'storage/stock_out/list.html', {
        'stock_outs': stock_outs,
        'warehouses': warehouses,
        'warehouse_id': warehouse_id,
        'stock_out_code': stock_out_code,
        'date_from': date_from,
        'date_to': date_to,
        'active_menu': 'storage_stock_out'
    })

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
