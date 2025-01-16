from django.urls import path
from . import views

app_name = 'manufacturing'

urlpatterns = [
    # 需求申请相关URL
    path('demand/', views.demand_list, name='demand_list'),
    path('demand/create/', views.demand_create, name='demand_create'),
    path('demand/<int:pk>/', views.demand_detail, name='demand_detail'),
    path('demand/<int:pk>/edit/', views.demand_edit, name='demand_edit'),
    path('demand/<int:pk>/delete/', views.demand_delete, name='demand_delete'),
    path('demand/<int:pk>/tracking/add/', views.tracking_create, name='tracking_create'),
    
    # 生产工单相关URL
    path('production/', views.production_list, name='production_list'),
    path('production/create/', views.production_create, name='production_create'),
    path('production/<int:pk>/', views.production_detail, name='production_detail'),
    path('production/<int:pk>/edit/', views.production_edit, name='production_edit'),
    path('production/<int:pk>/delete/', views.production_delete, name='production_delete'),
    
    # 报表页面
    path('report/', views.report, name='report'),
] 