from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Avg, F, Min, Max
from django.contrib import messages
from django.http import Http404,  JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.template.loader import render_to_string
from django.db.models.functions import Coalesce
from weasyprint import HTML
import json
import razorpay
import hmac
import hashlib

from .models import (
    Product, Category, ProductVariant, ProductReview, Coupon, CouponUsage,
    Cart, CartItem, Order, OrderItem, RazorpayPayment,
    OrderCancellation, OrderReturn, Wishlist, WishlistItem, ProductOffer, CategoryOffer
)
from users.models import Address, Wallet

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


COD_MAX_AMOUNT = Decimal('1000.00')  # Maximum order amount allowed for COD

# |---------Products----------|

def home(request):
    """Home page view"""
    return render(request, 'products/home.html')


def product_list(request):
    """
    Product listing with search, filter, sort and pagination
    Supports:
    - search
    - category filter
    - color filter
    - price filter (base + variants)
    - sorting
    """

    # -------------------------------------------------
    # 1️⃣ Base queryset
    # -------------------------------------------------
    products = (
        Product.objects
        .filter(is_active=True)
        .select_related('category', 'brand')
        .prefetch_related('variants__images')
    )

    # -------------------------------------------------
    # 2️⃣ Annotate EFFECTIVE PRICE (used everywhere)
    # -------------------------------------------------
    products = products.annotate(
        effective_price=Coalesce(
            Min('variants__price', filter=Q(variants__is_active=True)),
            'base_price'
        )
    )

    # -------------------------------------------------
    # 3️⃣ Read query params
    # -------------------------------------------------
    search_query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')
    color_filter = request.GET.get('color', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    sort_by = request.GET.get('sort', '')

    # -------------------------------------------------
    # 4️⃣ Search
    # -------------------------------------------------
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__name__icontains=search_query)
        )

    # -------------------------------------------------
    # 5️⃣ Category filter
    # -------------------------------------------------
    if category_filter:
        products = products.filter(category__name=category_filter)

    # -------------------------------------------------
    # 6️⃣ Color filter (variants)
    # -------------------------------------------------
    if color_filter:
        products = products.filter(
            variants__color=color_filter,
            variants__is_active=True
        )

    # -------------------------------------------------
    # 7️⃣ Price range filter (SAFE & CORRECT)
    # -------------------------------------------------
    if min_price:
        try:
            products = products.filter(
                effective_price__gte=Decimal(min_price)
            )
        except Exception:
            min_price = ''

    if max_price:
        try:
            products = products.filter(
                effective_price__lte=Decimal(max_price)
            )
        except Exception:
            max_price = ''

    # -------------------------------------------------
    # 8️⃣ Sorting (reuse effective_price)
    # -------------------------------------------------
    sort_by = request.GET.get('sort')

    if sort_by == 'price_low':
        products = products.order_by('base_price')
    elif sort_by == 'price_high':
        products = products.order_by('-base_price')
    elif sort_by == 'name_asc':
        products = products.order_by('name')
    elif sort_by == 'name_desc':
        products = products.order_by('-name')

    else:
        products = products.order_by('-created_at')

    # -------------------------------------------------
    # 9️⃣ Remove duplicates (variants JOIN safety)
    # -------------------------------------------------
    products = products.distinct()

    # -------------------------------------------------
    # 🔟 Pagination
    # -------------------------------------------------
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # -------------------------------------------------
    # 1️⃣1️⃣ Sidebar data
    # -------------------------------------------------
    categories = Category.objects.filter(is_active=True)
    available_colors = ProductVariant.COLOR_CHOICES

    # Preserve filters across pagination
    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = query_params.urlencode()

    # -------------------------------------------------
    # 1️⃣2️⃣ Context
    # -------------------------------------------------
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
    """Men's products listing - FIXED SORTING"""
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
            products = products.filter(
                Q(variants__price__gte=min_price_decimal, variants__is_active=True) |
                Q(base_price__gte=min_price_decimal, variants__isnull=True)
            )
        except:
            min_price = ''
    
    if max_price:
        try:
            max_price_decimal = Decimal(max_price)
            products = products.filter(
                Q(variants__price__lte=max_price_decimal, variants__is_active=True) |
                Q(base_price__lte=max_price_decimal, variants__isnull=True)
            )
        except:
            max_price = ''
    
    # ✅ FIXED SORTING
    if sort_by == 'price_low':
        products = products.annotate(
            min_variant_price=Min('variants__price', filter=Q(variants__is_active=True)),
            effective_min_price=Coalesce('min_variant_price', 'base_price')
        ).order_by('effective_min_price')
        
    elif sort_by == 'price_high':
        products = products.annotate(
            max_variant_price=Max('variants__price', filter=Q(variants__is_active=True)),
            effective_max_price=Coalesce('max_variant_price', 'base_price')
        ).order_by('-effective_max_price')
        
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
    """Women's products listing - FIXED SORTING"""
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
            products = products.filter(
                Q(variants__price__gte=min_price_decimal, variants__is_active=True) |
                Q(base_price__gte=min_price_decimal, variants__isnull=True)
            )
        except:
            min_price = ''
    
    if max_price:
        try:
            max_price_decimal = Decimal(max_price)
            products = products.filter(
                Q(variants__price__lte=max_price_decimal, variants__is_active=True) |
                Q(base_price__lte=max_price_decimal, variants__isnull=True)
            )
        except:
            max_price = ''
    
    # ✅ FIXED SORTING
    if sort_by == 'price_low':
        products = products.annotate(
            min_variant_price=Min('variants__price', filter=Q(variants__is_active=True)),
            effective_min_price=Coalesce('min_variant_price', 'base_price')
        ).order_by('effective_min_price')
        
    elif sort_by == 'price_high':
        products = products.annotate(
            max_variant_price=Max('variants__price', filter=Q(variants__is_active=True)),
            effective_max_price=Coalesce('max_variant_price', 'base_price')
        ).order_by('-effective_max_price')
        
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


