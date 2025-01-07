from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
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
        'carrier_id': carrier_id
    })

@login_required
def service_detail(request, pk):
    service = get_object_or_404(Service, pk=pk)
    return render(request, 'logistics/service/detail.html', {
        'service': service
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
        'status_choices': Package.STATUS_CHOICES
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
