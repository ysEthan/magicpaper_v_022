from django.urls import path
from . import views

app_name = 'storage'

urlpatterns = [
    # 仓库管理
    path('warehouse/', views.warehouse_list, name='warehouse_list'),
    path('warehouse/create/', views.warehouse_create, name='warehouse_create'),
    path('warehouse/<int:pk>/', views.warehouse_detail, name='warehouse_detail'),
    path('warehouse/<int:pk>/edit/', views.warehouse_edit, name='warehouse_edit'),
    
    # 库存管理
    path('inventory/', views.inventory_list, name='inventory_list'),
    
    # 入库管理
    path('stock-in/', views.stock_in_list, name='stock_in_list'),
    path('stock-in/create/', views.stock_in_create, name='stock_in_create'),
    path('stock-in/sync/', views.sync_stock_in, name='sync_stock_in'),
    
    # 出库管理
    path('stock-out/', views.stock_out_list, name='stock_out_list'),
    path('stock-out/create/', views.stock_out_create, name='stock_out_create'),
    
    # API接口
    path('api/available-inventory/', views.available_inventory_api, name='available_inventory_api'),
] 