def product_detail(request, uuid):
    """
    Product detail view with optimized Related Products feature
    """
    try:
        product = get_object_or_404(Product, uuid=uuid)
        
        # Check product availability
        if not product.is_active or not product.category.is_active:
            messages.error(request, f"Sorry, '{product.name}' is currently unavailable.")
            return redirect('products:product_list')
        
        if product.brand and not product.brand.is_active:
            messages.error(request, f"Sorry, '{product.name}' is currently unavailable.")
            return redirect('products:product_list')
            
    except Http404:
        messages.error(request, "Product not found.")
        return redirect('products:product_list')
    
    # Get active variants
    variants = product.variants.filter(is_active=True).prefetch_related('images').order_by('color')
    has_variants = variants.exists()
    
    # Get best offer
    best_offer = product.get_best_offer()
    
    # General product data
    general_data = {
        'name': product.name,
        'description': product.description,
        'brand': product.brand.name if product.brand else None,
        'category': product.category.name,
        'base_price': product.base_price,
        'has_variants': has_variants,
        'is_in_stock': product.is_in_stock,
        'average_rating': product.average_rating,
        'review_count': product.review_count,
    }
    
    # Variant options
    variant_options = []
    for variant in variants:
        variant_options.append({
            'id': variant.id,
            'color': variant.color,
            'color_display': variant.get_color_display(),
            'color_hex': variant.color_hex,
            'is_in_stock': variant.is_in_stock,
        })
    
    # Image data
    general_images = product.images.all()
    all_images = []
    
    for img in general_images:
        all_images.append({
            'url': img.image.url,
            'zoom_image': img.zoom_image.url if img.zoom_image else img.image.url,
            'type': 'general',
            'variant_color': '',
            'variant_name': 'Product Overview',
            'color_hex': '',
        })
    
    for variant in variants:
        for img in variant.images.all():
            all_images.append({
                'url': img.image.url,
                'zoom_image': img.zoom_image.url if img.zoom_image else img.image.url,
                'type': 'variant',
                'variant_color': variant.color,
                'variant_name': variant.get_color_display(),
                'color_hex': variant.color_hex,
            })
    
    # Reviews
    reviews = ProductReview.objects.filter(
        product=product, is_active=True
    ).select_related('user').order_by('-created_at')
    
    # ========================================
    # ✅ OPTIMIZED RELATED PRODUCTS
    # ========================================
    related_products = Product.objects.filter(
        category=product.category,  # Same category
        is_active=True,  # Only active products
        category__is_active=True  # Category must be active
    ).exclude(
        pk=product.pk  # Exclude current product
    ).prefetch_related(
        'images',  # Prefetch images for performance
        'variants'  # Prefetch variants
    ).order_by(
        '-created_at'  # Most recent first
    )[:4]  # Limit to 4 products
    
    # Add additional data to related products
    for related in related_products:
        # Get primary image
        related.primary_image = related.images.first()
        
        # Get best offer if available
        related.best_offer = related.get_best_offer()
        
        # Calculate offer price if offer exists
        if related.best_offer:
            if related.has_variants:
                base_price = related.min_price
            else:
                base_price = related.base_price
            
            related.offer_price = related.best_offer.get_discounted_price(base_price)
            related.discount_percentage = related.best_offer.discount_percentage
    
    # Coupons
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
        rating_distribution[i] = {'count': count, 'percentage': round(percentage, 1)}
    
    context = {
        'product': product,
        'general_data': general_data,
        'variants': variants,
        'variant_options': variant_options,
        'has_variants': has_variants,
        'best_offer': best_offer,
        'all_images': all_images,
        'general_images': general_images,
        'related_products': related_products,  # ✅ Related products
        'reviews': reviews,
        'available_coupons': available_coupons,
        'rating_distribution': rating_distribution,
        'breadcrumb_category': product.category.name,
    }
    
    return render(request, 'products/product_detail.html', context)





# |---------Variant----------|


@require_GET
def get_variant_data(request, product_uuid, variant_color):
    """
    ✅ FIXED: Get complete variant data including offers
    Returns all necessary information for displaying variant details
    """
    try:
        product = get_object_or_404(Product, uuid=product_uuid)
        variant = get_object_or_404(
            ProductVariant, 
            product=product, 
            color=variant_color, 
            is_active=True
        )
        
        # Get best offer for this product
        best_offer = product.get_best_offer()
        offer_price = None
        offer_discount = None
        
        if best_offer:
            offer_price = str(best_offer.get_discounted_price(variant.price))
            offer_discount = str(best_offer.calculate_discount(variant.price))
        
        # Build complete variant data
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
            # ✅ Offer data
            'offer_price': offer_price,
            'offer_discount': offer_discount,
            'has_offer': best_offer is not None,
            # ✅ Additional info
            'created_at': variant.created_at.isoformat() if variant.created_at else None,
        }
        
        return JsonResponse({
            'success': True,
            'variant': variant_data
        })
        
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Product not found'
        }, status=404)
    except ProductVariant.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Variant not found'
        }, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
 


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
def add_to_cart(request, uuid):
    """
    ✅ FIXED: Add product to cart with proper variant handling
    - Products WITHOUT variants: Add base product
    - Products WITH variants: REQUIRE variant selection
    """
    try:
        product = get_object_or_404(Product, uuid=uuid)
        
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
        
        # Get variant color from request
        variant_color = request.POST.get('variant_color', '').strip()
        
        # Get active variants
        active_variants = product.variants.filter(is_active=True)
        has_variants = active_variants.exists()
        
        # ✅ FIX: Determine what to add
        variant_to_add = None
        available_stock = 0
        
        if not has_variants:
            # ====================================
            # CASE 1: Product has NO variants
            # ====================================
            variant_to_add = None
            available_stock = product.stock
            
        elif variant_color and variant_color != '' and variant_color != 'no-variant':
            # ====================================
            # CASE 2: Product HAS variants AND user selected specific variant
            # ====================================
            try:
                variant_to_add = active_variants.get(color=variant_color)
                available_stock = variant_to_add.stock_quantity
            except ProductVariant.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Selected variant is not available.'
                })
        else:
            # ====================================
            # CASE 3: Product HAS variants BUT no variant was selected
            # ====================================
            return JsonResponse({
                'success': False,
                'message': 'Please select a color variant before adding to cart.'
            })
        
        # Check stock availability
        if available_stock <= 0:
            return JsonResponse({
                'success': False,
                'message': f"'{product.name}' is currently out of stock."
            })
        
        # Get or create cart item
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant_to_add,
            defaults={'quantity': quantity}
        )
        
        # Update quantity if item already exists
        if not item_created:
            new_quantity = cart_item.quantity + quantity
            
            # Check max quantity per order
            if new_quantity > product.max_quantity_per_order:
                return JsonResponse({
                    'success': False,
                    'message': f"Maximum {product.max_quantity_per_order} items allowed per order."
                })
            
            # Check stock
            if new_quantity > available_stock:
                return JsonResponse({
                    'success': False,
                    'message': f"Only {available_stock} items available."
                })
            
            cart_item.quantity = new_quantity
            cart_item.save()
            action = 'updated'
        else:
            # New item - validate quantity
            if quantity > product.max_quantity_per_order:
                cart_item.quantity = product.max_quantity_per_order
                cart_item.save()
            
            if quantity > available_stock:
                cart_item.quantity = available_stock
                cart_item.save()
            
            action = 'added'
        
        # Remove from wishlist if exists
        try:
            wishlist = Wishlist.objects.get(user=request.user)
            WishlistItem.objects.filter(
                wishlist=wishlist,
                product=product,
                variant=variant_to_add
            ).delete()
        except Wishlist.DoesNotExist:
            pass
        
        # Build success message
        if variant_to_add:
            message = f"'{product.name}' ({variant_to_add.get_color_display()}) {action} to cart!"
        else:
            message = f"'{product.name}' {action} to cart!"
        
        return JsonResponse({
            'success': True,
            'message': message,
            'cart_count': cart.total_items
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again.'
        })

    
@login_required
def cart_view(request):
    """Display cart with all items- WITH OFFER SUPPORT"""
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
    
    # ✅ CALCULATE CART TOTALS WITH OFFERS
    subtotal = Decimal('0')
    offer_discount_total = Decimal('0')
    original_total = Decimal('0')
    
    for item in cart_items:
        # Skip unavailable items from calculation
        if item in unavailable_items:
            continue
        
        # Get item price (from variant or base product)
        if item.variant:
            item_price = item.variant.price
        else:
            item_price = item.product.base_price
        
        # Add to original total
        original_total += item_price * item.quantity
        
        # Check if product has an active offer
        best_offer = item.product.get_best_offer()
        
        if best_offer:
            # Apply offer discount
            offer_discount = best_offer.calculate_discount(item_price)
            discounted_price = item_price - offer_discount
            item_total = discounted_price * item.quantity
            offer_discount_total += (offer_discount * item.quantity)
            
            # Attach offer info to item for template access
            item.offer_info = {
                'has_offer': True,
                'original_price': item_price,
                'discounted_price': discounted_price,
                'discount_percentage': best_offer.discount_percentage,
                'savings': offer_discount,
                'offer_name': best_offer.name
            }
        else:
            item_total = item_price * item.quantity
            item.offer_info = {
                'has_offer': False,
                'original_price': item_price
            }
        
        subtotal += item_total
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'unavailable_items': unavailable_items,
        'subtotal_with_offers': subtotal,
        'offer_discount_total': offer_discount_total,
        'original_total': original_total,
    }

    return render(request, 'products/cart.html', context)



