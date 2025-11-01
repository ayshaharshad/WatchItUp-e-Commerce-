from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Avg, F, Min, Max
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import razorpay
import hmac
import hashlib

from .models import (
    Product, Category, ProductVariant, ProductReview, Coupon, CouponUsage,
    Cart, CartItem, Order, OrderItem, RazorpayPayment,
    OrderCancellation, OrderReturn, Wishlist, WishlistItem
)
from users.models import Address

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

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



# ================== COUPON VIEWS ==================

@login_required
@require_POST
def apply_coupon(request):
    """Apply coupon during checkout with comprehensive validation"""
    coupon_code = request.POST.get('coupon_code', '').strip().upper()
    
    if not coupon_code:
        return JsonResponse({
            'success': False,
            'message': 'Please enter a coupon code.'
        })
    
    try:
        # Get cart
        cart = Cart.objects.get(user=request.user)
        
        if cart.total_items == 0:
            return JsonResponse({
                'success': False,
                'message': 'Your cart is empty.'
            })
        
        # Get coupon
        coupon = Coupon.objects.get(code=coupon_code)
        
        # Check if user can use this coupon
        can_use, message = coupon.can_use(request.user)
        if not can_use:
            return JsonResponse({
                'success': False,
                'message': message
            })
        
        # Check minimum amount
        subtotal = cart.subtotal
        if subtotal < coupon.minimum_amount:
            return JsonResponse({
                'success': False,
                'message': f'Minimum order amount ₹{coupon.minimum_amount} required.'
            })
        
        # Calculate discount
        discount_amount = coupon.calculate_discount(subtotal)
        
        # Store in session
        request.session['applied_coupon_code'] = coupon.code
        request.session['coupon_discount'] = float(discount_amount)
        
        # Calculate new totals
        tax = subtotal * Decimal('0.18')
        shipping = Decimal('0') if subtotal > 500 else Decimal('50')
        total = subtotal + tax + shipping - discount_amount
        
        return JsonResponse({
            'success': True,
            'message': f'Coupon "{coupon.code}" applied successfully!',
            'discount_amount': float(discount_amount),
            'coupon_code': coupon.code,
            'discount_type': coupon.discount_type,
            'discount_value': float(coupon.discount_value),
            'subtotal': float(subtotal),
            'tax': float(tax),
            'shipping': float(shipping),
            'total': float(total)
        })
        
    except Coupon.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Invalid coupon code.'
        })
    except Cart.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cart not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again.'
        })


