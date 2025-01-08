from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    # Brand URLs
    path('brands/', views.brand_list, name='brand_list'),
    path('brands/create/', views.brand_edit, name='brand_create'),
    path('brands/<int:pk>/', views.brand_detail, name='brand_detail'),
    path('brands/<int:pk>/edit/', views.brand_edit, name='brand_edit'),
    path('brands/<int:pk>/delete/', views.brand_delete, name='brand_delete'),

    # Category URLs
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_edit, name='category_create'),
    path('categories/<int:pk>/', views.category_detail, name='category_detail'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # SPU URLs
    path('spus/', views.spu_list, name='spu_list'),
    path('spus/create/', views.spu_edit, name='spu_create'),
    path('spus/<int:pk>/', views.spu_detail, name='spu_detail'),
    path('spus/<int:pk>/edit/', views.spu_edit, name='spu_edit'),
    path('spus/<int:pk>/delete/', views.spu_delete, name='spu_delete'),

    # SKU URLs
    path('skus/', views.sku_list, name='sku_list'),
    path('skus/create/', views.sku_edit, name='sku_create'),
    path('skus/<int:pk>/', views.sku_detail, name='sku_detail'),
    path('skus/<int:pk>/edit/', views.sku_edit, name='sku_edit'),
    path('skus/<int:pk>/delete/', views.sku_delete, name='sku_delete'),

    # Sync URLs
    path('sync/', views.sync_products, name='sync_products'),

    # Report URL
    path('report/', views.report, name='report'),
] 