@login_required
@require_POST
def update_cart_item(request, item_uuid):
    """Update cart item quantity with AJAX support - WITH OFFERS"""
    try:
        cart_item = get_object_or_404(CartItem, uuid=item_uuid, cart__user=request.user)
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
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid action.'
            })

        # ✅ CALCULATE TOTALS WITH OFFERS
        cart = cart_item.cart
        cart_items = cart.items.select_related('product', 'variant', 'product__category')
        
        subtotal = Decimal('0')
        offer_discount_total = Decimal('0')
        
        for item in cart_items:
            # Validate item availability
            if not item.product.is_active or not item.product.category.is_active:
                continue
            if item.variant and not item.variant.is_active:
                continue
                
            if item.variant:
                item_price = item.variant.price
            else:
                item_price = item.product.base_price
            
            best_offer = item.product.get_best_offer()
            
            if best_offer:
                offer_discount = best_offer.calculate_discount(item_price)
                discounted_price = item_price - offer_discount
                item_total = discounted_price * item.quantity
                offer_discount_total += (offer_discount * item.quantity)
            else:
                item_total = item_price * item.quantity
            
            subtotal += item_total
        
        tax = subtotal * Decimal('0.18')
        shipping = Decimal('0') if subtotal > 500 else Decimal('50')
        total = subtotal + tax + shipping
        
        # Get current item's offer-adjusted price
        current_item_price = cart_item.variant.price if cart_item.variant else cart_item.product.base_price
        current_best_offer = cart_item.product.get_best_offer()
        
        if current_best_offer:
            current_offer_discount = current_best_offer.calculate_discount(current_item_price)
            current_discounted_price = current_item_price - current_offer_discount
            current_item_total = current_discounted_price * cart_item.quantity
        else:
            current_item_total = current_item_price * cart_item.quantity

        return JsonResponse({
            'success': True,
            'quantity': cart_item.quantity,
            'item_total': float(current_item_total),
            'cart_subtotal': float(subtotal),
            'cart_tax': float(tax),
            'cart_shipping': float(shipping),
            'cart_total': float(total),
            'cart_items_count': cart.total_items,
            'offer_discount': float(offer_discount_total)
        })

    except CartItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cart item not found.'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while updating cart.'
        })


@login_required
@require_POST
def remove_cart_item(request, item_uuid):
    """Remove item from cart with AJAX support - WITH OFFERS"""
    try:
        cart_item = get_object_or_404(CartItem, uuid=item_uuid, cart__user=request.user)
        product_name = cart_item.product.name
        cart = cart_item.cart
        
        cart_item.delete()

        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # ✅ RECALCULATE WITH OFFERS
            cart_items = cart.items.select_related('product', 'variant', 'product__category')
            
            subtotal = Decimal('0')
            offer_discount_total = Decimal('0')
            
            for item in cart_items:
                if not item.product.is_active or not item.product.category.is_active:
                    continue
                if item.variant and not item.variant.is_active:
                    continue
                    
                if item.variant:
                    item_price = item.variant.price
                else:
                    item_price = item.product.base_price
                
                best_offer = item.product.get_best_offer()
                
                if best_offer:
                    offer_discount = best_offer.calculate_discount(item_price)
                    discounted_price = item_price - offer_discount
                    item_total = discounted_price * item.quantity
                    offer_discount_total += (offer_discount * item.quantity)
                else:
                    item_total = item_price * item.quantity
                
                subtotal += item_total
            
            tax = subtotal * Decimal('0.18')
            shipping = Decimal('0') if subtotal > 500 else Decimal('50')
            total = subtotal + tax + shipping
            
            return JsonResponse({
                'success': True,
                'message': f"'{product_name}' removed from cart.",
                'cart_subtotal': float(subtotal),
                'cart_tax': float(tax),
                'cart_shipping': float(shipping),
                'cart_total': float(total),
                'cart_items_count': cart.total_items,
                'cart_empty': cart.total_items == 0,
                'offer_discount': float(offer_discount_total)
            })
        else:
            # Regular form submission
            messages.success(request, f"'{product_name}' removed from cart.")
            return redirect('products:cart_view')

    except CartItem.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Cart item not found.'
            })
        else:
            messages.error(request, 'Cart item not found.')
            return redirect('products:cart_view')
    except Exception as e:
        import traceback
        traceback.print_exc()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Failed to remove item from cart.'
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


# ================== NEW: CANCEL CART ITEM FUNCTIONALITY ==================

@login_required
@require_POST
def cancel_cart_item(request, item_uuid):
    """Cancel/Remove a specific cart item (alternative to remove)"""
    try:
        cart_item = get_object_or_404(CartItem, uuid=item_uuid, cart__user=request.user)
        product_name = cart_item.product.name
        variant_name = cart_item.variant.get_color_display() if cart_item.variant else None
        
        # Delete the item
        cart_item.delete()
        
        # Build message
        if variant_name:
            message = f"'{product_name}' ({variant_name}) cancelled from cart."
        else:
            message = f"'{product_name}' cancelled from cart."
        
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            cart = Cart.objects.get(user=request.user)
            
            # Recalculate totals
            cart_items = cart.items.select_related('product', 'variant', 'product__category')
            
            subtotal = Decimal('0')
            offer_discount_total = Decimal('0')
            
            for item in cart_items:
                if not item.product.is_active or not item.product.category.is_active:
                    continue
                if item.variant and not item.variant.is_active:
                    continue
                    
                if item.variant:
                    item_price = item.variant.price
                else:
                    item_price = item.product.base_price
                
                best_offer = item.product.get_best_offer()
                
                if best_offer:
                    offer_discount = best_offer.calculate_discount(item_price)
                    discounted_price = item_price - offer_discount
                    item_total = discounted_price * item.quantity
                    offer_discount_total += (offer_discount * item.quantity)
                else:
                    item_total = item_price * item.quantity
                
                subtotal += item_total
            
            tax = subtotal * Decimal('0.18')
            shipping = Decimal('0') if subtotal > 500 else Decimal('50')
            total = subtotal + tax + shipping
            
            return JsonResponse({
                'success': True,
                'message': message,
                'cart_subtotal': float(subtotal),
                'cart_tax': float(tax),
                'cart_shipping': float(shipping),
                'cart_total': float(total),
                'cart_items_count': cart.total_items,
                'cart_empty': cart.total_items == 0,
                'offer_discount': float(offer_discount_total)
            })
        else:
            messages.success(request, message)
            return redirect('products:cart_view')
            
    except CartItem.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Cart item not found.'
            })
        else:
            messages.error(request, 'Cart item not found.')
            return redirect('products:cart_view')
    except Exception as e:
        import traceback
        traceback.print_exc()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Failed to cancel item.'
            })
        else:
            messages.error(request, 'Failed to cancel item.')
            return redirect('products:cart_view')