@login_required
@require_POST
def remove_coupon(request):
    """Remove applied coupon"""
    try:
        # Clear session
        request.session.pop('applied_coupon_code', None)
        request.session.pop('coupon_discount', None)
        
        # Recalculate totals
        cart = Cart.objects.get(user=request.user)
        subtotal = cart.subtotal
        tax = subtotal * Decimal('0.18')
        shipping = Decimal('0') if subtotal > 500 else Decimal('50')
        total = subtotal + tax + shipping
        
        return JsonResponse({
            'success': True,
            'message': 'Coupon removed successfully.',
            'subtotal': float(subtotal),
            'tax': float(tax),
            'shipping': float(shipping),
            'total': float(total)
        })
        
    except Cart.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cart not found.'
        })

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
        # FIX: Handle products WITH and WITHOUT variants
        # ============================================
        active_variants = product.variants.filter(is_active=True)
        
        # CASE 1: PRODUCT WITHOUT VARIANTS (uses base product.stock)
        if not active_variants.exists():
            # Check base product stock
            if product.stock <= 0:
                return JsonResponse({
                    'success': False,
                    'message': f"'{product.name}' is out of stock."
                })
            
            # Check if item already in cart (variant=None for base products)
            cart_item, item_created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                variant=None,  # No variant for base products
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
                
                # Check against base product stock
                if new_quantity > product.stock:
                    return JsonResponse({
                        'success': False,
                        'message': f"Only {product.stock} items available."
                    })
                
                cart_item.quantity = new_quantity
                cart_item.save()
                action = 'updated'
            else:
                # New item - validate quantity
                if quantity > product.max_quantity_per_order:
                    cart_item.quantity = product.max_quantity_per_order
                    cart_item.save()
                
                if quantity > product.stock:
                    cart_item.quantity = product.stock
                    cart_item.save()
                
                action = 'added'
            
            # Remove from wishlist if exists (no variant)
            try:
                wishlist = Wishlist.objects.get(user=request.user)
                WishlistItem.objects.filter(
                    wishlist=wishlist,
                    product=product,
                    variant=None
                ).delete()
            except Wishlist.DoesNotExist:
                pass
            
            # Success message for product without variants
            message = f"'{product.name}' {action} in cart!"
            
            return JsonResponse({
                'success': True,
                'message': message,
                'cart_count': cart.total_items
            })
        
        # CASE 2: PRODUCT WITH VARIANTS
        
        # Check if there are multiple color options
        variant_colors = active_variants.values_list('color', flat=True).distinct()
        has_multiple_variants = len(variant_colors) > 1
        
        # Get selected variant color from POST
        variant_color = request.POST.get('variant_color', '').strip()
        
        if has_multiple_variants:
            # Product has MULTIPLE color options - require selection
            if not variant_color or variant_color == 'no-variant':
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
            # Product has ONLY ONE variant - auto-select it
            if variant_color and variant_color != 'no-variant':
                # User explicitly selected the variant
                try:
                    variant = active_variants.get(color=variant_color)
                except ProductVariant.DoesNotExist:
                    variant = active_variants.first()
            else:
                # Auto-select the only variant
                variant = active_variants.first()
        
        # Check variant stock
        if not variant.is_in_stock:
            return JsonResponse({
                'success': False,
                'message': f"'{product.name}' ({variant.get_color_display()}) is out of stock."
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
            
            # Check against variant stock
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
        
        # Check variant status (only if variant exists)
        if item.variant and not item.variant.is_active:
            unavailable_items.append(item)
            continue
        
        # Check stock - handle both products with and without variants
        if item.variant:
            # Product has variant - check variant stock
            if item.quantity > item.variant.stock_quantity:
                item.quantity = item.variant.stock_quantity
                item.save()
                messages.warning(request, f"Quantity adjusted for '{item.product.name}' due to stock limitation.")
        else:
            # Product without variant - check base product stock
            if item.quantity > item.product.stock:
                item.quantity = item.product.stock
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
    """Update cart item quantity with AJAX support"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        action = request.POST.get('action')

        # Validate product is still available
        if not cart_item.product.is_active or not cart_item.product.category.is_active:
            return JsonResponse({
                'success': False,
                'message': 'This product is no longer available.'
            })

        # Check variant status (only if variant exists)
        if cart_item.variant and not cart_item.variant.is_active:
            return JsonResponse({
                'success': False,
                'message': 'This variant is no longer available.'
            })

        # Get available stock (variant or base product)
        available_stock = cart_item.variant.stock_quantity if cart_item.variant else cart_item.product.stock

        if action == 'increment':
            new_quantity = cart_item.quantity + 1

            if new_quantity > cart_item.product.max_quantity_per_order:
                return JsonResponse({
                    'success': False,
                    'message': f"Maximum {cart_item.product.max_quantity_per_order} items allowed."
                })

            if new_quantity > available_stock:
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

        # Calculate totals
        cart = cart_item.cart
        subtotal = float(cart.subtotal)
        tax = subtotal * 0.18
        shipping = 0 if subtotal > 500 else 50
        total = subtotal + tax + shipping

        return JsonResponse({
            'success': True,
            'quantity': cart_item.quantity,
            'item_total': float(cart_item.item_total),
            'cart_subtotal': subtotal,
            'cart_tax': round(tax, 2),
            'cart_shipping': shipping,
            'cart_total': round(total, 2),
            'cart_items_count': cart.total_items
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred.'
        })



@login_required
@require_POST
def remove_cart_item(request, item_id):
    """Remove item from cart with AJAX support"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        product_name = cart_item.product.name
        cart = cart_item.cart
        
        cart_item.delete()

        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Calculate new totals
            subtotal = float(cart.subtotal)
            tax = subtotal * 0.18
            shipping = 0 if subtotal > 500 else 50
            total = subtotal + tax + shipping
            
            return JsonResponse({
                'success': True,
                'message': f"'{product_name}' removed from cart.",
                'cart_subtotal': subtotal,
                'cart_tax': round(tax, 2),
                'cart_shipping': shipping,
                'cart_total': round(total, 2),
                'cart_items_count': cart.total_items,
                'cart_empty': cart.total_items == 0
            })
        else:
            # Regular form submission
            messages.success(request, f"'{product_name}' removed from cart.")
            return redirect('products:cart_view')

    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Failed to remove item.'
            })
        else:
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


