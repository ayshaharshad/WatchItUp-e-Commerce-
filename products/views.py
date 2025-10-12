from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Avg, F, Min, Max
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from decimal import Decimal
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json

from .models import (
    Product, Category, ProductVariant, ProductReview, Coupon, Cart, CartItem, 
    Checkout, CheckoutItem, Order, OrderItem,
    OrderCancellation, OrderReturn, Wishlist, WishlistItem
)
from users.models import Address

# |---------Products----------|


def home(request):
    """Home page view"""
    return render(request, 'products/home.html')


def product_list(request):
    """Product listing with search, filter, sort and pagination - Updated for variants"""
    products = Product.objects.filter(is_active=True).select_related('category', 'brand').prefetch_related('variants__images')
    
    # Get filter parameters
    search_query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')
    color_filter = request.GET.get('color', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    sort_by = request.GET.get('sort', '')
    
    # Search functionality
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__name__icontains=search_query)
        )
    
    # Category filter
    if category_filter:
        products = products.filter(category__name=category_filter)
    
    # Color filter
    if color_filter:
        products = products.filter(variants__color=color_filter, variants__is_active=True)
    
    # Price range filter
    if min_price:
        try:
            min_price_decimal = Decimal(min_price)
            products = products.filter(variants__price__gte=min_price_decimal, variants__is_active=True)
        except:
            min_price = ''
    
    if max_price:
        try:
            max_price_decimal = Decimal(max_price)
            products = products.filter(variants__price__lte=max_price_decimal, variants__is_active=True)
        except:
            max_price = ''
    
    # Sorting
    if sort_by == 'price_low':
        products = products.annotate(min_variant_price=Min('variants__price')).order_by('min_variant_price')
    elif sort_by == 'price_high':
        products = products.annotate(max_variant_price=Max('variants__price')).order_by('-max_variant_price')
    elif sort_by == 'name_asc':
        products = products.order_by('name')
    elif sort_by == 'name_desc':
        products = products.order_by('-name')
    else:
        products = products.order_by('-created_at')
    
    products = products.distinct()
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get active categories for filter
    categories = Category.objects.filter(is_active=True)
    
    # Get available colors for filter
    available_colors = ProductVariant.COLOR_CHOICES
    
    # Build query string for pagination links
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = query_params.urlencode()
    
    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'categories': categories,
        'available_colors': available_colors,
        'search_query': search_query,
        'category_filter': category_filter,
        'color_filter': color_filter,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
        'query_string': query_string,
        'total_products': paginator.count,
    }
    
    return render(request, 'products/product_list.html', context)

# |---------Categories----------|


def men_products(request):
    """Men's products listing"""
    products = Product.objects.filter(
        is_active=True, 
        category__name='Men'
    ).select_related('category', 'brand').prefetch_related('variants__images')
    
    # Get filter parameters
    search_query = request.GET.get('q', '')
    color_filter = request.GET.get('color', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    sort_by = request.GET.get('sort', '')
    
    # Search functionality
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__name__icontains=search_query)
        )
    
    # Color filter
    if color_filter:
        products = products.filter(variants__color=color_filter, variants__is_active=True)
    
    # Price range filter
    if min_price:
        try:
            min_price_decimal = Decimal(min_price)
            products = products.filter(variants__price__gte=min_price_decimal, variants__is_active=True)
        except:
            min_price = ''
    
    if max_price:
        try:
            max_price_decimal = Decimal(max_price)
            products = products.filter(variants__price__lte=max_price_decimal, variants__is_active=True)
        except:
            max_price = ''
    
    # Sorting
    if sort_by == 'price_low':
        products = products.annotate(min_variant_price=Min('variants__price')).order_by('min_variant_price')
    elif sort_by == 'price_high':
        products = products.annotate(max_variant_price=Max('variants__price')).order_by('-max_variant_price')
    elif sort_by == 'name_asc':
        products = products.order_by('name')
    elif sort_by == 'name_desc':
        products = products.order_by('-name')
    else:
        products = products.order_by('-created_at')
    
    products = products.distinct()
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available colors for filter
    available_colors = ProductVariant.COLOR_CHOICES
    
    # Build query string for pagination links
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = query_params.urlencode()
    
    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'available_colors': available_colors,
        'search_query': search_query,
        'color_filter': color_filter,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
        'query_string': query_string,
        'total_products': paginator.count,
        'category_title': 'Men\'s Watches',
    }
    
    return render(request, 'products/category_products.html', context)


