from django.urls import path
from . import views

app_name = 'page'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('products/', views.product_list, name='product_list'),
    path('products2/', views.products2, name='products2'),
    path('guest-order/', views.guest_order, name='guest_order'),
    path('get-sku-price/', views.get_sku_price, name='get_sku_price'),
] 