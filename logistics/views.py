from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from .models import Carrier, Service, Package, Tracking
import json

@login_required
def carrier_list(request):
    search_term = request.GET.get('search', '')
    carriers = Carrier.objects.all()
    
    if search_term:
        carriers = carriers.filter(
            Q(name_zh__icontains=search_term) |
            Q(name_en__icontains=search_term) |
            Q(code__icontains=search_term)
        )
    
    paginator = Paginator(carriers, 20)
    page = request.GET.get('page')
    carriers = paginator.get_page(page)
    
    return render(request, 'logistics/carrier/list.html', {
        'carriers': carriers,
        'search_term': search_term
    })

@login_required
def carrier_detail(request, pk):
    carrier = get_object_or_404(Carrier, pk=pk)
    services = carrier.service_set.all()
    
    return render(request, 'logistics/carrier/detail.html', {
        'carrier': carrier,
        'services': services
    })

@login_required
def service_list(request):
    search_term = request.GET.get('search', '')
    carrier_id = request.GET.get('carrier', '')
    services = Service.objects.all()
    
    if search_term:
        services = services.filter(
            Q(service_name__icontains=search_term) |
            Q(service_code__icontains=search_term)
        )
    
    if carrier_id:
        services = services.filter(carrier_id=carrier_id)
    
    carriers = Carrier.objects.all()
    paginator = Paginator(services, 20)
    page = request.GET.get('page')
    services = paginator.get_page(page)
    
    return render(request, 'logistics/service/list.html', {
        'services': services,
        'carriers': carriers,
        'search_term': search_term,
        'carrier_id': carrier_id,
        'active_menu': 'logistics',
        'active_submenu': 'service'
    })

@login_required
def service_detail(request, pk):
    service = get_object_or_404(Service, pk=pk)
    return render(request, 'logistics/service/detail.html', {
        'service': service,
        'active_menu': 'logistics',
        'active_submenu': 'service'
    })

@login_required
def package_list(request):
    search_term = request.GET.get('search', '')
    status = request.GET.get('status', '')
    packages = Package.objects.all()
    
    if search_term:
        packages = packages.filter(
            Q(tracking_no__icontains=search_term) |
            Q(order__order_number__icontains=search_term)
        )
    
    if status:
        packages = packages.filter(pkg_status_code=status)
    
    paginator = Paginator(packages, 20)
    page = request.GET.get('page')
    packages = paginator.get_page(page)
    
    return render(request, 'logistics/package/list.html', {
        'packages': packages,
        'search_term': search_term,
        'status': status,
        'status_choices': Package.STATUS_CHOICES,
        'active_menu': 'logistics',
        'active_submenu': 'package'
    })

@login_required
def package_detail(request, pk):
    package = get_object_or_404(Package, pk=pk)
    tracking_records = package.tracking_records.all().order_by('-tracking_time')
    
    return render(request, 'logistics/package/detail.html', {
        'package': package,
        'tracking_records': tracking_records
    })

@login_required
def tracking_list(request, pk):
    package = get_object_or_404(Package, pk=pk)
    tracking_records = package.tracking_records.all().order_by('-tracking_time')
    
    return render(request, 'logistics/tracking/list.html', {
        'package': package,
        'tracking_records': tracking_records
    })

@login_required
def service_update(request, pk):
    if request.method != 'PUT':
        return JsonResponse({'success': False, 'message': '不支持的请求方法'})
    
    service = get_object_or_404(Service, pk=pk)
    try:
        data = json.loads(request.body)
        service.service_name = data.get('service_name', service.service_name)
        service.service_code = data.get('service_code', service.service_code)
        service.service_type = data.get('service_type', service.service_type)
        service.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def report(request):
    """物流报表页面"""
    today = timezone.now()
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 总体统计
    total_packages = Package.objects.count()
    new_packages_today = Package.objects.filter(created_at__date=today.date()).count()
    
    # 未完成包裹（未发货或运输中的包裹）
    pending_packages = Package.objects.filter(
        pkg_status_code__in=['0', '1', '2']
    ).count()
    
    # 计算本月运费
    month_shipping_cost = Package.objects.filter(
        created_at__gte=month_start
    ).aggregate(
        total=Sum('carrier_cost')
    )['total'] or 0
    
    # 异常包裹（已取消）
    abnormal_packages = Package.objects.filter(
        pkg_status_code='4'
    ).count()
    
    # 计算百分比
    pending_packages_percentage = round((pending_packages / total_packages * 100) if total_packages > 0 else 0, 1)
    abnormal_packages_percentage = round((abnormal_packages / total_packages * 100) if total_packages > 0 else 0, 1)
    
    # 计算环比（与上月相比的增长率）
    last_month_start = month_start.replace(month=month_start.month-1 if month_start.month > 1 else 12)
    last_month_cost = Package.objects.filter(
        created_at__gte=last_month_start,
        created_at__lt=month_start
    ).aggregate(
        total=Sum('carrier_cost')
    )['total'] or 0
    month_over_month = round(
        ((month_shipping_cost - last_month_cost) / last_month_cost * 100) if last_month_cost > 0 else 0,
        1
    )
    
    # 按物流商统计
    carriers = Carrier.objects.annotate(
        total_packages=Count('services__packages'),
        pending_packages=Count(
            'services__packages',
            filter=Q(services__packages__pkg_status_code__in=['0', '1', '2'])
        ),
        month_cost=Sum(
            'services__packages__carrier_cost',
            filter=Q(services__packages__created_at__gte=month_start)
        ),
        abnormal_packages=Count(
            'services__packages',
            filter=Q(services__packages__pkg_status_code='4')
        )
    )
    
    # 按包裹状态统计
    package_status = []
    total_cost = Package.objects.aggregate(
        total=Sum('carrier_cost')
    )['total'] or 0
    
    for status_code, status_name in Package.STATUS_CHOICES:
        status_packages = Package.objects.filter(pkg_status_code=status_code)
        count = status_packages.count()
        cost = status_packages.aggregate(
            total=Sum('carrier_cost')
        )['total'] or 0
        percentage = round((cost / total_cost * 100) if total_cost > 0 else 0, 1)
        
        package_status.append({
            'name': status_name,
            'count': count,
            'cost': cost,
            'percentage': percentage
        })
    
    context = {
        'total_packages': total_packages,
        'new_packages_today': new_packages_today,
        'pending_packages': pending_packages,
        'pending_packages_percentage': pending_packages_percentage,
        'month_shipping_cost': month_shipping_cost,
        'month_over_month': month_over_month,
        'abnormal_packages': abnormal_packages,
        'abnormal_packages_percentage': abnormal_packages_percentage,
        'carriers': carriers,
        'package_status': package_status,
        'current_month': today.strftime('%Y年%m月'),
        'active_menu': 'logistics',
        'active_submenu': 'report'
    }
    
    return render(request, 'logistics/report.html', context)