# ================== CHECKOUT & PAYMENT VIEWS ==================

@login_required
def checkout_view(request):
    """Checkout page with address selection and coupon support"""
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
                continue
            
            if item.variant and not item.variant.is_active:
                invalid_items.append(item)
                continue
            
            if item.variant:
                if item.quantity > item.variant.stock_quantity:
                    invalid_items.append(item)
            else:
                if item.quantity > item.product.stock:
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
        tax = subtotal * Decimal('0.18')
        shipping_charge = Decimal('0') if subtotal > 500 else Decimal('50')
        
        # Get applied coupon discount
        coupon_discount = Decimal('0')
        applied_coupon = None
        coupon_code = request.session.get('applied_coupon_code')
        
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code)
                can_use, _ = coupon.can_use(request.user)
                
                if can_use and subtotal >= coupon.minimum_amount:
                    coupon_discount = Decimal(str(coupon.calculate_discount(subtotal)))
                    applied_coupon = coupon
                else:
                    # Invalid coupon, clear session
                    request.session.pop('applied_coupon_code', None)
                    request.session.pop('coupon_discount', None)
            except Coupon.DoesNotExist:
                request.session.pop('applied_coupon_code', None)
                request.session.pop('coupon_discount', None)
        
        total = subtotal + tax + shipping_charge - coupon_discount
        
        # Get available coupons
        available_coupons = Coupon.objects.filter(
            is_active=True,
            valid_from__lte=timezone.now(),
            valid_to__gte=timezone.now(),
            minimum_amount__lte=subtotal
        ).filter(
            Q(usage_limit__isnull=True) | Q(usage_limit__gt=F('used_count'))
        )[:5]
        
        context = {
            'cart': cart,
            'cart_items': cart_items,
            'addresses': addresses,
            'default_address': default_address,
            'subtotal': subtotal,
            'tax': tax,
            'shipping_charge': shipping_charge,
            'coupon_discount': coupon_discount,
            'applied_coupon': applied_coupon,
            'total': total,
            'available_coupons': available_coupons,
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        }
        
        return render(request, 'products/checkout.html', context)
        
    except Cart.DoesNotExist:
        messages.warning(request, 'Your cart is empty.')
        return redirect('products:cart_view')


@login_required
@require_POST
def create_razorpay_order(request):
    """Create Razorpay order for payment"""
    try:
        cart = Cart.objects.get(user=request.user)
        
        if cart.total_items == 0:
            return JsonResponse({
                'success': False,
                'message': 'Your cart is empty.'
            })
        
        # Get address
        address_id = request.POST.get('address_id')
        if not address_id:
            return JsonResponse({
                'success': False,
                'message': 'Please select a delivery address.'
            })
        
        address = get_object_or_404(Address, id=address_id, user=request.user, is_active=True)
        
        # Calculate totals
        subtotal = cart.subtotal
        tax = subtotal * Decimal('0.18')
        shipping_charge = Decimal('0') if subtotal > 500 else Decimal('50')
        
        # Apply coupon if present
        coupon = None
        coupon_discount = Decimal('0')
        coupon_code = request.session.get('applied_coupon_code')
        
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code)
                can_use, _ = coupon.can_use(request.user)
                if can_use:
                    coupon_discount = Decimal(str(coupon.calculate_discount(subtotal)))
            except Coupon.DoesNotExist:
                pass
        
        total = subtotal + tax + shipping_charge - coupon_discount
        
        # Create order in database (pending state)
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
            discount=coupon_discount,
            coupon=coupon,
            total=total,
            payment_method='razorpay',
            payment_status='pending',
            status='pending',
            notes=request.POST.get('notes', '')
        )
        
        # Create order items
        cart_items = cart.items.select_related('product', 'variant')
        for item in cart_items:
            if item.variant:
                item_image = item.variant.images.first()
                variant_name = item.variant.get_color_display()
                item_price = item.variant.price
            else:
                item_image = item.product.images.first()
                variant_name = ''
                item_price = item.product.base_price
            
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                product_name=item.product.name,
                product_image=item_image.image if item_image else None,
                variant_name=variant_name,
                price=item_price,
                quantity=item.quantity,
                item_total=item.item_total
            )
        
        # Create Razorpay order
        amount_in_paise = int(total * 100)  # Convert to paise
        
        razorpay_order = razorpay_client.order.create({
            'amount': amount_in_paise,
            'currency': 'INR',
            'payment_capture': '1',
            'notes': {
                'order_id': order.order_id,
                'user_id': str(request.user.id)
            }
        })
        
        # Save Razorpay payment details
        RazorpayPayment.objects.create(
            order=order,
            razorpay_order_id=razorpay_order['id'],
            amount=total,
            status='created'
        )
        
        return JsonResponse({
            'success': True,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': amount_in_paise,
            'currency': 'INR',
            'order_id': order.order_id,
            'user_name': request.user.get_full_name() or request.user.username,
            'user_email': request.user.email,
            'user_phone': address.phone
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': 'Failed to create payment order. Please try again.'
        })


