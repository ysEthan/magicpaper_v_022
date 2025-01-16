from django.contrib import admin
from .models import DemandRequest, DemandTracking, ProductionOrder

@admin.register(DemandRequest)
class DemandRequestAdmin(admin.ModelAdmin):
    list_display = ['request_number', 'title', 'request_type', 'priority', 'status', 'creator', 'handler', 'expected_completion_date']
    list_filter = ['request_type', 'priority', 'status']
    search_fields = ['request_number', 'title', 'description']
    raw_id_fields = ['creator', 'handler']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

@admin.register(DemandTracking)
class DemandTrackingAdmin(admin.ModelAdmin):
    list_display = ['demand', 'tracking_type', 'operator', 'created_at']
    list_filter = ['tracking_type']
    search_fields = ['content', 'demand__request_number']
    raw_id_fields = ['demand', 'operator']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'sku', 'quantity', 'status', 'production_start_date', 'production_end_date']
    list_filter = ['status']
    search_fields = ['order_number', 'sku__sku_code']
    raw_id_fields = ['sku', 'demand']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