@login_required
@require_POST
def cancel_entire_cart(request):
    """Cancel all items in cart (clear cart with confirmation)"""
    try:
        cart = Cart.objects.get(user=request.user)
        item_count = cart.total_items
        
        if item_count == 0:
            return JsonResponse({
                'success': False,
                'message': 'Cart is already empty.'
            })
        
        # Delete all items
        cart.items.all().delete()
        
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'All {item_count} items cancelled from cart.',
                'cart_empty': True,
                'cart_items_count': 0
            })
        else:
            messages.success(request, f'All {item_count} items cancelled from cart.')
            return redirect('products:cart_view')
            
    except Cart.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Cart not found.'
            })
        else:
            messages.error(request, 'Cart not found.')
            return redirect('products:cart_view')
    except Exception as e:
        import traceback
        traceback.print_exc()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Failed to cancel cart.'
            })
        else:
            messages.error(request, 'Failed to cancel cart.')
            return redirect('products:cart_view')


@login_required
@require_POST
def cancel_selected_items(request):
    """Cancel multiple selected items from cart"""
    try:
        # Get list of item UUIDs from POST data
        item_uuids = request.POST.getlist('item_uuids[]')
        
        if not item_uuids:
            return JsonResponse({
                'success': False,
                'message': 'No items selected.'
            })
        
        cart = Cart.objects.get(user=request.user)
        
        # Delete selected items
        deleted_count = CartItem.objects.filter(
            cart=cart,
            uuid__in=item_uuids
        ).delete()[0]
        
        # Recalculate totals
        cart_items = cart.items.select_related('product', 'variant', 'product__category')
        
        subtotal = Decimal('0')
        offer_discount_total = Decimal('0')
        
        for item in cart_items:
            if not item.product.is_active or not item.product.category.is_active:
                continue
            if item.variant and not item.variant.is_active:
                continue
                
            if item.variant:
                item_price = item.variant.price
            else:
                item_price = item.product.base_price
            
            best_offer = item.product.get_best_offer()
            
            if best_offer:
                offer_discount = best_offer.calculate_discount(item_price)
                discounted_price = item_price - offer_discount
                item_total = discounted_price * item.quantity
                offer_discount_total += (offer_discount * item.quantity)
            else:
                item_total = item_price * item.quantity
            
            subtotal += item_total
        
        tax = subtotal * Decimal('0.18')
        shipping = Decimal('0') if subtotal > 500 else Decimal('50')
        total = subtotal + tax + shipping
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully cancelled {deleted_count} item(s).',
            'cart_subtotal': float(subtotal),
            'cart_tax': float(tax),
            'cart_shipping': float(shipping),
            'cart_total': float(total),
            'cart_items_count': cart.total_items,
            'cart_empty': cart.total_items == 0,
            'offer_discount': float(offer_discount_total),
            'deleted_count': deleted_count
        })
        
    except Cart.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cart not found.'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': 'Failed to cancel selected items.'
        })

 #================== CHECKOUT & PAYMENT VIEWS ==================

@login_required
def checkout_view(request):
    """Checkout page with wallet payment option - SUPPORTS SELECTED ITEMS"""
    try:
        cart = Cart.objects.get(user=request.user)
        
        if cart.total_items == 0:
            messages.warning(request, 'Your cart is empty.')
            return redirect('products:cart_view')
        
        # GET SELECTED ITEM IDs FROM SESSION
        selected_item_ids = request.session.get('selected_cart_items', [])
        
        cart_items = cart.items.select_related(
            'product', 'variant', 'product__category'
        ).prefetch_related('variant__images')
        
        # FILTER TO ONLY SELECTED ITEMS IF ANY ARE SELECTED
        if selected_item_ids:
            cart_items = cart_items.filter(uuid__in=selected_item_ids)
            
            if not cart_items.exists():
                messages.error(request, 'No valid items selected for checkout.')
                return redirect('products:cart_view')
        
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
        
        # ✅ REMOVED: Don't redirect if no addresses - let checkout page handle it
        # if not addresses.exists():
        #     messages.warning(request, 'Please add a delivery address.')
        #     return redirect('users:add_address')
        
        # Calculate totals with offer discounts
        subtotal = Decimal('0')
        offer_discount_total = Decimal('0')
        original_total = Decimal('0')
        
        for item in cart_items:
            if item.variant:
                item_price = item.variant.price
                product = item.product
            else:
                item_price = item.product.base_price
                product = item.product
            
            original_total += item_price * item.quantity
            best_offer = product.get_best_offer()
            
            if best_offer:
                offer_discount = best_offer.calculate_discount(item_price)
                discounted_price = item_price - offer_discount
                item_total = discounted_price * item.quantity
                offer_discount_total += (offer_discount * item.quantity)
                
                item.offer_info = {
                    'has_offer': True,
                    'original_price': item_price,
                    'discounted_price': discounted_price,
                    'discount_percentage': best_offer.discount_percentage,
                    'savings': offer_discount,
                    'offer_name': best_offer.name
                }
            else:
                item_total = item_price * item.quantity
                item.offer_info = {
                    'has_offer': False,
                    'original_price': item_price
                }
            
            subtotal += item_total

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
                    request.session.pop('applied_coupon_code', None)
                    request.session.pop('coupon_discount', None)
            except Coupon.DoesNotExist:
                request.session.pop('applied_coupon_code', None)
                request.session.pop('coupon_discount', None)
        
        total = subtotal + tax + shipping_charge - coupon_discount
        
        # Check if COD is allowed based on order total
        cod_allowed = total <= COD_MAX_AMOUNT
        
        # Get wallet balance
        wallet = Wallet.objects.get_or_create(user=request.user)[0]
        wallet_balance = wallet.balance
        can_use_wallet = wallet.has_sufficient_balance(total)
        
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
            'offer_discount_total': offer_discount_total,
            'original_total': original_total,
            'wallet_balance': wallet_balance,
            'can_use_wallet': can_use_wallet,
            'is_partial_checkout': bool(selected_item_ids),
            'selected_items_count': len(selected_item_ids) if selected_item_ids else cart.total_items,
            'cod_allowed': cod_allowed,
            'cod_max_amount': COD_MAX_AMOUNT,
        }
        
        return render(request, 'products/checkout.html', context)
        
    except Cart.DoesNotExist:
        messages.warning(request, 'Your cart is empty.')
        return redirect('products:cart_view')



# ✅ NEW: Store selected items for checkout
@login_required
@require_POST
def proceed_to_checkout_with_selection(request):
    """Store selected item UUIDs in session and redirect to checkout"""
    try:
        selected_items = request.POST.getlist('selected_items[]')
        
        if not selected_items:
            # No items selected - clear session and proceed with full cart
            request.session.pop('selected_cart_items', None)
            messages.info(request, 'Proceeding to checkout with all cart items.')
        else:
            # Store selected items in session
            request.session['selected_cart_items'] = selected_items
            messages.success(request, f'Proceeding to checkout with {len(selected_items)} selected item(s).')
        
        return redirect('products:checkout_view')
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, 'Failed to proceed to checkout.')
        return redirect('products:cart_view')
    
    