@csrf_exempt
@require_POST
def verify_razorpay_payment(request):
    """Verify Razorpay payment signature"""
    try:
        data = json.loads(request.body)
        
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')
        
        # Get payment record
        payment = RazorpayPayment.objects.get(razorpay_order_id=razorpay_order_id)
        order = payment.order
        
        # Verify signature
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode('utf-8'),
            f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature == razorpay_signature:
            # Payment successful
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = 'paid'
            payment.save()
            
            order.payment_status = 'completed'
            order.status = 'confirmed'
            order.save()
            
            # Reduce stock
            for item in order.items.all():
                if item.variant:
                    item.variant.stock_quantity -= item.quantity
                    item.variant.save()
                else:
                    item.product.stock -= item.quantity
                    item.product.save()
            
            # Record coupon usage
            if order.coupon:
                CouponUsage.objects.create(
                    coupon=order.coupon,
                    user=request.user,
                    order=order,
                    discount_amount=order.discount
                )
                order.coupon.used_count += 1
                order.coupon.save()
            
            # Clear cart and session
            try:
                cart = Cart.objects.get(user=request.user)
                cart.items.all().delete()
            except Cart.DoesNotExist:
                pass
            
            request.session.pop('applied_coupon_code', None)
            request.session.pop('coupon_discount', None)
            
            return JsonResponse({
                'success': True,
                'order_id': order.order_id,
                'redirect_url': f'/products/order/success/{order.order_id}/'
            })
        else:
            # Signature verification failed
            payment.status = 'failed'
            payment.save()
            
            order.payment_status = 'failed'
            order.save()
            
            return JsonResponse({
                'success': False,
                'message': 'Payment verification failed',
                'redirect_url': f'/products/order/failure/{order.order_id}/'
            })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': 'Payment verification error'
        })