def women_products(request):
    """Women's products listing"""
    products = Product.objects.filter(
        is_active=True, 
        category__name='Women'
    ).select_related('category', 'brand').prefetch_related('variants__images')
    
    # Get filter parameters
    search_query = request.GET.get('q', '')
    color_filter = request.GET.get('color', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    sort_by = request.GET.get('sort', '')
    
    # Search functionality
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__name__icontains=search_query)
        )
    
    # Color filter
    if color_filter:
        products = products.filter(variants__color=color_filter, variants__is_active=True)
    
    # Price range filter
    if min_price:
        try:
            min_price_decimal = Decimal(min_price)
            products = products.filter(variants__price__gte=min_price_decimal, variants__is_active=True)
        except:
            min_price = ''
    
    if max_price:
        try:
            max_price_decimal = Decimal(max_price)
            products = products.filter(variants__price__lte=max_price_decimal, variants__is_active=True)
        except:
            max_price = ''
    
    # Sorting
    if sort_by == 'price_low':
        products = products.annotate(min_variant_price=Min('variants__price')).order_by('min_variant_price')
    elif sort_by == 'price_high':
        products = products.annotate(max_variant_price=Max('variants__price')).order_by('-max_variant_price')
    elif sort_by == 'name_asc':
        products = products.order_by('name')
    elif sort_by == 'name_desc':
        products = products.order_by('-name')
    else:
        products = products.order_by('-created_at')
    
    products = products.distinct()
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available colors for filter
    available_colors = ProductVariant.COLOR_CHOICES
    
    # Build query string for pagination links
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = query_params.urlencode()
    
    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'available_colors': available_colors,
        'search_query': search_query,
        'color_filter': color_filter,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
        'query_string': query_string,
        'total_products': paginator.count,
        'category_title': 'Women\'s Watches',
    }
    
    return render(request, 'products/category_products.html', context)

# |---------Product Detail----------|


def product_detail(request, pk):
    """UNIFIED CAROUSEL - Product detail page with combined general + variant images"""
    try:
        product = get_object_or_404(Product, pk=pk)
        
        # Check product availability
        if not product.is_active or not product.category.is_active or (product.brand and not product.brand.is_active):
            messages.error(request, f"Sorry, '{product.name}' is currently unavailable.")
            return redirect('products:product_list')
            
    except Http404:
        messages.error(request, "Product not found.")
        return redirect('products:product_list')
    
    # Get active product variants
    variants = product.variants.filter(is_active=True).prefetch_related('images').order_by('color')
    
    # UNIFIED IMAGE COLLECTION
    all_images = []
    
    # Add general product images first
    general_images = product.images.all()
    for idx, img in enumerate(general_images):
        all_images.append({
            'url': img.image.url,
            'zoom_image': img.zoom_image.url if img.zoom_image else img.image.url,
            'type': 'general',
            'variant': None,
            'variant_color': None,
            'variant_name': None,
            'is_first_general': idx == 0,
            'index': len(all_images)
        })
    
    # Add variant images for each variant
    for variant in variants:
        variant_images = variant.images.all()
        for idx, img in enumerate(variant_images):
            all_images.append({
                'url': img.image.url,
                'zoom_image': img.zoom_image.url if img.zoom_image else img.image.url,
                'type': 'variant',
                'variant': variant.id,
                'variant_color': variant.color,
                'variant_name': variant.get_color_display(),
                'color_hex': variant.color_hex,
                'is_first_variant': idx == 0,
                'index': len(all_images)
            })
    
    # Debug print for all_images
    print("All Images:", all_images)
    
    # Get product reviews
    reviews = ProductReview.objects.filter(
        product=product, 
        is_active=True
    ).select_related('user').order_by('-created_at')
    
    # Get related products
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True,
        category__is_active=True
    ).exclude(pk=product.pk).select_related('category', 'brand').prefetch_related('variants__images')[:4]
    
    # Get available coupons
    available_coupons = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=timezone.now(),
        valid_to__gte=timezone.now()
    ).filter(
        Q(usage_limit__isnull=True) | Q(usage_limit__gt=F('used_count'))
    )[:3]
    
    # Rating distribution
    rating_distribution = {}
    total_reviews = reviews.count()
    for i in range(1, 6):
        count = reviews.filter(rating=i).count()
        percentage = (count / total_reviews * 100) if total_reviews > 0 else 0
        rating_distribution[i] = {
            'count': count,
            'percentage': round(percentage, 1)
        }
    
    context = {
        'product': product,
        'variants': variants,
        'all_images': all_images,
        'general_images': general_images,
        'related_products': related_products,
        'reviews': reviews,
        'available_coupons': available_coupons,
        'rating_distribution': rating_distribution,
        'breadcrumb_category': product.category.name,
    }
    
    return render(request, 'products/product_detail.html', context)


# |---------Variant----------|

@require_GET
def get_variant_data(request, product_pk, variant_color):
    """Get variant data for quick selection without carousel change"""
    try:
        product = get_object_or_404(Product, pk=product_pk)
        variant = get_object_or_404(ProductVariant, product=product, color=variant_color, is_active=True)
        
        variant_data = {
            'id': variant.id,
            'color': variant.color,
            'color_display': variant.get_color_display(),
            'color_hex': variant.color_hex,
            'price': str(variant.price),
            'original_price': str(variant.original_price) if variant.original_price else None,
            'discount_percentage': variant.discount_percentage,
            'stock_quantity': variant.stock_quantity,
            'is_in_stock': variant.is_in_stock,
            'sku': variant.sku,
        }
        
        return JsonResponse({'success': True, 'variant': variant_data})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})