@login_required
@require_POST
def create_razorpay_order(request):
    """Create Razorpay order for payment - WITH OFFER AND SELECTED ITEMS SUPPORT"""
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
        
        # ✅ GET SELECTED ITEMS
        selected_item_ids = request.session.get('selected_cart_items', [])
        
        # ✅ CALCULATE TOTALS WITH OFFER DISCOUNTS
        cart_items = cart.items.select_related('product', 'variant')
        
        # ✅ FILTER SELECTED ITEMS
        if selected_item_ids:
            cart_items = cart_items.filter(uuid__in=selected_item_ids)
        
        subtotal = Decimal('0')
        offer_discount_total = Decimal('0')
        
        for item in cart_items:
            if item.variant:
                item_price = item.variant.price
                product = item.product
            else:
                item_price = item.product.base_price
                product = item.product
            
            # Check for offers
            best_offer = product.get_best_offer()
            
            if best_offer:
                offer_discount = best_offer.calculate_discount(item_price)
                discounted_price = item_price - offer_discount
                item_total = discounted_price * item.quantity
                offer_discount_total += (offer_discount * item.quantity)
            else:
                item_total = item_price * item.quantity
            
            subtotal += item_total

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
        
        # ✅ SANITIZE ADDRESS LINE 2
        # Sanitize address fields
        shipping_line1 = address.address_line1 if address.address_line1 and address.address_line1.strip() and address.address_line1.upper() != 'N/A' else ''
        shipping_line2 = address.address_line2 if address.address_line2 and address.address_line2.strip() and address.address_line2.upper() != 'N/A' else ''
        shipping_country = address.country if address.country and address.country.strip() and address.country.upper() != 'N/A' else ''
        
        # Create order in database (pending state)
        order = Order.objects.create(
            user=request.user,
            shipping_full_name=address.full_name,
            shipping_phone=address.phone,
            shipping_line1=shipping_line1,
            shipping_line2=shipping_line2,
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_postal_code=address.postal_code,
            shipping_country=shipping_country,
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
        
        # Create order items with offer-adjusted prices
        for item in cart_items:
            if item.variant:
                item_image = item.variant.images.first()
                variant_name = item.variant.get_color_display()
                item_price = item.variant.price
                product = item.product
            else:
                item_image = item.product.images.first()
                variant_name = ''
                item_price = item.product.base_price
                product = item.product
            
            # Apply offer if available
            best_offer = product.get_best_offer()
            if best_offer:
                offer_discount = best_offer.calculate_discount(item_price)
                final_price = item_price - offer_discount
            else:
                final_price = item_price
            
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                product_name=item.product.name,
                product_image=item_image.image if item_image else None,
                variant_name=variant_name,
                price=final_price,
                quantity=item.quantity,
                item_total=final_price * item.quantity
            )

        # ✅ CREATE RAZORPAY ORDER
        amount_in_paise = int(total * 100)  # Convert to paise
        
        try:
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
            
            # ✅ Return data for frontend
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
            # Delete the order if Razorpay order creation fails
            order.delete()
            return JsonResponse({
                'success': False,
                'message': f'Payment gateway error: {str(e)}'
            })
        
    except Cart.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cart not found.'
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
    """Verify Razorpay payment signature - WITH SELECTED ITEMS CLEANUP"""
    try:
        data = json.loads(request.body)
        
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')
        
        # Get payment record
        payment = RazorpayPayment.objects.get(razorpay_order_id=razorpay_order_id)
        order = payment.order
        
        # ✅ VERIFY SIGNATURE
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode('utf-8'),
            f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature == razorpay_signature:
            # ✅ PAYMENT SUCCESSFUL
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = 'paid'
            payment.save()
            
            order.payment_status = 'completed'
            order.status = 'confirmed'
            order.save()
            
            # ✅ GET SELECTED ITEMS FROM SESSION
            selected_item_ids = request.session.get('selected_cart_items', [])
            
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
            
            # ✅ CLEAR CART - ONLY SELECTED OR ALL
            try:
                cart = Cart.objects.get(user=request.user)
                if selected_item_ids:
                    cart.items.filter(uuid__in=selected_item_ids).delete()
                else:
                    cart.items.all().delete()
            except Cart.DoesNotExist:
                pass
            
            # ✅ CLEAR SESSION
            request.session.pop('applied_coupon_code', None)
            request.session.pop('coupon_discount', None)
            request.session.pop('selected_cart_items', None)
            
            return JsonResponse({
                'success': True,
                'order_id': order.order_id,
                'redirect_url': f'/products/order/success/{order.order_id}/'
            })
        else:
            # ❌ SIGNATURE VERIFICATION FAILED
            payment.status = 'failed'
            payment.save()
            
            order.payment_status = 'failed'
            order.save()
            
            return JsonResponse({
                'success': False,
                'message': 'Payment verification failed',
                'redirect_url': f'/products/order/failure/{order.order_id}/'
            })
        
    except RazorpayPayment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Payment record not found'
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
    """Place order with Cash on Delivery - WITH OFFER SUPPORT AND SELECTED ITEMS"""
    try:
        cart = Cart.objects.get(user=request.user)
        
        if cart.total_items == 0:
            return JsonResponse({
                'success': False,
                'message': 'Your cart is empty.'
            })
        
        # Get selected address
        address_id = request.POST.get('address_id')
        if not address_id:
            return JsonResponse({
                'success': False,
                'message': 'Please select a delivery address.'
            })
        address = get_object_or_404(Address, id=address_id, user=request.user, is_active=True)
        
        # GET SELECTED ITEMS FROM SESSION
        selected_item_ids = request.session.get('selected_cart_items', [])
        
        # Validate cart items
        cart_items = cart.items.select_related('product', 'variant')
        
        # FILTER TO SELECTED ITEMS ONLY
        if selected_item_ids:
            cart_items = cart_items.filter(uuid__in=selected_item_ids)
        
        for item in cart_items:
            if not item.product.is_active or not item.product.category.is_active:
                return JsonResponse({
                    'success': False,
                    'message': f"'{item.product.name}' is no longer available."
                })
            
            if item.variant:
                if not item.variant.is_active or item.variant.stock_quantity < item.quantity:
                    return JsonResponse({
                        'success': False,
                        'message': f"'{item.product.name}' stock insufficient."
                    })
            else:
                if item.product.stock < item.quantity:
                    return JsonResponse({
                        'success': False,
                        'message': f"'{item.product.name}' stock insufficient."
                    })
        
        # CALCULATE TOTALS WITH OFFER DISCOUNTS
        subtotal = Decimal('0')
        offer_discount_total = Decimal('0')
        
        for item in cart_items:
            if item.variant:
                item_price = item.variant.price
                product = item.product
            else:
                item_price = item.product.base_price
                product = item.product
            
            # Check for offers
            best_offer = product.get_best_offer()
            
            if best_offer:
                offer_discount = best_offer.calculate_discount(item_price)
                discounted_price = item_price - offer_discount
                item_total = discounted_price * item.quantity
                offer_discount_total += (offer_discount * item.quantity)
            else:
                item_total = item_price * item.quantity
            
            subtotal += item_total

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
        
        # ✅ NEW: Validate COD amount limit
        if total > COD_MAX_AMOUNT:
            return JsonResponse({
                'success': False,
                'message': f'Cash on Delivery is not available for orders above ₹{COD_MAX_AMOUNT}. Please choose another payment method.'
            })
        
        shipping_line1 = address.address_line1 if address.address_line1 and address.address_line1.strip() and address.address_line1.upper() != 'N/A' else ''
        shipping_line2 = address.address_line2 if address.address_line2 and address.address_line2.strip() and address.address_line2.upper() != 'N/A' else ''
        shipping_country = address.country if address.country and address.country.strip() and address.country.upper() != 'N/A' else ''

        # Create order
        order = Order.objects.create(
            user=request.user,
            shipping_full_name=address.full_name,
            shipping_phone=address.phone,
            shipping_line1=shipping_line1,
            shipping_line2=shipping_line2,
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_postal_code=address.postal_code,
            shipping_country=shipping_country,
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
        
        # CREATE ORDER ITEMS AND REDUCE STOCK WITH OFFER-ADJUSTED PRICES
        for item in cart_items:
            if item.variant:
                item_image = item.variant.images.first()
                variant_name = item.variant.get_color_display()
                item_price = item.variant.price
                product = item.product
            else:
                item_image = item.product.images.first()
                variant_name = ''
                item_price = item.product.base_price
                product = item.product
            
            # Apply offer if available
            best_offer = product.get_best_offer()
            if best_offer:
                offer_discount = best_offer.calculate_discount(item_price)
                final_price = item_price - offer_discount
            else:
                final_price = item_price
            
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                product_name=item.product.name,
                product_image=item_image.image if item_image else None,
                variant_name=variant_name,
                price=final_price,
                quantity=item.quantity,
                item_total=final_price * item.quantity
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
        
        # DELETE ONLY SELECTED ITEMS OR ALL
        if selected_item_ids:
            cart.items.filter(uuid__in=selected_item_ids).delete()
        else:
            cart.items.all().delete()
        
        # CLEAR SESSION
        request.session.pop('applied_coupon_code', None)
        request.session.pop('coupon_discount', None)
        request.session.pop('selected_cart_items', None)
        
        return JsonResponse({
            'success': True,
            'message': f'Order placed successfully! Order ID: {order.order_id}',
            'redirect_url': f'/products/order/success/{order.order_id}/'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': 'Failed to place order. Please try again.'
        })


# ================== WALLET PAYMENT VIEW ==================


# ✅ SIMILAR UPDATES FOR OTHER PAYMENT METHODS
@login_required
@require_POST
def place_order_wallet(request):
    """Place order using wallet balance - WITH SELECTED ITEMS SUPPORT"""
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
        
        # ✅ GET SELECTED ITEMS FROM SESSION
        selected_item_ids = request.session.get('selected_cart_items', [])
        
        # Validate cart items
        cart_items = cart.items.select_related('product', 'variant')
        
        # ✅ FILTER TO SELECTED ITEMS
        if selected_item_ids:
            cart_items = cart_items.filter(uuid__in=selected_item_ids)
        
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
        
        # Calculate totals with offer discounts
        subtotal = Decimal('0')
        offer_discount_total = Decimal('0')
        
        for item in cart_items:
            if item.variant:
                item_price = item.variant.price
                product = item.product
            else:
                item_price = item.product.base_price
                product = item.product
            
            best_offer = product.get_best_offer()
            
            if best_offer:
                offer_discount = best_offer.calculate_discount(item_price)
                discounted_price = item_price - offer_discount
                item_total = discounted_price * item.quantity
                offer_discount_total += (offer_discount * item.quantity)
            else:
                item_total = item_price * item.quantity
            
            subtotal += item_total

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
        
        # Check wallet balance
        wallet = Wallet.objects.get_or_create(user=request.user)[0]
        
        if not wallet.has_sufficient_balance(total):
            messages.error(request, f'Insufficient wallet balance. You have ₹{wallet.balance}, but order total is ₹{total}.')
            return redirect('products:checkout_view')
        
        shipping_line1 = address.address_line1 if address.address_line1 and address.address_line1.strip() and address.address_line1.upper() != 'N/A' else ''
        shipping_line2 = address.address_line2 if address.address_line2 and address.address_line2.strip() and address.address_line2.upper() != 'N/A' else ''
        shipping_country = address.country if address.country and address.country.strip() and address.country.upper() != 'N/A' else ''

        # Create order
        order = Order.objects.create(
            user=request.user,
            shipping_full_name=address.full_name,
            shipping_phone=address.phone,
            shipping_line1=shipping_line1,
            shipping_line2=shipping_line2,
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_postal_code=address.postal_code,
            shipping_country=shipping_country,
            subtotal=subtotal,
            tax=tax,
            shipping_charge=shipping_charge,
            discount=coupon_discount,
            coupon=coupon,
            total=total,
            payment_method='wallet',
            payment_status='completed',
            status='confirmed',
            notes=request.POST.get('notes', '')
        )
        
        # Create order items and reduce stock
        for item in cart_items:
            if item.variant:
                item_image = item.variant.images.first()
                variant_name = item.variant.get_color_display()
                item_price = item.variant.price
                product = item.product
            else:
                item_image = item.product.images.first()
                variant_name = ''
                item_price = item.product.base_price
                product = item.product
            
            # Apply offer if available
            best_offer = product.get_best_offer()
            if best_offer:
                offer_discount = best_offer.calculate_discount(item_price)
                final_price = item_price - offer_discount
            else:
                final_price = item_price
            
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                product_name=item.product.name,
                product_image=item_image.image if item_image else None,
                variant_name=variant_name,
                price=final_price,
                quantity=item.quantity,
                item_total=final_price * item.quantity
            )
            
            # Reduce stock
            if item.variant:
                item.variant.stock_quantity -= item.quantity
                item.variant.save()
            else:
                item.product.stock -= item.quantity
                item.product.save()
        
        # Deduct from wallet
        wallet.deduct_money(
            amount=total,
            transaction_type='debit_purchase',
            description=f'Order payment for {order.order_id}',
            reference_id=order.order_id
        )
        
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
        
        # ✅ DELETE ONLY SELECTED ITEMS OR ALL
        if selected_item_ids:
            cart.items.filter(uuid__in=selected_item_ids).delete()
        else:
            cart.items.all().delete()
        
        # ✅ CLEAR SESSION
        request.session.pop('applied_coupon_code', None)
        request.session.pop('coupon_discount', None)
        request.session.pop('selected_cart_items', None)
        
        messages.success(request, f'Order placed successfully using wallet! Order ID: {order.order_id}')
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
    
    # Format delivery address properly
    address_parts = [order.shipping_line1]
    if order.shipping_line2 and order.shipping_line2.strip():
        address_parts.append(order.shipping_line2)
    
    formatted_address = ", ".join(address_parts)
    
    context = {
        'order': order,
        'formatted_address': formatted_address,
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

@login_required
@require_POST
def retry_payment(request, order_id):
    """Retry payment for a failed order"""
    try:
        order = get_object_or_404(Order, order_id=order_id, user=request.user)
        
        # Check if order can be retried
        if order.payment_status not in ['failed', 'pending']:
            return JsonResponse({
                'success': False,
                'message': 'This order cannot be retried.'
            })
        
        # Check if order is too old (optional - prevent retry after 24 hours)
        from datetime import timedelta
        if timezone.now() > order.created_at + timedelta(hours=24):
            return JsonResponse({
                'success': False,
                'message': 'This order is too old to retry. Please place a new order.'
            })
        
        # Verify stock is still available
        for item in order.items.all():
            if item.variant:
                if not item.variant.is_active or item.variant.stock_quantity < item.quantity:
                    return JsonResponse({
                        'success': False,
                        'message': f"'{item.product_name}' is no longer available in required quantity."
                    })
            else:
                if not item.product.is_active or item.product.stock < item.quantity:
                    return JsonResponse({
                        'success': False,
                        'message': f"'{item.product_name}' is no longer available in required quantity."
                    })
        
        # Create new Razorpay order
        amount_in_paise = int(order.total * 100)
        
        try:
            razorpay_order = razorpay_client.order.create({
                'amount': amount_in_paise,
                'currency': 'INR',
                'payment_capture': '1',
                'notes': {
                    'order_id': order.order_id,
                    'user_id': str(request.user.id),
                    'retry': 'true'
                }
            })
            
            # Create new payment record (or update existing)
            RazorpayPayment.objects.create(
                order=order,
                razorpay_order_id=razorpay_order['id'],
                amount=order.total,
                status='created'
            )
            
            # Return payment details
            return JsonResponse({
                'success': True,
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'amount': amount_in_paise,
                'currency': 'INR',
                'order_id': order.order_id,
                'user_name': request.user.get_full_name() or request.user.username,
                'user_email': request.user.email,
                'user_phone': order.shipping_phone
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'message': f'Payment gateway error: {str(e)}'
            })
        
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Order not found.'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': 'Failed to retry payment. Please try again.'
        })
    