@login_required
@require_POST
def place_order_cod(request):
    """Place order with Cash on Delivery"""
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
        
        # Validate cart items
        cart_items = cart.items.select_related('product', 'variant')
        for item in cart_items:
            if not item.product.is_active or not item.product.category.is_active:
                messages.error(request, f"'{item.product.name}' is no longer available.")
                return redirect('products:cart_view')
            
            if item.variant:
                if not item.variant.is_active or item.variant.stock_quantity < item.quantity:
                    messages.error(request, f"'{item.product.name}' stock insufficient.")
                    return redirect('products:cart_view')
            else:
                if item.product.stock < item.quantity:
                    messages.error(request, f"'{item.product.name}' stock insufficient.")
                    return redirect('products:cart_view')
        
        # Calculate totals
        subtotal = cart.subtotal
        tax = subtotal * Decimal('0.18')
        shipping_charge = Decimal('0') if subtotal > 500 else Decimal('50')
        
        # Apply coupon if present
        coupon = None
        coupon_discount = Decimal('0')
        coupon_code = request.session.get('applied_coupon_code')
        
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code)
                can_use, _ = coupon.can_use(request.user)
                if can_use:
                    coupon_discount = Decimal(str(coupon.calculate_discount(subtotal)))
            except Coupon.DoesNotExist:
                pass
        
        total = subtotal + tax + shipping_charge - coupon_discount
        
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
            discount=coupon_discount,
            coupon=coupon,
            total=total,
            payment_method='cod',
            payment_status='pending',
            status='pending',
            notes=request.POST.get('notes', '')
        )
        
        # Create order items and reduce stock
        for item in cart_items:
            if item.variant:
                item_image = item.variant.images.first()
                variant_name = item.variant.get_color_display()
                item_price = item.variant.price
            else:
                item_image = item.product.images.first()
                variant_name = ''
                item_price = item.product.base_price
            
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                product_name=item.product.name,
                product_image=item_image.image if item_image else None,
                variant_name=variant_name,
                price=item_price,
                quantity=item.quantity,
                item_total=item.item_total
            )
            
            # Reduce stock
            if item.variant:
                item.variant.stock_quantity -= item.quantity
                item.variant.save()
            else:
                item.product.stock -= item.quantity
                item.product.save()
        
        # Record coupon usage
        if coupon:
            CouponUsage.objects.create(
                coupon=coupon,
                user=request.user,
                order=order,
                discount_amount=coupon_discount
            )
            coupon.used_count += 1
            coupon.save()
        
        # Clear cart and session
        cart.items.all().delete()
        request.session.pop('applied_coupon_code', None)
        request.session.pop('coupon_discount', None)
        
        messages.success(request, f'Order placed successfully! Order ID: {order.order_id}')
        return redirect('products:order_success', order_id=order.order_id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
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


@login_required
def order_failure(request, order_id):
    """Order payment failure page"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    context = {
        'order': order,
    }
    
    return render(request, 'products/order_failure.html', context)


# ================== ORDER MANAGEMENT VIEWS ==================

@login_required
def order_list(request):
    """List all user orders with search and filters"""
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    
    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        orders = orders.filter(
            Q(order_id__icontains=search_query) |
            Q(items__product_name__icontains=search_query)
        ).distinct()
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'orders': page_obj.object_list,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': Order.STATUS_CHOICES,
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
    """Cancel entire order with reason"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    if not order.can_cancel:
        return JsonResponse({
            'success': False,
            'message': 'This order cannot be cancelled.'
        })
    
    reason = request.POST.get('reason', '').strip()
    
    if not reason:
        return JsonResponse({
            'success': False,
            'message': 'Please provide a cancellation reason.'
        })
    
    # Restore stock for all active items
    for item in order.items.filter(status='active'):
        if item.variant:
            item.variant.stock_quantity += item.quantity
            item.variant.save()
        else:
            item.product.stock += item.quantity
            item.product.save()
        
        item.status = 'cancelled'
        item.save()
    
    # Calculate refund amount
    refund_amount = order.total if order.payment_status == 'completed' else Decimal('0')
    
    # Update order status
    order.status = 'cancelled'
    order.cancelled_at = timezone.now()
    order.save()
    
    # Create cancellation record
    OrderCancellation.objects.create(
        order=order,
        cancellation_type='full_order',
        reason=reason,
        refund_amount=refund_amount,
        cancelled_by=request.user
    )
    
    return JsonResponse({
        'success': True,
        'message': f'Order {order.order_id} cancelled successfully.',
        'refund_amount': float(refund_amount) if refund_amount > 0 else None
    })


@login_required
@require_POST
def cancel_order_item(request, item_id):
    """Cancel individual order item with reason"""
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    
    if not item.can_cancel:
        return JsonResponse({
            'success': False,
            'message': 'This item cannot be cancelled.'
        })
    
    reason = request.POST.get('reason', '').strip()
    
    if not reason:
        return JsonResponse({
            'success': False,
            'message': 'Please provide a cancellation reason.'
        })
    
    # Restore stock
    if item.variant:
        item.variant.stock_quantity += item.quantity
        item.variant.save()
    else:
        item.product.stock += item.quantity
        item.product.save()
    
    # Calculate proportional refund if paid
    refund_amount = Decimal('0')
    if item.order.payment_status == 'completed':
        refund_amount = item.item_total
    
    item.status = 'cancelled'
    item.save()
    
    # Create cancellation record
    OrderCancellation.objects.create(
        order=item.order,
        order_item=item,
        cancellation_type='single_item',
        reason=reason,
        refund_amount=refund_amount,
        cancelled_by=request.user
    )
    
    # Check if all items are cancelled
    if not item.order.items.filter(status='active').exists():
        item.order.status = 'cancelled'
        item.order.cancelled_at = timezone.now()
        item.order.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Item cancelled successfully.',
        'refund_amount': float(refund_amount) if refund_amount > 0 else None
    })


