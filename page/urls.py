from django.urls import path
from . import views

app_name = 'page'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('products/', views.product_list, name='product_list'),
] 