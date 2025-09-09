from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.home, name='home'),
    path('products-list/', views.product_list, name='product_list'),
    path('men/', views.men_products, name='men_products'),
    path('women/', views.women_products, name='women_products'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('coupon/apply/', views.apply_coupon, name='apply_coupon'),
]