def apply_coupon(request):
    """Apply coupon with validation"""
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_code', '').strip().upper()
        
        if not coupon_code:
            messages.error(request, "Please enter a coupon code.")
            return redirect(request.META.get('HTTP_REFERER', 'products:home'))
        
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            
            if not coupon.is_valid:
                messages.error(request, "This coupon is not valid or has expired.")
            else:
                request.session['applied_coupon'] = coupon_code
                
                if coupon.discount_type == 'percentage':
                    messages.success(request, f"Coupon applied! You get {coupon.discount_value}% discount.")
                else:
                    messages.success(request, f"Coupon applied! You get ₹{coupon.discount_value} discount.")
                    
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code.")
    
    return redirect(request.META.get('HTTP_REFERER', 'products:home'))

# ================== CART VIEWS ==================


@login_required
@require_POST
def add_to_cart(request, pk):
    """Add product variant to cart with comprehensive validation"""
    try:
        product = get_object_or_404(Product, pk=pk)
        
        # Validate product availability
        if not product.is_active or not product.category.is_active:
            return JsonResponse({
                'success': False,
                'message': f"'{product.name}' is currently unavailable."
            })
        
        if product.brand and not product.brand.is_active:
            return JsonResponse({
                'success': False,
                'message': f"'{product.name}' is currently unavailable."
            })
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Get requested quantity
        try:
            quantity = int(request.POST.get('quantity', 1))
            if quantity < 1:
                raise ValueError
        except (ValueError, TypeError):
            quantity = 1
        
        # ============================================
        # FIX: Check if product has MULTIPLE variants
        # ============================================
        active_variants = product.variants.filter(is_active=True)
        
        if not active_variants.exists():
            return JsonResponse({
                'success': False,
                'message': 'This product is currently unavailable.'
            })
        
        # Check if there are multiple color options
        variant_colors = active_variants.values_list('color', flat=True).distinct()
        has_multiple_variants = len(variant_colors) > 1
        
        # Get selected variant color from POST
        variant_color = request.POST.get('variant_color', '').strip()
        
        if has_multiple_variants:
            # Product has MULTIPLE color options - require selection
            if not variant_color:
                return JsonResponse({
                    'success': False,
                    'message': 'Please select a color variant.'
                })
            
            try:
                variant = active_variants.get(color=variant_color)
            except ProductVariant.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Selected variant is not available.'
                })
        else:
            # Product has ONLY ONE variant (general product)
            # Use the first/only variant automatically
            variant = active_variants.first()
        
        # Check stock
        if not variant.is_in_stock:
            return JsonResponse({
                'success': False,
                'message': f"'{product.name}' is out of stock."
            })
        
        # Check if item already in cart
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            defaults={'quantity': quantity}
        )
        
        if not item_created:
            # Item exists, increment quantity
            new_quantity = cart_item.quantity + quantity
            
            # Check against max quantity per order
            if new_quantity > product.max_quantity_per_order:
                return JsonResponse({
                    'success': False,
                    'message': f"Maximum {product.max_quantity_per_order} items allowed per order."
                })
            
            # Check against stock
            if new_quantity > variant.stock_quantity:
                return JsonResponse({
                    'success': False,
                    'message': f"Only {variant.stock_quantity} items available."
                })
            
            cart_item.quantity = new_quantity
            cart_item.save()
            action = 'updated'
        else:
            # New item - validate quantity
            if quantity > product.max_quantity_per_order:
                cart_item.quantity = product.max_quantity_per_order
                cart_item.save()
            
            if quantity > variant.stock_quantity:
                cart_item.quantity = variant.stock_quantity
                cart_item.save()
            
            action = 'added'
        
        # Remove from wishlist if exists
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            WishlistItem.objects.filter(
                wishlist=wishlist,
                product=product,
                variant=variant
            ).delete()
        except Wishlist.DoesNotExist:
            pass
        
        # Build success message
        if has_multiple_variants:
            message = f"'{product.name}' ({variant.get_color_display()}) {action} in cart!"
        else:
            message = f"'{product.name}' {action} in cart!"
        
        return JsonResponse({
            'success': True,
            'message': message,
            'cart_count': cart.total_items
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()  # For debugging - check console
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again.'
        })


