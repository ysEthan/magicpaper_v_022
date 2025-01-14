from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q, Count, Sum, F, OuterRef, Subquery
from django.utils import timezone
from .models import Carrier, Service, Package, Tracking
import json
from django.contrib import messages
from django.utils.translation import gettext as _
from .services.jky_service import JiKeYunService
from .jky_config import CARRIER_CODE_MAP
import logging
from django.utils.safestring import mark_safe

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
    services = carrier.services.all()
    
    return render(request, 'logistics/carrier/detail.html', {
        'carrier': carrier,
        'services': services,
        'active_menu': 'logistics',
        'active_submenu': 'carrier'
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
    """包裹列表页面"""
    search_term = request.GET.get('search', '')
    status = request.GET.get('status', '')
    carrier_id = request.GET.get('carrier', '')
    
    packages = Package.objects.annotate(
        pending_time=Subquery(
            Tracking.objects.filter(
                package=OuterRef('pk'),
                status=0
            ).values('tracking_time')[:1]
        )
    ).order_by('-pending_time', '-created_at')
    
    if search_term:
        packages = packages.filter(
            Q(tracking_no__icontains=search_term) |
            Q(order__order_number__icontains=search_term)
        )
    
    if status:
        packages = packages.filter(pkg_status_code=status)
        
    if carrier_id:
        packages = packages.filter(service__carrier_id=carrier_id)
    
    carriers = Carrier.objects.all()
    paginator = Paginator(packages, 20)
    page = request.GET.get('page')
    packages = paginator.get_page(page)
    
    return render(request, 'logistics/package/list.html', {
        'packages': packages,
        'carriers': carriers,
        'search_term': search_term,
        'carrier_id': carrier_id,
        'status': status,
        'status_choices': Package.STATUS_CHOICES,
        'active_menu': 'logistics',
        'active_submenu': 'package'
    })

@login_required
def package_detail(request, pk):
    package = get_object_or_404(Package, pk=pk)
    tracking_records = package.tracking_records.all().order_by('-tracking_time')
    
    if request.method == 'POST':
        try:
            # Create new tracking record
            tracking = Tracking.objects.create(
                package=package,
                status=int(request.POST.get('status')),
                location=request.POST.get('location'),
                description=request.POST.get('description'),
                tracking_time=request.POST.get('tracking_time'),
                operator=request.user
            )
            
            # Update package status
            package.pkg_status_code = str(tracking.status)
            package.save()
            
            messages.success(request, _('物流轨迹添加成功'))
        except Exception as e:
            messages.error(request, _('物流轨迹添加失败：{}').format(str(e)))
        
        return redirect('logistics:package_detail', pk=pk)
    
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

def push_to_jky(request, pk):
    """推送包裹信息到吉客云"""
    try:
        package = get_object_or_404(Package, pk=pk)
        logger = logging.getLogger('logistics.jky')
        
        logger.info(f"开始处理包裹推送请求 - 包裹ID: {pk}")
        logger.info(f"包裹基本信息 - 运单号: {package.tracking_no}, 物流商: {package.carrier_name}, 服务: {package.service_name}")
        
        # 检查必要信息是否完整
        missing_fields = []
        request_info = {
            '包裹ID': pk,
            '运单号': package.tracking_no or '未填写',
            '发货仓库': package.warehouse.warehouse_name if package.warehouse else '未选择',
            '平台订单号': package.order.platform_order_number if package.order else '未填写',
            '物流商': package.carrier_name or '未选择',
            '物流服务': package.service_name or '未选择',
            '包裹状态': package.get_pkg_status_code_display() if hasattr(package, 'get_pkg_status_code_display') else '未知',
            '包裹尺寸': {
                '长': str(package.length) if package.length else '未填写',
                '宽': str(package.width) if package.width else '未填写',
                '高': str(package.height) if package.height else '未填写',
                '重量': str(package.weight) if package.weight else '未填写',
                '体积': str(package.volume) if package.volume else '未填写'
            }
        }
        
        if not package.tracking_no:
            missing_fields.append('运单号')
            
        if not package.warehouse:
            missing_fields.append('发货仓库')
            
        if not package.order.platform_order_number:
            missing_fields.append('平台订单号')
        
        if missing_fields:
            error_message = mark_safe(_(
                f'以下字段不能为空：{", ".join(missing_fields)}<br><br>'
                '<strong>当前数据：</strong><br>'
                '<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 10px;">'
                f'{json.dumps(request_info, ensure_ascii=False, indent=2)}</pre>'
            ))
            messages.error(request, error_message)
            logger.warning(f"推送失败：字段缺失 - 包裹ID: {pk}, 缺失字段: {missing_fields}")
            return redirect('logistics:package_detail', pk=pk)
        
        # 推送到吉客云
        service = JiKeYunService()
        success, message, request_data = service.push_package(package)
        
        if success:
            messages.success(request, mark_safe(_(
                '推送成功<br><br>'
                '<strong>请求数据：</strong><br>'
                '<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 10px;">'
                f'{request_data}</pre>'
            )))
            logger.info(f"推送成功 - 包裹ID: {pk}")
        else:
            messages.error(request, mark_safe(_(
                f'{message}<br><br>'
                '<strong>请求数据：</strong><br>'
                '<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 10px;">'
                f'{request_data}</pre>'
            )))
            logger.error(f"推送失败 - 包裹ID: {pk}, 错误信息: {message}")
        
    except Exception as e:
        error_msg = f"系统错误: {str(e)}"
        try:
            current_data = {
                '包裹ID': pk,
                '错误类型': e.__class__.__name__,
                '错误信息': str(e),
                '错误位置': str(e.__traceback__.tb_frame.f_code.co_filename),
                '错误行号': str(e.__traceback__.tb_lineno)
            }
            error_detail = json.dumps(current_data, ensure_ascii=False, indent=2)
        except:
            error_detail = str(e)
            
        messages.error(request, mark_safe(_(
            f'{error_msg}<br><br>'
            '<strong>错误详情：</strong><br>'
            '<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 10px;">'
            f'{error_detail}</pre>'
        )))
        logger.exception(f"推送异常 - 包裹ID: {pk}")
    
    return redirect('logistics:package_detail', pk=pk)