@login_required(login_url='users:login')
def download_invoice(request, order_id):
    """Download order invoice as PDF"""
    
    # IMPORT MOVED HERE — SAFE
    from weasyprint import HTML

    # Filter by user
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product', 'items__variant'),
        order_id=order_id,
        user=request.user
    )
    
    # Only allow invoice for completed/pending payments
    if order.payment_status not in ['completed', 'pending'] and order.status == 'pending':
        messages.error(request, 'Invoice not available for this order yet.')
        return redirect('products:order_detail', order_id=order.order_id)
    
    # Render HTML template
    html_string = render_to_string('products/invoice_pdf.html', {
        'order': order,
        'company_name': 'WatchItUp',
        'company_address': 'Kochi, Kerala, India',
        'company_email': 'support@watchitup.com',
        'company_phone': '+91 1234567890',
    })
    
    # Generate PDF
    html = HTML(string=html_string)
    pdf_file = html.write_pdf()
    
    # Create HTTP response with PDF
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="WatchItUp_Invoice_{order.order_id}.pdf"'
    
    return response


#================== ORDER MANAGEMENT VIEWS ==================

@login_required(login_url='users:login')  # ✅ ADDED
def order_list(request):
    """List all user orders with search and filters - FIXED to exclude incomplete orders"""
    from datetime import timedelta
    
    # ✅ FIXED: Only fetch orders that have been properly placed
    thirty_minutes_ago = timezone.now() - timedelta(minutes=30)
    
    orders = Order.objects.filter(
        user=request.user  # ✅ CRITICAL: User can only see their own orders
    ).filter(
        Q(payment_status='completed') |  # Completed payments
        Q(payment_status='refunded') |  # Refunded orders
        Q(
            payment_method='cod',
            status__in=['confirmed', 'processing', 'shipped', 'out_for_delivery', 'delivered']
        ) |  # Confirmed COD orders
        Q(
            created_at__gte=thirty_minutes_ago,
            status='pending',
            payment_status='pending'
        ) |  # Recent pending orders (still processing)
        Q(status='cancelled') |  # Cancelled orders
        Q(status__in=['return_requested', 'return_approved', 'returned'])  # Returned orders
    ).prefetch_related('items').distinct().order_by('-created_at')
    
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