@login_required
def cart_view(request):
    """Display cart with all items"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related(
        'product', 'variant', 'product__category', 'product__brand'
    ).prefetch_related('variant__images')
    
    # Validate each item
    unavailable_items = []
    for item in cart_items:
        # Check product/category/brand status
        if not item.product.is_active or not item.product.category.is_active:
            unavailable_items.append(item)
            continue
        
        if item.product.brand and not item.product.brand.is_active:
            unavailable_items.append(item)
            continue
        
        # Check variant status
        if not item.variant.is_active:
            unavailable_items.append(item)
            continue
        
        # Check stock
        if item.quantity > item.variant.stock_quantity:
            item.quantity = item.variant.stock_quantity
            item.save()
            messages.warning(request, f"Quantity adjusted for '{item.product.name}' due to stock limitation.")
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'unavailable_items': unavailable_items,
    }
    
    return render(request, 'products/cart.html', context)


@login_required
@require_POST
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        action = request.POST.get('action')
        
        # Validate product is still available
        if not cart_item.product.is_active or not cart_item.product.category.is_active:
            return JsonResponse({
                'success': False,
                'message': 'This product is no longer available.'
            })
        
        if not cart_item.variant.is_active:
            return JsonResponse({
                'success': False,
                'message': 'This variant is no longer available.'
            })
        
        if action == 'increment':
            new_quantity = cart_item.quantity + 1
            
            if new_quantity > cart_item.product.max_quantity_per_order:
                return JsonResponse({
                    'success': False,
                    'message': f"Maximum {cart_item.product.max_quantity_per_order} items allowed."
                })
            
            if new_quantity > cart_item.variant.stock_quantity:
                return JsonResponse({
                    'success': False,
                    'message': 'Not enough stock available.'
                })
            
            cart_item.quantity = new_quantity
            cart_item.save()
            
        elif action == 'decrement':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Minimum quantity is 1.'
                })
        
        return JsonResponse({
            'success': True,
            'quantity': cart_item.quantity,
            'item_total': float(cart_item.item_total),
            'cart_subtotal': float(cart_item.cart.subtotal),
            'cart_total': float(cart_item.cart.total)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred.'
        })


@login_required
@require_POST
def remove_cart_item(request, item_id):
    """Remove item from cart"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        product_name = cart_item.product.name
        cart_item.delete()
        
        messages.success(request, f"'{product_name}' removed from cart.")
        return redirect('products:cart_view')
        
    except Exception as e:
        messages.error(request, 'Failed to remove item.')
        return redirect('products:cart_view')


@login_required
@require_POST
def clear_cart(request):
    """Clear all items from cart"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart.items.all().delete()
        messages.success(request, 'Cart cleared successfully.')
    except Cart.DoesNotExist:
        pass
    
    return redirect('products:cart_view')


# ================== CHECKOUT VIEWS ==================

@login_required
def checkout_view(request):
    """Checkout page with address selection"""
    try:
        cart = Cart.objects.get(user=request.user)
        
        if cart.total_items == 0:
            messages.warning(request, 'Your cart is empty.')
            return redirect('products:cart_view')
        
        # Get cart items
        cart_items = cart.items.select_related(
            'product', 'variant', 'product__category'
        ).prefetch_related('variant__images')
        
        # Validate all items
        invalid_items = []
        for item in cart_items:
            if not item.product.is_active or not item.product.category.is_active:
                invalid_items.append(item)
            elif not item.variant.is_active:
                invalid_items.append(item)
            elif item.quantity > item.variant.stock_quantity:
                invalid_items.append(item)
        
        if invalid_items:
            messages.error(request, 'Some items in your cart are unavailable. Please review.')
            return redirect('products:cart_view')
        
        # Get user addresses
        addresses = Address.objects.filter(user=request.user, is_active=True)
        default_address = addresses.filter(is_default=True).first()
        
        if not addresses.exists():
            messages.warning(request, 'Please add a delivery address.')
            return redirect('users:add_address')
        
        # Calculate totals
        subtotal = cart.subtotal
        tax = subtotal * Decimal('0.18')  # 18% GST
        shipping_charge = Decimal('0') if subtotal > 500 else Decimal('50')
        discount = Decimal('0')  # Can be extended with coupon logic
        total = subtotal + tax + shipping_charge - discount
        
        context = {
            'cart': cart,
            'cart_items': cart_items,
            'addresses': addresses,
            'default_address': default_address,
            'subtotal': subtotal,
            'tax': tax,
            'shipping_charge': shipping_charge,
            'discount': discount,
            'total': total,
        }
        
        return render(request, 'products/checkout.html', context)
        
    except Cart.DoesNotExist:
        messages.warning(request, 'Your cart is empty.')
        return redirect('products:cart_view')


@login_required
@require_POST
def place_order(request):
    """Place order (COD)"""
    try:
        cart = Cart.objects.get(user=request.user)
        
        if cart.total_items == 0:
            messages.error(request, 'Your cart is empty.')
            return redirect('products:cart_view')
        
        # Get selected address
        address_id = request.POST.get('address_id')
        if not address_id:
            messages.error(request, 'Please select a delivery address.')
            return redirect('products:checkout_view')
        
        address = get_object_or_404(Address, id=address_id, user=request.user, is_active=True)
        
        # Validate cart items again
        cart_items = cart.items.select_related('product', 'variant')
        for item in cart_items:
            if not item.product.is_active or not item.product.category.is_active:
                messages.error(request, f"'{item.product.name}' is no longer available.")
                return redirect('products:cart_view')
            
            if not item.variant.is_active or item.variant.stock_quantity < item.quantity:
                messages.error(request, f"'{item.product.name}' stock insufficient.")
                return redirect('products:cart_view')
        
        # Calculate totals
        subtotal = cart.subtotal
        tax = subtotal * Decimal('0.18')
        shipping_charge = Decimal('0') if subtotal > 500 else Decimal('50')
        discount = Decimal('0')
        total = subtotal + tax + shipping_charge - discount
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            shipping_full_name=address.full_name,
            shipping_phone=address.phone,
            shipping_line1=address.address_line1,
            shipping_line2=address.address_line2,
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_postal_code=address.postal_code,
            shipping_country=address.country,
            subtotal=subtotal,
            tax=tax,
            shipping_charge=shipping_charge,
            discount=discount,
            total=total,
            payment_method='cod',
            status='pending',
            notes=request.POST.get('notes', '')
        )
        
        # Create order items and reduce stock
        for item in cart_items:
            # Get primary variant image
            variant_image = item.variant.images.first()
            
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                product_name=item.product.name,
                product_image=variant_image.image if variant_image else None,
                variant_name=item.variant.get_color_display(),
                price=item.variant.price,
                quantity=item.quantity,
                item_total=item.item_total
            )
            
            # Reduce stock
            item.variant.stock_quantity -= item.quantity
            item.variant.save()
        
        # Clear cart
        cart.items.all().delete()
        
        messages.success(request, f'Order placed successfully! Order ID: {order.order_id}')
        return redirect('products:order_success', order_id=order.order_id)
        
    except Exception as e:
        messages.error(request, 'Failed to place order. Please try again.')
        return redirect('products:checkout_view')


@login_required
def order_success(request, order_id):
    """Order success page"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    context = {
        'order': order,
    }
    
    return render(request, 'products/order_success.html', context)


