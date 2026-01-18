from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Home & Products
    path('', views.home, name='home'),
    path('products-list/', views.product_list, name='product_list'),
    path('men/', views.men_products, name='men_products'),
    path('women/', views.women_products, name='women_products'),
    path('product/<uuid:uuid>/', views.product_detail, name='product_detail'),
    
    # Variant API
    path('api/variant/<uuid:product_uuid>/<str:variant_color>/', views.get_variant_data, name='get_variant_data'),
    
    # ====== COUPON MANAGEMENT ======
    path('coupon/apply/', views.apply_coupon, name='apply_coupon'),
    path('coupon/remove/', views.remove_coupon, name='remove_coupon'),
    
    # ====== CART MANAGEMENT ======
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<uuid:uuid>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<uuid:item_uuid>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<uuid:item_uuid>/', views.remove_cart_item, name='remove_cart_item'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    # ✅ Cancel cart item URLs
    path('cart/cancel-item/<uuid:item_uuid>/', views.cancel_cart_item, name='cancel_cart_item'),
    path('cart/cancel-all/', views.cancel_entire_cart, name='cancel_entire_cart'),
    path('cart/cancel-selected/', views.cancel_selected_items, name='cancel_selected_items'),
    
    # ====== CHECKOUT & PAYMENT ======
    path('checkout/', views.checkout_view, name='checkout_view'),
    # ✅ NEW: Proceed to checkout with selection
    path('checkout/proceed/', views.proceed_to_checkout_with_selection, name='proceed_to_checkout_with_selection'),
    path('checkout/place-order-cod/', views.place_order_cod, name='place_order_cod'),
    path('checkout/create-razorpay-order/', views.create_razorpay_order, name='create_razorpay_order'),
    path('checkout/verify-payment/', views.verify_razorpay_payment, name='verify_razorpay_payment'),
    path('checkout/place-order-wallet/', views.place_order_wallet, name='place_order_wallet'),
    
    # ====== ORDER SUCCESS/FAILURE ======
    path('order/success/<str:order_id>/', views.order_success, name='order_success'),
    path('order/failure/<str:order_id>/', views.order_failure, name='order_failure'),
    path('order/<str:order_id>/retry-payment/', views.retry_payment, name='retry_payment'),
    path('order/invoice/<str:order_id>/', views.download_invoice, name='download_invoice'),
    
    # ====== ORDER MANAGEMENT ======
    path('orders/', views.order_list, name='order_list'),
    path('order/<str:order_id>/', views.order_detail, name='order_detail'),
    path('order/<str:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('order/<str:order_id>/return/', views.return_order, name='return_order'),
    path('order/<str:order_id>/invoice/', views.download_invoice, name='download_invoice'),
    path('order/item/<uuid:item_uuid>/cancel/', views.cancel_order_item, name='cancel_order_item'),
       # Cancel selected items
    path('order/<str:order_id>/cancel-items/', views.cancel_selected_items, name='cancel_selected_items'),
    
    # Return selected items
    path('order/<str:order_id>/return-items/', views.return_selected_items, name='return_selected_items'),
    
    # Get order items data (AJAX helper)
    path('order/<str:order_id>/items-data/', views.get_order_items_data, name='get_order_items_data'),
    # Invoice download
    path('order/invoice/<str:order_id>/', views.download_invoice, name='download_invoice'),

    
    # ====== WISHLIST ======
    path('wishlist/', views.wishlist_view, name='wishlist_view'),
    path('wishlist/add/<uuid:uuid>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<uuid:item_uuid>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/clear/', views.clear_wishlist, name='clear_wishlist'),
    path('wishlist/move-to-cart/<uuid:item_uuid>/', views.move_to_cart_from_wishlist, name='move_to_cart_from_wishlist'),
    path('wishlist/check/<uuid:uuid>/', views.check_wishlist_status, name='check_wishlist_status'),
]