@login_required(login_url='users:login')
def order_detail(request, order_id):
    """Order detail page - USER FACING with individual item selection"""
    # Ensure user can only see their own orders
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product', 'items__variant'),
        order_id=order_id,
        user=request.user
    )
    
    # Get items grouped by status for easier display
    active_items = order.items.filter(status='active')
    cancelled_items = order.items.filter(status='cancelled')
    returned_items = order.items.filter(status='returned')
    
    context = {
        'order': order,
        'active_items': active_items,
        'cancelled_items': cancelled_items,
        'returned_items': returned_items,
        'can_cancel_items': order.can_cancel and active_items.exists(),
        'can_return_items': order.can_return and active_items.exists(),
    }
    
    return render(request, 'products/order_detail.html', context)


@login_required(login_url='users:login')
def download_invoice(request, order_id):
    """
    Download order invoice as PDF with security checks
    """
    # ✅ SECURITY: Filter by user to ensure users can only access their own invoices
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product', 'items__variant'),
        order_id=order_id,
        user=request.user
    )
    
    # ✅ SECURITY: Only allow invoice for valid orders
    if order.payment_status not in ['completed', 'refunded']:
        messages.error(request, 'Invoice not available for this order yet.')
        return redirect('products:order_detail', order_id=order.order_id)
    
    # Calculate active items total (excluding cancelled/returned)
    active_items = order.items.filter(status='active')
    active_items_total = sum(item.item_total for item in active_items)
    
    # Prepare context for invoice template
    context = {
        'order': order,
        'active_items': active_items,
        'active_items_total': active_items_total,
        'company_name': 'WatchItUp',
        'company_address': 'Kochi, Kerala, India',
        'company_email': 'support@watchitup.com',
        'company_phone': '+91 1234567890',
        'company_website': 'www.watchitup.com',
    }
    
    # ✅ CHANGED: Use 'invoice_download.html' instead of 'invoice_pdf.html'
    html_string = render_to_string('products/invoice_download.html', context)
    
    # Generate PDF from HTML
    html = HTML(string=html_string)
    pdf_file = html.write_pdf()
    
    # Create HTTP response with PDF
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="WatchItUp_Invoice_{order.order_id}.pdf"'
    
    return response



@login_required(login_url='users:login')  # ✅ ADDED
@require_POST
def cancel_order(request, order_id):
    """Cancel entire order with wallet refund"""
    # ✅ CRITICAL: Filter by user
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
    refund_amount = Decimal('0')
    if order.payment_status == 'completed':
        refund_amount = order.total
        
        # Refund to wallet
        wallet = Wallet.objects.get_or_create(user=request.user)[0]
        wallet.add_money(
            amount=refund_amount,
            transaction_type='credit_refund_cancel',
            description=f'Refund for cancelled order {order.order_id}',
            reference_id=order.order_id
        )
    
    # Update order status
    order.status = 'cancelled'
    order.cancelled_at = timezone.now()
    order.payment_status = 'refunded' if refund_amount > 0 else order.payment_status
    order.save()
    
    # Create cancellation record
    OrderCancellation.objects.create(
        order=order,
        cancellation_type='full_order',
        reason=reason,
        refund_amount=refund_amount,
        refund_status='processed' if refund_amount > 0 else 'pending',
        cancelled_by=request.user,
        processed_at=timezone.now() if refund_amount > 0 else None
    )
    
    message = f'Order {order.order_id} cancelled successfully.'
    if refund_amount > 0:
        message += f' ₹{refund_amount} has been refunded to your wallet.'
    
    return JsonResponse({
        'success': True,
        'message': message,
        'refund_amount': float(refund_amount) if refund_amount > 0 else None
    })


@login_required(login_url='users:login')  # ✅ ADDED
@require_POST
def cancel_order_item(request, item_uuid):
    """Cancel individual order item with reason"""
    # ✅ CRITICAL: Filter by user
    item = get_object_or_404(OrderItem, id=item_uuid, order__user=request.user)
    
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


@login_required(login_url='users:login')  # ✅ ADDED
@require_POST
def return_order(request, order_id):
    """Request order return - admin approval required for wallet refund"""
    # ✅ CRITICAL: Filter by user
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    if not order.can_return:
        return JsonResponse({
            'success': False,
            'message': 'This order cannot be returned. Return window may have expired or order is not delivered.'
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
    
    # Create return request (pending admin approval)
    OrderReturn.objects.create(
        order=order,
        reason=reason,
        additional_comments=comments,
        requested_by=request.user,
        refund_amount=order.total,
        status='pending'
    )
    
    order.status = 'return_requested'
    order.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Return request submitted successfully. Admin will review and process your refund to wallet.'
    })


# ==================== CANCEL SELECTED ITEMS ====================

