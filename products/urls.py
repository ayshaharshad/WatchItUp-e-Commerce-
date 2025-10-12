from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Home & Products
    path('', views.home, name='home'),
    path('products-list/', views.product_list, name='product_list'),
    path('men/', views.men_products, name='men_products'),
    path('women/', views.women_products, name='women_products'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    
    # Variant API
    path('api/variant/<int:product_pk>/<str:variant_color>/', views.get_variant_data, name='get_variant_data'),
    
    # ====== CART MANAGEMENT ======
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    
    # ====== CHECKOUT ======
    path('checkout/', views.checkout_view, name='checkout_view'),
    path('checkout/place-order/', views.place_order, name='place_order'),
    path('order/success/<str:order_id>/', views.order_success, name='order_success'),
    
    # ====== ORDER MANAGEMENT ======
    path('orders/', views.order_list, name='order_list'),
    path('order/<str:order_id>/', views.order_detail, name='order_detail'),
    path('order/<str:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('order/<str:order_id>/return/', views.return_order, name='return_order'),
    path('order/<str:order_id>/invoice/', views.download_invoice, name='download_invoice'),
    path('order/item/<int:item_id>/cancel/', views.cancel_order_item, name='cancel_order_item'),
    
    # ====== WISHLIST ======
    path('wishlist/', views.wishlist_view, name='wishlist_view'),
    path('wishlist/add/<int:pk>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:item_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/clear/', views.clear_wishlist, name='clear_wishlist'),
    path('wishlist/move-to-cart/<int:item_id>/', views.move_to_cart_from_wishlist, name='move_to_cart_from_wishlist'),
    path('wishlist/check/<int:pk>/', views.check_wishlist_status, name='check_wishlist_status')
]
    
