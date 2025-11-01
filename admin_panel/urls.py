from django.urls import path
from . import views

app_name = "admin_panel" 

urlpatterns = [
    path("login/", views.admin_login, name="admin_login"),
    path("logout/", views.admin_logout, name="admin_logout"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # Users
    path("users/", views.user_list, name="user_list"),
    path("users/block/<int:user_id>/", views.block_unblock_user, name="block_unblock_user"),

    # Categories
    path("categories/", views.category_list, name="category_list"),
    path("categories/add/", views.add_category, name="add_category"),
    path("categories/edit/<int:pk>/", views.edit_category, name="edit_category"),
    path("categories/delete/<int:pk>/", views.delete_category, name="delete_category"),

    # Products
    path("products/", views.product_list, name="product_list"),
    path("products/add/", views.add_product, name="add_product"),
    path("products/edit/<int:pk>/", views.edit_product, name="edit_product"),
    path("products/delete/<int:pk>/", views.delete_product, name="delete_product"),

     # Product Variant Management
    path("products/<int:product_id>/variants/", views.product_variant_detail, name="product_variant_detail"),
    path('variants/', views.variant_list, name='variant_list'),
    path('variants/add/', views.add_product_variant, name='add_product_variant'),
    path('variants/add/<int:product_id>/', views.add_product_variant, name='add_product_variant'),
    path('variants/<int:pk>/edit/', views.edit_product_variant, name='edit_product_variant'),
    path('variants/<int:pk>/delete/', views.delete_product_variant, name='delete_product_variant'),
    path('variants/bulk-create/', views.bulk_create_variants, name='bulk_create_variants'),
    path('variants/stock-update/', views.variant_stock_update, name='variant_stock_update'),

    # Order Management
    path('orders/', views.order_list, name='order_list'),
    path('orders/<str:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<str:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('orders/<str:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('orders/filters/clear/', views.clear_order_filters, name='clear_order_filters'),

    # Coupon Management
    path('coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/create/', views.create_coupon, name='create_coupon'),
    path('coupons/<int:pk>/', views.coupon_detail, name='coupon_detail'),
    path('coupons/<int:pk>/edit/', views.edit_coupon, name='edit_coupon'),
    path('coupons/<int:pk>/delete/', views.delete_coupon, name='delete_coupon'),
    path('coupons/<int:pk>/toggle-status/', views.toggle_coupon_status, name='toggle_coupon_status'),
    
    # Inventory Management
    path('inventory/report/', views.order_inventory_report, name='order_inventory_report'),
]