# ================== ORDER MANAGEMENT VIEWS ==================

@login_required
def order_list(request):
    """List all user orders with search"""
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    
    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        orders = orders.filter(
            Q(order_id__icontains=search_query) |
            Q(items__product_name__icontains=search_query)
        ).distinct()
    
    context = {
        'orders': orders,
        'search_query': search_query,
    }
    
    return render(request, 'products/order_list.html', context)


@login_required
def order_detail(request, order_id):
    """Order detail page"""
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product', 'items__variant'),
        order_id=order_id,
        user=request.user
    )
    
    context = {
        'order': order,
    }
    
    return render(request, 'products/order_detail.html', context)


@login_required
@require_POST
def cancel_order(request, order_id):
    """Cancel entire order"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    if not order.can_cancel:
        messages.error(request, 'This order cannot be cancelled.')
        return redirect('products:order_detail', order_id=order_id)
    
    reason = request.POST.get('reason', '')
    
    # Restore stock for all items
    for item in order.items.filter(status='active'):
        if item.variant:
            item.variant.stock_quantity += item.quantity
            item.variant.save()
        
        item.status = 'cancelled'
        item.save()
    
    # Update order status
    order.status = 'cancelled'
    order.save()
    
    # Create cancellation record
    OrderCancellation.objects.create(
        order=order,
        reason=reason,
        cancelled_by=request.user
    )
    
    messages.success(request, f'Order {order.order_id} cancelled successfully.')
    return redirect('products:order_detail', order_id=order_id)


@login_required
@require_POST
def cancel_order_item(request, item_id):
    """Cancel individual order item"""
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    
    if item.order.status not in ['pending', 'confirmed']:
        messages.error(request, 'This item cannot be cancelled.')
        return redirect('products:order_detail', order_id=item.order.order_id)
    
    if item.status != 'active':
        messages.error(request, 'This item is already cancelled or returned.')
        return redirect('products:order_detail', order_id=item.order.order_id)
    
    reason = request.POST.get('reason', '')
    
    # Restore stock
    if item.variant:
        item.variant.stock_quantity += item.quantity
        item.variant.save()
    
    item.status = 'cancelled'
    item.save()
    
    # Create cancellation record
    OrderCancellation.objects.create(
        order_item=item,
        reason=reason,
        cancelled_by=request.user
    )
    
    # Check if all items are cancelled
    if not item.order.items.filter(status='active').exists():
        item.order.status = 'cancelled'
        item.order.save()
    
    messages.success(request, 'Item cancelled successfully.')
    return redirect('products:order_detail', order_id=item.order.order_id)


@login_required
@require_POST
def return_order(request, order_id):
    """Request order return"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    if not order.can_return:
        messages.error(request, 'This order cannot be returned.')
        return redirect('products:order_detail', order_id=order_id)
    
    reason = request.POST.get('reason', '').strip()
    
    if not reason:
        messages.error(request, 'Please provide a reason for return.')
        return redirect('products:order_detail', order_id=order_id)
    
    # Create return request
    OrderReturn.objects.create(
        order=order,
        reason=reason,
        requested_by=request.user
    )
    
    order.status = 'returned'
    order.save()
    
    messages.success(request, 'Return request submitted successfully.')
    return redirect('products:order_detail', order_id=order_id)


