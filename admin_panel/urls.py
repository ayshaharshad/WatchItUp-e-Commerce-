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
    path('orders/<str:order_id>/', views.order_detail, name='order_detail'),  # admin_panel:order_detail
    path('orders/<str:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('orders/<str:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('orders/filters/clear/', views.clear_order_filters, name='clear_order_filters'),
    path('orders/<str:order_id>/cancel-items/', 
         views.cancel_order_items_admin, 
         name='cancel_order_items_admin'),
    
    path('orders/<str:order_id>/enhanced/', 
         views.order_detail_enhanced, 
         name='order_detail_enhanced'),

    # AJAX: Get items for cancellation
    path('orders/<str:order_id>/items/active/', 
         views.get_order_items_for_cancellation, 
         name='get_order_items_for_cancellation'),
    
    # ==================== CANCELLATION TRACKING ====================
    
    # View all cancellations (full orders + individual items)
    path('cancellations/', 
         views.cancellation_history, 
         name='cancellation_history'),
    
    # View detailed cancellation information
    path('cancellations/<int:cancellation_id>/', 
         views.cancellation_detail, 
         name='cancellation_detail'),
    
    # ==================== RETURN PROCESSING ====================
    
    # Process return request (approve/reject)
    path('returns/<int:return_id>/process/', 
         views.process_item_return_admin, 
         name='process_item_return_admin'),
    
    # ==================== STATISTICS & REPORTING ====================
    
    # Comprehensive order statistics dashboard
    path('orders/statistics/', 
         views.order_statistics_dashboard, 
         name='order_statistics_dashboard'),
    

    # Coupon Management
    path('coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/create/', views.create_coupon, name='create_coupon'),
    path('coupons/<int:pk>/', views.coupon_detail, name='coupon_detail'),
    path('coupons/<int:pk>/edit/', views.edit_coupon, name='edit_coupon'),
    path('coupons/<int:pk>/delete/', views.delete_coupon, name='delete_coupon'),
    path('coupons/<int:pk>/toggle-status/', views.toggle_coupon_status, name='toggle_coupon_status'),
    
    # Inventory Management
    path('inventory/report/', views.order_inventory_report, name='order_inventory_report'),

    # Product Offers
    path('offers/product/', views.product_offer_list, name='product_offer_list'),
    path('offers/product/create/', views.create_product_offer, name='create_product_offer'),
    path('offers/product/<int:pk>/edit/', views.edit_product_offer, name='edit_product_offer'),
    path('offers/product/<int:pk>/delete/', views.delete_product_offer, name='delete_product_offer'),
    path('offers/product/<int:pk>/toggle/', views.toggle_product_offer_status, name='toggle_product_offer_status'),
    
    # Category Offers
    path('offers/category/', views.category_offer_list, name='category_offer_list'),
    path('offers/category/create/', views.create_category_offer, name='create_category_offer'),
    path('offers/category/<int:pk>/edit/', views.edit_category_offer, name='edit_category_offer'),
    path('offers/category/<int:pk>/delete/', views.delete_category_offer, name='delete_category_offer'),
    path('offers/category/<int:pk>/toggle/', views.toggle_category_offer_status, name='toggle_category_offer_status'),
    
    # Referral Management
    path('referrals/', views.referral_list, name='referral_list'),

    # Return Request Management
    path('returns/', views.return_request_list, name='return_request_list'),
    path('returns/<int:pk>/', views.return_request_detail, name='return_request_detail'),
    path('returns/<int:pk>/approve/', views.approve_return_request, name='approve_return_request'),
    path('returns/<int:pk>/reject/', views.reject_return_request, name='reject_return_request'),

    # # Wallet Management
    # path('wallet/transactions/', views.wallet_transactions, name='wallet_transactions'),
    # path('wallet/user/<int:user_id>/', views.user_wallet_detail, name='user_wallet_detail'),
    # path('wallet/user/<int:user_id>/adjust/', views.admin_adjust_wallet, name='admin_adjust_wallet'),

    path('wallet/transactions/', views.wallet_transactions, name='wallet_transactions'),
    
    # ✅ NEW: Detailed transaction view
    path('wallet/transactions/<int:transaction_id>/', views.transaction_detail, name='transaction_detail'),
    
    # User-specific wallet detail (enhanced with filters)
    path('wallet/user/<int:user_id>/', views.user_wallet_detail, name='user_wallet_detail'),
    
    # Admin wallet adjustment
    path('wallet/user/<int:user_id>/adjust/', views.admin_adjust_wallet, name='admin_adjust_wallet'),
    
    # ✅ NEW: Wallet statistics dashboard
    path('wallet/statistics/', views.wallet_statistics, name='wallet_statistics'),

    # Sales Reports
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/sales/download/pdf/', views.download_sales_report_pdf, name='download_sales_report_pdf'),
    path('reports/sales/download/excel/', views.download_sales_report_excel, name='download_sales_report_excel'),

]