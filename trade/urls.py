from django.urls import path
from . import views

app_name = 'trade'

urlpatterns = [
    # 订单列表
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    # 订单详情
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    # 创建订单
    path('orders/create/', views.OrderCreateView.as_view(), name='order_create'),
    # 更新订单
    path('orders/<int:pk>/update/', views.OrderUpdateView.as_view(), name='order_update'),
    # 同步订单
    path('orders/sync/', views.sync_orders, name='order_sync'),
    path('report/', views.report, name='report'),
    path('sales-detail/', views.SalesDetailView.as_view(), name='sales_detail'),
    path('sales-detail/export/', views.export_sales_detail, name='export_sales_detail'),
] 