@login_required
def download_invoice(request, order_id):
    """Download order invoice as PDF"""
    from django.template.loader import render_to_string
    from weasyprint import HTML
    import tempfile
    
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        order_id=order_id,
        user=request.user
    )
    
    # Render HTML template
    html_string = render_to_string('products/invoice_pdf.html', {
        'order': order,
        'company_name': 'Your Company Name',
        'company_address': 'Your Company Address',
    })
    
    # Generate PDF
    html = HTML(string=html_string)
    result = html.write_pdf()
    
    # Create response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_id}.pdf"'
    response.write(result)
    
    return response

#|===========WISHLIST & WISHLIST MANAGEMENT=============|


@login_required
def wishlist_view(request):
    """Display user's wishlist"""
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    wishlist_items = wishlist.items.select_related(
        'product', 'variant', 'product__category', 'product__brand'
    ).prefetch_related('variant__images', 'product__images')
    
    # Check availability of each item
    for item in wishlist_items:
        item.is_available = (
            item.product.is_active and 
            item.product.category.is_active and
            item.variant.is_active and
            item.variant.is_in_stock
        )
    
    context = {
        'wishlist': wishlist,
        'wishlist_items': wishlist_items,
    }
    
    return render(request, 'products/wishlist.html', context)


@login_required
@require_POST
def add_to_wishlist(request, pk):
    """Add product variant to wishlist"""
    try:
        product = get_object_or_404(Product, pk=pk)
        
        # Validate product availability
        if not product.is_active or not product.category.is_active:
            return JsonResponse({
                'success': False,
                'message': f"'{product.name}' is currently unavailable."
            })
        
        # Get or create wishlist
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        
        # Get variant color from POST
        variant_color = request.POST.get('variant_color', '').strip()
        
        # Get all active variants
        active_variants = product.variants.filter(is_active=True)
        
        if not active_variants.exists():
            return JsonResponse({
                'success': False,
                'message': 'This product is currently unavailable.'
            })
        
        # Check if product has multiple colors
        unique_colors = active_variants.values_list('color', flat=True).distinct()
        has_multiple_variants = len(unique_colors) > 1
        
        # Get the variant
        if has_multiple_variants:
            # Product has multiple colors - require selection
            if not variant_color:
                return JsonResponse({
                    'success': False,
                    'message': 'Please select a color variant.'
                })
            
            try:
                variant = active_variants.get(color=variant_color)
            except ProductVariant.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Selected variant is not available.'
                })
        else:
            # Product has only one color - auto-select
            variant = active_variants.first()
        
        # Check if already in wishlist
        existing_item = WishlistItem.objects.filter(
            wishlist=wishlist,
            product=product,
            variant=variant
        ).first()
        
        if existing_item:
            return JsonResponse({
                'success': False,
                'message': 'This item is already in your wishlist.',
                'in_wishlist': True,
                'wishlist_count': wishlist.total_items
            })
        
        # Add to wishlist
        WishlistItem.objects.create(
            wishlist=wishlist,
            product=product,
            variant=variant
        )
        
        return JsonResponse({
            'success': True,
            'message': f"'{product.name}' added to wishlist!",
            'wishlist_count': wishlist.total_items,
            'in_wishlist': True
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()  # For debugging
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again.'
        })


@login_required
@require_POST
def remove_from_wishlist(request, item_id):
    """Remove item from wishlist"""
    try:
        wishlist_item = get_object_or_404(
            WishlistItem, 
            id=item_id, 
            wishlist__user=request.user
        )
        
        product_name = wishlist_item.product.name
        wishlist_item.delete()
        
        messages.success(request, f"'{product_name}' removed from wishlist.")
        return redirect('products:wishlist_view')
        
    except Exception as e:
        messages.error(request, 'Failed to remove item.')
        return redirect('products:wishlist_view')


@login_required
@require_POST
def clear_wishlist(request):
    """Clear all items from wishlist"""
    try:
        wishlist = Wishlist.objects.get(user=request.user)
        wishlist.items.all().delete()
        messages.success(request, 'Wishlist cleared successfully.')
    except Wishlist.DoesNotExist:
        pass
    
    return redirect('products:wishlist_view')


