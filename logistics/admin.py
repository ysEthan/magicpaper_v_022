from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Carrier, Service, Package, Tracking


@admin.register(Carrier)
class CarrierAdmin(admin.ModelAdmin):
    list_display = ['name_zh', 'name_en', 'code', 'contact', 'url']
    list_filter = ['created_at']
    search_fields = ['name_zh', 'name_en', 'code']
    ordering = ['name_zh']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['carrier', 'service_name', 'service_code', 'service_type']
    list_filter = ['carrier', 'service_type']
    search_fields = ['service_name', 'service_code', 'carrier__name_zh']
    ordering = ['carrier', 'service_name']


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'order', 'tracking_no', 'carrier_name', 'service_name',
        'pkg_status_code', 'weight', 'volume', 'estimated_logistics_cost',
        'carrier_cost'
    ]
    list_filter = ['pkg_status_code', 'service__carrier', 'created_at']
    search_fields = ['tracking_no', 'order__order_number']
    readonly_fields = [
        'created_at', 'updated_at', 'volume', 'volume_weight'
    ]
    raw_id_fields = ['order', 'warehouse', 'service']
    date_hierarchy = 'created_at'
    fieldsets = [
        (None, {
            'fields': (
                'order', 'warehouse', 'service', 'tracking_no',
                'pkg_status_code', 'items'
            )
        }),
        (_('包裹尺寸'), {
            'fields': (
                ('length', 'width', 'height'),
                ('weight', 'volume', 'volume_weight')
            )
        }),
        (_('费用信息'), {
            'fields': (
                'estimated_logistics_cost', 'carrier_cost'
            )
        }),
        (_('时间信息'), {
            'fields': (
                'created_at', 'updated_at'
            )
        })
    ]

    def carrier_name(self, obj):
        return obj.carrier_name
    carrier_name.short_description = _('物流商')

    def service_name(self, obj):
        return obj.service_name
    service_name.short_description = _('服务名称')

    def volume(self, obj):
        if obj.volume:
            return f"{obj.volume:.2f} cm³"
        return "-"
    volume.short_description = _('体积')


@admin.register(Tracking)
class TrackingAdmin(admin.ModelAdmin):
    list_display = ['package', 'status', 'location', 'tracking_time', 'operator']
    list_filter = ['status', 'tracking_time', 'operator']
    search_fields = ['package__tracking_no', 'location', 'description']
    raw_id_fields = ['package', 'operator']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'tracking_time'
    ordering = ['-tracking_time']
