from django.urls import path
from . import views

app_name = 'logistics'

urlpatterns = [
    # 物流商管理
    path('carriers/', views.carrier_list, name='carrier_list'),
    path('carriers/<int:pk>/', views.carrier_detail, name='carrier_detail'),
    
    # 物流服务
    path('services/', views.service_list, name='service_list'),
    path('services/<int:pk>/', views.service_detail, name='service_detail'),
    
    # 包裹管理
    path('packages/', views.package_list, name='package_list'),
    path('packages/<int:pk>/', views.package_detail, name='package_detail'),
    path('packages/<int:pk>/tracking/', views.tracking_list, name='tracking_list'),
    
    # API endpoints
    path('api/services/<int:pk>/', views.service_update, name='service_update'),
] 