@login_required
@require_POST
def move_to_cart_from_wishlist(request, item_id):
    """Move wishlist item to cart"""
    try:
        wishlist_item = get_object_or_404(
            WishlistItem,
            id=item_id,
            wishlist__user=request.user
        )
        
        # Check product availability
        if not wishlist_item.product.is_active or not wishlist_item.product.category.is_active:
            messages.error(request, 'This product is no longer available.')
            wishlist_item.delete()
            return redirect('products:wishlist_view')
        
        if not wishlist_item.variant.is_active or not wishlist_item.variant.is_in_stock:
            messages.error(request, 'This variant is out of stock.')
            return redirect('products:wishlist_view')
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Check if already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=wishlist_item.product,
            variant=wishlist_item.variant,
            defaults={'quantity': 1}
        )
        
        if not created:
            # Item exists, increment quantity if possible
            if cart_item.quantity < wishlist_item.product.max_quantity_per_order and \
               cart_item.quantity < wishlist_item.variant.stock_quantity:
                cart_item.quantity += 1
                cart_item.save()
        
        # Remove from wishlist
        product_name = wishlist_item.product.name
        wishlist_item.delete()
        
        messages.success(request, f"'{product_name}' moved to cart!")
        return redirect('products:wishlist_view')
        
    except Exception as e:
        messages.error(request, 'Failed to move item to cart.')
        return redirect('products:wishlist_view')


