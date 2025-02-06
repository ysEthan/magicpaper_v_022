from django.urls import path
from . import views

app_name = 'page'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('products/', views.product_list, name='product_list'),
    path('products2/', views.products2, name='products2'),
    path('guest-order/', views.guest_order, name='guest_order'),
    path('guest-order/query/', views.guest_order_query, name='guest_order_query'),
    path('get-sku-price/', views.get_sku_price, name='get_sku_price'),


    path('redbook_api/', views.redbook_callback, name='redbook_callback'),

] 