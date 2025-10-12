
from .models import Cart, Wishlist


def cart_wishlist_counts(request):
    """
    Make cart and wishlist counts available in all templates
    """
    context = {
        'cart_count': 0,
        'wishlist_count': 0,
    }
    
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            context['cart_count'] = cart.total_items
        except Cart.DoesNotExist:
            context['cart_count'] = 0
        
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            context['wishlist_count'] = wishlist.total_items
        except Wishlist.DoesNotExist:
            context['wishlist_count'] = 0
    
    return context