@login_required
@require_GET
def check_wishlist_status(request, pk):
    """Check if product is in wishlist (AJAX endpoint)"""
    try:
        product = get_object_or_404(Product, pk=pk)
        variant_color = request.GET.get('variant_color', '').strip()
        
        wishlist = Wishlist.objects.filter(user=request.user).first()
        if not wishlist:
            return JsonResponse({
                'in_wishlist': False,
                'wishlist_count': 0
            })
        
        # Get active variants
        active_variants = product.variants.filter(is_active=True)
        
        if not active_variants.exists():
            return JsonResponse({
                'in_wishlist': False,
                'wishlist_count': wishlist.total_items
            })
        
        # Determine which variant to check
        if variant_color:
            variant = active_variants.filter(color=variant_color).first()
        else:
            # If no color specified, use first variant
            variant = active_variants.first()
        
        if not variant:
            return JsonResponse({
                'in_wishlist': False,
                'wishlist_count': wishlist.total_items
            })
        
        # Check if exists in wishlist
        exists = WishlistItem.objects.filter(
            wishlist=wishlist,
            product=product,
            variant=variant
        ).exists()
        
        return JsonResponse({
            'in_wishlist': exists,
            'wishlist_count': wishlist.total_items
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()  # For debugging
        return JsonResponse({
            'in_wishlist': False,
            'wishlist_count': 0
        })








# @login_required
# def wishlist_view(request):
#     """Display user's wishlist"""
#     wishlist, created = Wishlist.objects.get_or_create(user=request.user)
#     wishlist_items = wishlist.items.select_related(
#         'product', 'variant', 'product__category', 'product__brand'
#     ).prefetch_related('variant__images', 'product__images')
    
#     # Check availability of each item
#     for item in wishlist_items:
#         item.is_available = (
#             item.product.is_active and 
#             item.product.category.is_active and
#             item.variant.is_active and
#             item.variant.is_in_stock
#         )
    
#     context = {
#         'wishlist': wishlist,
#         'wishlist_items': wishlist_items,
#     }
    
#     return render(request, 'products/wishlist.html', context)


# @login_required
# def add_to_wishlist(request, pk):
#     """Add product variant to wishlist - FIXED to handle both POST and GET"""
#     if request.method != 'POST':
#         messages.error(request, 'Invalid request method.')
#         return redirect('products:product_detail', pk=pk)
    
#     try:
#         product = get_object_or_404(Product, pk=pk)
        
#         # Validate product availability
#         if not product.is_active or not product.category.is_active:
#             if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#                 return JsonResponse({
#                     'success': False,
#                     'message': f"'{product.name}' is currently unavailable."
#                 })
#             messages.error(request, f"'{product.name}' is currently unavailable.")
#             return redirect('products:product_detail', pk=pk)
        
#         # Get variant color
#         variant_color = request.POST.get('variant_color', '').strip()
        
#         # Get or create wishlist
#         wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        
#         # Get variant
#         variant = None
#         if variant_color:
#             try:
#                 variant = product.variants.get(color=variant_color, is_active=True)
#             except ProductVariant.DoesNotExist:
#                 if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#                     return JsonResponse({
#                         'success': False,
#                         'message': 'Selected variant is not available.'
#                     })
#                 messages.error(request, 'Selected variant is not available.')
#                 return redirect('products:product_detail', pk=pk)
#         else:
#             # If no variant selected, use first available variant
#             variant = product.variants.filter(is_active=True).first()
#             if not variant:
#                 if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#                     return JsonResponse({
#                         'success': False,
#                         'message': 'No available variants.'
#                     })
#                 messages.error(request, 'No available variants.')
#                 return redirect('products:product_detail', pk=pk)
        
#         # Check if already in wishlist
#         existing_item = WishlistItem.objects.filter(
#             wishlist=wishlist,
#             product=product,
#             variant=variant
#         ).first()
        
#         if existing_item:
#             # Remove from wishlist (toggle behavior)
#             existing_item.delete()
#             if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#                 return JsonResponse({
#                     'success': True,
#                     'message': f"'{product.name}' removed from wishlist.",
#                     'wishlist_count': wishlist.total_items,
#                     'in_wishlist': False
#                 })
#             messages.success(request, f"'{product.name}' removed from wishlist.")
#             return redirect('products:product_detail', pk=pk)
        
#         # Add to wishlist
#         WishlistItem.objects.create(
#             wishlist=wishlist,
#             product=product,
#             variant=variant
#         )
        
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             return JsonResponse({
#                 'success': True,
#                 'message': f"'{product.name}' added to wishlist!",
#                 'wishlist_count': wishlist.total_items,
#                 'in_wishlist': True
#             })
#         messages.success(request, f"'{product.name}' added to wishlist!")
#         return redirect('products:product_detail', pk=pk)
        
#     except Exception as e:
#         print(f"Error in add_to_wishlist: {e}")  # Debug print
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             return JsonResponse({
#                 'success': False,
#                 'message': 'An error occurred. Please try again.'
#             })
#         messages.error(request, 'An error occurred. Please try again.')
#         return redirect('products:product_detail', pk=pk)
        
# @login_required
# @require_POST
# def remove_from_wishlist(request, item_id):
#     """Remove item from wishlist"""
#     try:
#         wishlist_item = get_object_or_404(
#             WishlistItem, 
#             id=item_id, 
#             wishlist__user=request.user
#         )
        
#         product_name = wishlist_item.product.name
#         wishlist_item.delete()
        
#         messages.success(request, f"'{product_name}' removed from wishlist.")
#         return redirect('products:wishlist_view')
        
#     except Exception as e:
#         messages.error(request, 'Failed to remove item.')
#         return redirect('products:wishlist_view')


# @login_required
# @require_POST
# def clear_wishlist(request):
#     """Clear all items from wishlist"""
#     try:
#         wishlist = Wishlist.objects.get(user=request.user)
#         wishlist.items.all().delete()
#         messages.success(request, 'Wishlist cleared successfully.')
#     except Wishlist.DoesNotExist:
#         pass
    
#     return redirect('products:wishlist_view')


# @login_required
# @require_POST
# def move_to_cart_from_wishlist(request, item_id):
#     """Move wishlist item to cart"""
#     try:
#         wishlist_item = get_object_or_404(
#             WishlistItem,
#             id=item_id,
#             wishlist__user=request.user
#         )
        
#         # Check product availability
#         if not wishlist_item.product.is_active or not wishlist_item.product.category.is_active:
#             messages.error(request, 'This product is no longer available.')
#             wishlist_item.delete()
#             return redirect('products:wishlist_view')
        
#         if not wishlist_item.variant.is_active or not wishlist_item.variant.is_in_stock:
#             messages.error(request, 'This variant is out of stock.')
#             return redirect('products:wishlist_view')
        
#         # Get or create cart
#         cart, created = Cart.objects.get_or_create(user=request.user)
        
#         # Check if already in cart
#         cart_item, created = CartItem.objects.get_or_create(
#             cart=cart,
#             product=wishlist_item.product,
#             variant=wishlist_item.variant,
#             defaults={'quantity': 1}
#         )
        
#         if not created:
#             # Item exists, increment quantity if possible
#             if cart_item.quantity < wishlist_item.product.max_quantity_per_order and \
#                cart_item.quantity < wishlist_item.variant.stock_quantity:
#                 cart_item.quantity += 1
#                 cart_item.save()
        
#         # Remove from wishlist
#         product_name = wishlist_item.product.name
#         wishlist_item.delete()
        
#         messages.success(request, f"'{product_name}' moved to cart!")
#         return redirect('products:wishlist_view')
        
#     except Exception as e:
#         messages.error(request, 'Failed to move item to cart.')
#         return redirect('products:wishlist_view')


# @login_required
# @require_GET
# def check_wishlist_status(request, pk):
#     """Check if product is in wishlist (AJAX endpoint)"""
#     try:
#         product = get_object_or_404(Product, pk=pk)
#         variant_color = request.GET.get('variant_color')
        
#         wishlist = Wishlist.objects.filter(user=request.user).first()
#         if not wishlist:
#             return JsonResponse({'in_wishlist': False})
        
#         variant = None
#         if variant_color:
#             variant = product.variants.filter(color=variant_color).first()
        
#         exists = WishlistItem.objects.filter(
#             wishlist=wishlist,
#             product=product,
#             variant=variant
#         ).exists()
        
#         return JsonResponse({
#             'in_wishlist': exists,
#             'wishlist_count': wishlist.total_items
#         })
        
#     except Exception as e:
#         return JsonResponse({'in_wishlist': False})