@login_required
@require_POST
def return_order(request, order_id):
    """Request order return with mandatory reason"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    if not order.can_return:
        return JsonResponse({
            'success': False,
            'message': 'This order cannot be returned. Return window may have expired.'
        })
    
    reason = request.POST.get('reason', '').strip()
    comments = request.POST.get('comments', '').strip()
    
    if not reason:
        return JsonResponse({
            'success': False,
            'message': 'Please provide a return reason.'
        })
    
    # Check if return already requested
    existing_return = OrderReturn.objects.filter(order=order).first()
    if existing_return:
        return JsonResponse({
            'success': False,
            'message': f'Return already {existing_return.status}.'
        })
    
    # Create return request
    OrderReturn.objects.create(
        order=order,
        reason=reason,
        additional_comments=comments,
        requested_by=request.user,
        refund_amount=order.total,
        status='requested'
    )
    
    order.status = 'return_requested'
    order.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Return request submitted successfully. We will review and get back to you.'
    })

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
        # Base checks
        product_active = item.product.is_active and item.product.category.is_active
        
        # Check variant availability (only if variant exists)
        if item.variant:
            # Product with variant
            variant_active = item.variant.is_active and item.variant.is_in_stock
            item.is_available = product_active and variant_active
        else:
            # Product without variant - check base product stock
            item.is_available = product_active and item.product.stock > 0
    
    context = {
        'wishlist': wishlist,
        'wishlist_items': wishlist_items,
    }
    
    return render(request, 'products/wishlist.html', context)

@login_required
@require_POST
def add_to_wishlist(request, pk):
    """Add product variant to wishlist - supports products with and without variants"""
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
        
        # ============================================
        #  Handle products WITHOUT variants
        # ============================================
        if not active_variants.exists():
            # Product has NO variants - add to wishlist without variant
            
            # Check if already in wishlist (no variant)
            existing_item = WishlistItem.objects.filter(
                wishlist=wishlist,
                product=product,
                variant=None  # No variant for base products
            ).first()
            
            if existing_item:
                return JsonResponse({
                    'success': False,
                    'message': 'This item is already in your wishlist.',
                    'in_wishlist': True,
                    'wishlist_count': wishlist.total_items
                })
            
            # Add to wishlist without variant
            WishlistItem.objects.create(
                wishlist=wishlist,
                product=product,
                variant=None  # No variant
            )
            
            return JsonResponse({
                'success': True,
                'message': f"'{product.name}' added to wishlist!",
                'wishlist_count': wishlist.total_items,
                'in_wishlist': True
            })
        
        # ============================================
        # Handle products WITH variants
        # ============================================
        
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
        
        # Build message
        if has_multiple_variants:
            message = f"'{product.name}' ({variant.get_color_display()}) added to wishlist!"
        else:
            message = f"'{product.name}' added to wishlist!"
        
        return JsonResponse({
            'success': True,
            'message': message,
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
    """Move wishlist item to cart - handles both products with and without variants"""
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
        
        # Check variant/stock status
        if wishlist_item.variant:
            # Product with variant
            if not wishlist_item.variant.is_active or not wishlist_item.variant.is_in_stock:
                messages.error(request, 'This variant is out of stock.')
                return redirect('products:wishlist_view')
            
            available_stock = wishlist_item.variant.stock_quantity
        else:
            # Product without variant
            if wishlist_item.product.stock <= 0:
                messages.error(request, 'This product is out of stock.')
                return redirect('products:wishlist_view')
            
            available_stock = wishlist_item.product.stock
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Check if already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=wishlist_item.product,
            variant=wishlist_item.variant,  # Will be None for products without variants
            defaults={'quantity': 1}
        )
        
        if not created:
            # Item exists, increment quantity if possible
            if cart_item.quantity < wishlist_item.product.max_quantity_per_order and \
               cart_item.quantity < available_stock:
                cart_item.quantity += 1
                cart_item.save()
        
        # Remove from wishlist
        product_name = wishlist_item.product.name
        wishlist_item.delete()
        
        messages.success(request, f"'{product_name}' moved to cart!")
        return redirect('products:wishlist_view')
        
    except Exception as e:
        import traceback
        traceback.print_exc()  # For debugging
        messages.error(request, 'Failed to move item to cart.')
        return redirect('products:wishlist_view')
    


@login_required
@require_GET
def check_wishlist_status(request, pk):
    """Check if product is in wishlist (AJAX endpoint) - supports products with and without variants"""
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
        
        # ============================================
        # CASE 1: Product WITHOUT variants
        # ============================================
        if not active_variants.exists():
            # Check if product (without variant) is in wishlist
            exists = WishlistItem.objects.filter(
                wishlist=wishlist,
                product=product,
                variant=None  # No variant
            ).exists()
            
            return JsonResponse({
                'in_wishlist': exists,
                'wishlist_count': wishlist.total_items
            })
        
        # ============================================
        # CASE 2: Product WITH variants
        # ============================================
        
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
    