@login_required(login_url='users:login')
@require_POST
def cancel_selected_items(request, order_id):
    """Cancel multiple selected items from an order"""
    try:
        order = get_object_or_404(Order, order_id=order_id, user=request.user)
        
        if not order.can_cancel:
            return JsonResponse({
                'success': False,
                'message': 'This order cannot be cancelled anymore.'
            })
        
        # Get selected item IDs
        selected_item_ids = request.POST.getlist('item_ids[]')
        reason = request.POST.get('reason', '').strip()
        
        if not selected_item_ids:
            return JsonResponse({
                'success': False,
                'message': 'Please select at least one item to cancel.'
            })
        
        if not reason:
            return JsonResponse({
                'success': False,
                'message': 'Please provide a cancellation reason.'
            })
        
        # Validate and get items
        items_to_cancel = OrderItem.objects.filter(
            id__in=selected_item_ids,
            order=order,
            status='active'
        )
        
        if not items_to_cancel.exists():
            return JsonResponse({
                'success': False,
                'message': 'No valid items found to cancel.'
            })
        
        # Calculate refund amount
        total_refund = Decimal('0')
        cancelled_items_info = []
        
        for item in items_to_cancel:
            # Restore stock
            if item.variant:
                item.variant.stock_quantity += item.quantity
                item.variant.save()
            else:
                item.product.stock += item.quantity
                item.product.save()
            
            # Calculate item refund
            if order.payment_status == 'completed':
                item_refund = item.item_total
                total_refund += item_refund
            
            # Update item status
            item.status = 'cancelled'
            item.save()
            
            cancelled_items_info.append({
                'name': item.product_name,
                'variant': item.variant_name,
                'quantity': item.quantity
            })
            
            # Create individual cancellation record
            OrderCancellation.objects.create(
                order=order,
                order_item=item,
                cancellation_type='single_item',
                reason=reason,
                refund_amount=item_refund if order.payment_status == 'completed' else Decimal('0'),
                refund_status='processed' if order.payment_status == 'completed' else 'pending',
                cancelled_by=request.user,
                processed_at=timezone.now() if order.payment_status == 'completed' else None
            )
        
        # Process refund to wallet if payment was completed
        if total_refund > 0:
            wallet = Wallet.objects.get_or_create(user=request.user)[0]
            wallet.add_money(
                amount=total_refund,
                transaction_type='credit_refund_cancel',
                description=f'Refund for cancelled items in order {order.order_id}',
                reference_id=order.order_id
            )
        
        # Check if all items are now cancelled
        remaining_active = order.items.filter(status='active').count()
        if remaining_active == 0:
            order.status = 'cancelled'
            order.cancelled_at = timezone.now()
            order.payment_status = 'refunded' if total_refund > 0 else order.payment_status
            order.save()
            
            message = f'All items cancelled successfully.'
        else:
            message = f'{len(cancelled_items_info)} item(s) cancelled successfully.'
        
        if total_refund > 0:
            message += f' ₹{total_refund} has been refunded to your wallet.'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'refund_amount': float(total_refund) if total_refund > 0 else None,
            'cancelled_count': len(cancelled_items_info),
            'all_items_cancelled': remaining_active == 0
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': 'Failed to cancel items. Please try again.'
        })


# ==================== RETURN SELECTED ITEMS ====================

@login_required(login_url='users:login')
@require_POST
def return_selected_items(request, order_id):
    """Request return for multiple selected items"""
    try:
        order = get_object_or_404(Order, order_id=order_id, user=request.user)
        
        if not order.can_return:
            return JsonResponse({
                'success': False,
                'message': 'This order is not eligible for return. Return window may have expired or order is not delivered.'
            })
        
        # Get selected item IDs
        selected_item_ids = request.POST.getlist('item_ids[]')
        reason = request.POST.get('reason', '').strip()
        comments = request.POST.get('comments', '').strip()
        
        if not selected_item_ids:
            return JsonResponse({
                'success': False,
                'message': 'Please select at least one item to return.'
            })
        
        if not reason:
            return JsonResponse({
                'success': False,
                'message': 'Please provide a return reason.'
            })
        
        # Validate and get items
        items_to_return = OrderItem.objects.filter(
            id__in=selected_item_ids,
            order=order,
            status='active'
        )
        
        if not items_to_return.exists():
            return JsonResponse({
                'success': False,
                'message': 'No valid items found to return.'
            })
        
        # Calculate potential refund amount
        total_refund = sum(item.item_total for item in items_to_return)
        
        # Create return request
        order_return = OrderReturn.objects.create(
            order=order,
            reason=reason,
            additional_comments=comments,
            requested_by=request.user,
            refund_amount=total_refund,
            status='pending'
        )
        
        # Store which items are being returned
        # You might want to create a separate model for this, but for now we'll use comments
        item_details = []
        for item in items_to_return:
            item_name = f"{item.product_name}"
            if item.variant_name:
                item_name += f" ({item.variant_name})"
            item_details.append(f"{item_name} x{item.quantity}")
        
        order_return.additional_comments = f"Items: {', '.join(item_details)}\n\n{comments}"
        order_return.save()
        
        # Update order status
        order.status = 'return_requested'
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Return request submitted for {len(items_to_return)} item(s). Admin will review and process your refund to wallet.',
            'items_count': len(items_to_return),
            'potential_refund': float(total_refund)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': 'Failed to submit return request. Please try again.'
        })


# ==================== HELPER: GET ITEM SELECTION DATA ====================

@login_required(login_url='users:login')
@require_GET
def get_order_items_data(request, order_id):
    """Get order items data for selection (AJAX)"""
    try:
        order = get_object_or_404(Order, order_id=order_id, user=request.user)
        
        items_data = []
        for item in order.items.filter(status='active'):
            items_data.append({
                'id': item.id,
                'name': item.product_name,
                'variant': item.variant_name,
                'quantity': item.quantity,
                'price': float(item.price),
                'total': float(item.item_total),
                'image_url': item.product_image.url if item.product_image else None
            })
        
        return JsonResponse({
            'success': True,
            'items': items_data,
            'can_cancel': order.can_cancel,
            'can_return': order.can_return
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


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
def add_to_wishlist(request, uuid):
    """Add product variant to wishlist - supports products with and without variants"""
    try:
        product = get_object_or_404(Product, uuid=uuid)
        
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
        
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Product not found.'
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
def remove_from_wishlist(request, item_uuid):
    """Remove item from wishlist"""
    try:
        # ✅ CRITICAL FIX: WishlistItem uses 'id' not 'uuid', but we'll try uuid first
        # Check if WishlistItem has uuid field
        try:
            wishlist_item = get_object_or_404(
                WishlistItem, 
                uuid=item_uuid,  # Try uuid first
                wishlist__user=request.user
            )
        except:
            # Fallback to id if uuid doesn't exist
            wishlist_item = get_object_or_404(
                WishlistItem, 
                id=item_uuid, 
                wishlist__user=request.user
            )
        
        product_name = wishlist_item.product.name
        wishlist_item.delete()
        
        messages.success(request, f"'{product_name}' removed from wishlist.")
        return redirect('products:wishlist_view')
        
    except Exception as e:
        import traceback
        traceback.print_exc()
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
def move_to_cart_from_wishlist(request, item_uuid):
    """Move wishlist item to cart - handles both products with and without variants"""
    try:
        # ✅ CRITICAL FIX: Try uuid first, fallback to id
        try:
            wishlist_item = get_object_or_404(
                WishlistItem,
                uuid=item_uuid,
                wishlist__user=request.user
            )
        except:
            wishlist_item = get_object_or_404(
                WishlistItem,
                id=item_uuid,
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
def check_wishlist_status(request, uuid):
    """Check if product is in wishlist (AJAX endpoint) - supports products with and without variants"""
    try:
        product = get_object_or_404(Product, uuid=uuid)
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
        
    except Product.DoesNotExist:
        return JsonResponse({
            'in_wishlist': False,
            'wishlist_count': 0,
            'error': 'Product not found'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()  # For debugging
        return JsonResponse({
            'in_wishlist': False,
            'wishlist_count': 0,
            'error': str(e)
        })
    






