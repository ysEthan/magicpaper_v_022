from django.urls import path
from . import views

app_name = 'procurement'

urlpatterns = [
    # 供应商相关URL
    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/create/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('suppliers/<int:pk>/', views.SupplierDetailView.as_view(), name='supplier_detail'),
    path('suppliers/<int:pk>/update/', views.SupplierUpdateView.as_view(), name='supplier_update'),

    # 采购订单相关URL
    path('orders/', views.PurchaseOrderListView.as_view(), name='purchase_order_list'),
    path('orders/create/', views.PurchaseOrderCreateView.as_view(), name='purchase_order_create'),
    path('orders/<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='purchase_order_detail'),
    path('orders/<int:pk>/update/', views.PurchaseOrderUpdateView.as_view(), name='purchase_order_update'),
    
    # 同步功能
    path('sync/orders/', views.sync_purchase_orders, name='sync_purchase_orders'),
] 