from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Avg, F, Min, Max
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from .models import Product, Category, ProductReview, Coupon, ProductVariant, ProductVariantImage
from decimal import Decimal
import json


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
    
    # Color filter - filter products that have variants with the selected color
    if color_filter:
        products = products.filter(variants__color=color_filter, variants__is_active=True)
    
    # Price range filter - filter by variant prices
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
    
    # Remove duplicates that might occur due to variant filtering
    products = products.distinct()
    
    # Pagination
    paginator = Paginator(products, 12)  # 12 products per page
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


def men_products(request):
    """Men's products listing - Updated for variants"""
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
    """Women's products listing - Updated for variants"""
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
    
    # UNIFIED IMAGE COLLECTION - Combine all images into one carousel
    all_images = []
    
    # Add general product images first
    general_images = product.images.all()
    for idx, img in enumerate(general_images):
        all_images.append({
            'url': img.image.url,
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
                'type': 'variant',
                'variant': variant,
                'variant_color': variant.color,
                'variant_name': variant.get_color_display(),
                'is_first_variant': idx == 0,
                'index': len(all_images)
            })
    
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
        'all_images': all_images,  # NEW: Unified image collection
        'general_images': general_images,
        'related_products': related_products,
        'reviews': reviews,
        'available_coupons': available_coupons,
        'rating_distribution': rating_distribution,
        'breadcrumb_category': product.category.name,
    }
    
    return render(request, 'products/product_detail.html', context)


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

def add_to_cart(request, pk):
    """Add product variant to cart with proper error handling"""
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, pk=pk)
            
            # Check if product is available
            if not product.is_active:
                messages.error(request, f"Sorry, '{product.name}' is currently unavailable.")
                return redirect('products:product_list')
            
            # Get selected variant
            variant_color = request.POST.get('variant_color')
            if variant_color:
                try:
                    variant = product.variants.get(color=variant_color, is_active=True)
                    
                    # Check stock
                    if not variant.is_in_stock:
                        messages.error(request, f"Sorry, '{product.name}' in {variant.get_color_display()} is out of stock.")
                        return redirect('products:product_detail', pk=pk)
                    
                    # Add your cart logic here with variant
                    # For now, just show success message
                    messages.success(request, f"'{product.name}' ({variant.get_color_display()}) added to cart successfully!")
                    
                except ProductVariant.DoesNotExist:
                    messages.error(request, "Please select a valid color option.")
                    return redirect('products:product_detail', pk=pk)
            else:
                # Handle products without variants (backward compatibility)
                if not product.is_in_stock:
                    messages.error(request, f"Sorry, '{product.name}' is out of stock.")
                    return redirect('products:product_detail', pk=pk)
                
                messages.success(request, f"'{product.name}' added to cart successfully!")
            
            return redirect('products:product_detail', pk=pk)
            
        except Http404:
            messages.error(request, "Product not found.")
            return redirect('products:product_list')
    
    return redirect('products:product_list')

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
                # Store coupon in session (you can customize this)
                request.session['applied_coupon'] = coupon_code
                
                if coupon.discount_type == 'percentage':
                    messages.success(request, f"Coupon applied! You get {coupon.discount_value}% discount.")
                else:
                    messages.success(request, f"Coupon applied! You get ₹{coupon.discount_value} discount.")
                    
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code.")
    
    return redirect(request.META.get('HTTP_REFERER', 'products:home'))



# from django.shortcuts import render, get_object_or_404, redirect
# from django.core.paginator import Paginator
# from django.db.models import Q, Avg, F
# from django.contrib import messages
# from django.http import Http404
# from django.utils import timezone
# from .models import Product, Category, ProductReview, Coupon
# from decimal import Decimal


# def home(request):
#     """Home page view"""
#     return render(request, 'products/home.html')


# def product_list(request):
#     """Product listing with search, filter, sort and pagination"""
#     products = Product.objects.filter(is_active=True).select_related('category', 'brand').prefetch_related('images')
    
#     # Get filter parameters
#     search_query = request.GET.get('q', '')
#     category_filter = request.GET.get('category', '')
#     min_price = request.GET.get('min_price', '')
#     max_price = request.GET.get('max_price', '')
#     sort_by = request.GET.get('sort', '')
    
#     # Search functionality
#     if search_query:
#         products = products.filter(
#             Q(name__icontains=search_query) |
#             Q(description__icontains=search_query) |
#             Q(brand__name__icontains=search_query)
#         )
    
#     # Category filter
#     if category_filter:
#         products = products.filter(category__name=category_filter)
    
#     # Price range filter
#     if min_price:
#         try:
#             min_price_decimal = Decimal(min_price)
#             products = products.filter(price__gte=min_price_decimal)
#         except:
#             min_price = ''
    
#     if max_price:
#         try:
#             max_price_decimal = Decimal(max_price)
#             products = products.filter(price__lte=max_price_decimal)
#         except:
#             max_price = ''
    
#     # Sorting
#     if sort_by == 'price_low':
#         products = products.order_by('price')
#     elif sort_by == 'price_high':
#         products = products.order_by('-price')
#     elif sort_by == 'name_asc':
#         products = products.order_by('name')
#     elif sort_by == 'name_desc':
#         products = products.order_by('-name')
#     else:
#         products = products.order_by('-created_at')
    
#     # Pagination
#     paginator = Paginator(products, 12)  # 12 products per page
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
    
#     # Get active categories for filter
#     categories = Category.objects.filter(is_active=True)
    
#     # Build query string for pagination links
#     query_params = request.GET.copy()
#     if 'page' in query_params:
#         del query_params['page']
#     query_string = query_params.urlencode()
    
#     context = {
#         'page_obj': page_obj,
#         'products': page_obj.object_list,
#         'categories': categories,
#         'search_query': search_query,
#         'category_filter': category_filter,
#         'min_price': min_price,
#         'max_price': max_price,
#         'sort_by': sort_by,
#         'query_string': query_string,
#         'total_products': paginator.count,
#     }
    
#     return render(request, 'products/product_list.html', context)


# def men_products(request):
#     """Men's products listing"""
#     products = Product.objects.filter(is_active=True, category__name='Men').select_related('category', 'brand').prefetch_related('images')
    
#     # Get filter parameters
#     search_query = request.GET.get('q', '')
#     min_price = request.GET.get('min_price', '')
#     max_price = request.GET.get('max_price', '')
#     sort_by = request.GET.get('sort', '')
    
#     # Search functionality
#     if search_query:
#         products = products.filter(
#             Q(name__icontains=search_query) |
#             Q(description__icontains=search_query) |
#             Q(brand__name__icontains=search_query)
#         )
    
#     # Price range filter
#     if min_price:
#         try:
#             min_price_decimal = Decimal(min_price)
#             products = products.filter(price__gte=min_price_decimal)
#         except:
#             min_price = ''
    
#     if max_price:
#         try:
#             max_price_decimal = Decimal(max_price)
#             products = products.filter(price__lte=max_price_decimal)
#         except:
#             max_price = ''
    
#     # Sorting
#     if sort_by == 'price_low':
#         products = products.order_by('price')
#     elif sort_by == 'price_high':
#         products = products.order_by('-price')
#     elif sort_by == 'name_asc':
#         products = products.order_by('name')
#     elif sort_by == 'name_desc':
#         products = products.order_by('-name')
#     else:
#         products = products.order_by('-created_at')
    
#     # Pagination
#     paginator = Paginator(products, 12)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
    
#     # Build query string for pagination links
#     query_params = request.GET.copy()
#     if 'page' in query_params:
#         del query_params['page']
#     query_string = query_params.urlencode()
    
#     context = {
#         'page_obj': page_obj,
#         'products': page_obj.object_list,
#         'search_query': search_query,
#         'min_price': min_price,
#         'max_price': max_price,
#         'sort_by': sort_by,
#         'query_string': query_string,
#         'total_products': paginator.count,
#         'category_title': 'Men\'s Watches',
#     }
    
#     return render(request, 'products/category_products.html', context)


# def women_products(request):
#     """Women's products listing"""
#     products = Product.objects.filter(is_active=True, category__name='Women').select_related('category', 'brand').prefetch_related('images')
    
#     # Get filter parameters
#     search_query = request.GET.get('q', '')
#     min_price = request.GET.get('min_price', '')
#     max_price = request.GET.get('max_price', '')
#     sort_by = request.GET.get('sort', '')
    
#     # Search functionality
#     if search_query:
#         products = products.filter(
#             Q(name__icontains=search_query) |
#             Q(description__icontains=search_query) |
#             Q(brand__name__icontains=search_query)
#         )
    
#     # Price range filter
#     if min_price:
#         try:
#             min_price_decimal = Decimal(min_price)
#             products = products.filter(price__gte=min_price_decimal)
#         except:
#             min_price = ''
    
#     if max_price:
#         try:
#             max_price_decimal = Decimal(max_price)
#             products = products.filter(price__lte=max_price_decimal)
#         except:
#             max_price = ''
    
#     # Sorting
#     if sort_by == 'price_low':
#         products = products.order_by('price')
#     elif sort_by == 'price_high':
#         products = products.order_by('-price')
#     elif sort_by == 'name_asc':
#         products = products.order_by('name')
#     elif sort_by == 'name_desc':
#         products = products.order_by('-name')
#     else:
#         products = products.order_by('-created_at')
    
#     # Pagination
#     paginator = Paginator(products, 12)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
    
#     # Build query string for pagination links
#     query_params = request.GET.copy()
#     if 'page' in query_params:
#         del query_params['page']
#     query_string = query_params.urlencode()
    
#     context = {
#         'page_obj': page_obj,
#         'products': page_obj.object_list,
#         'search_query': search_query,
#         'min_price': min_price,
#         'max_price': max_price,
#         'sort_by': sort_by,
#         'query_string': query_string,
#         'total_products': paginator.count,
#         'category_title': 'Women\'s Watches',
#     }
    
#     return render(request, 'products/category_products.html', context)


# def product_detail(request, pk):
#     """Enhanced Product detail page with error handling and redirects"""
#     try:
#         # Check if product exists and is active
#         product = get_object_or_404(Product, pk=pk)
        
#         # If product is not active, redirect to product list with error message
#         if not product.is_active:
#             messages.error(request, f"Sorry, '{product.name}' is currently unavailable.")
#             return redirect('products:product_list')
        
#         # Check if category is active
#         if not product.category.is_active:
#             messages.error(request, f"Sorry, '{product.name}' is currently unavailable.")
#             return redirect('products:product_list')
        
#         # Check if brand is active (if product has a brand)
#         if product.brand and not product.brand.is_active:
#             messages.error(request, f"Sorry, '{product.name}' is currently unavailable.")
#             return redirect('products:product_list')
            
#     except Http404:
#         messages.error(request, "Product not found.")
#         return redirect('products:product_list')
    
#     # Get product images
#     images = product.images.all()
    
#     # Get product reviews with user information
#     reviews = ProductReview.objects.filter(
#         product=product, 
#         is_active=True
#     ).select_related('user').order_by('-created_at')
    
#     # Get related products from same category (exclude current product and inactive products)
#     related_products = Product.objects.filter(
#         category=product.category,
#         is_active=True,
#         category__is_active=True
#     ).exclude(pk=product.pk).select_related('category', 'brand').prefetch_related('images')[:4]
    
#     # Check for active coupons (you can customize this logic)
#     available_coupons = Coupon.objects.filter(
#         is_active=True,
#         valid_from__lte=timezone.now(),
#         valid_to__gte=timezone.now()
#     ).filter(
#         Q(usage_limit__isnull=True) | Q(usage_limit__gt=F('used_count'))
#     )[:3]  # Show top 3 available coupons
    
#     # Rating distribution for reviews
#     rating_distribution = {}
#     total_reviews = reviews.count()
#     for i in range(1, 6):
#         count = reviews.filter(rating=i).count()
#         percentage = (count / total_reviews * 100) if total_reviews > 0 else 0
#         rating_distribution[i] = {
#             'count': count,
#             'percentage': round(percentage, 1)
#         }
    
#     context = {
#         'product': product,
#         'images': images,
#         'related_products': related_products,
#         'reviews': reviews,
#         'available_coupons': available_coupons,
#         'rating_distribution': rating_distribution,
#         'breadcrumb_category': product.category.name,
#     }
    
#     return render(request, 'products/product_detail.html', context)


# # NEW: Add to cart with error handling
# def add_to_cart(request, pk):
#     """Add product to cart with proper error handling"""
#     if request.method == 'POST':
#         try:
#             product = get_object_or_404(Product, pk=pk)
            
#             # Check if product is available
#             if not product.is_active:
#                 messages.error(request, f"Sorry, '{product.name}' is currently unavailable.")
#                 return redirect('products:product_list')
            
#             # Check stock
#             if not product.is_in_stock:
#                 messages.error(request, f"Sorry, '{product.name}' is out of stock.")
#                 return redirect('products:product_detail', pk=pk)
            
#             # Add your cart logic here
#             # For now, just show success message
#             messages.success(request, f"'{product.name}' added to cart successfully!")
#             return redirect('products:product_detail', pk=pk)
            
#         except Http404:
#             messages.error(request, "Product not found.")
#             return redirect('products:product_list')
    
#     return redirect('products:product_list')


# # NEW: Apply coupon functionality
# def apply_coupon(request):
#     """Apply coupon with validation"""
#     if request.method == 'POST':
#         coupon_code = request.POST.get('coupon_code', '').strip().upper()
        
#         if not coupon_code:
#             messages.error(request, "Please enter a coupon code.")
#             return redirect(request.META.get('HTTP_REFERER', 'products:home'))
        
#         try:
#             coupon = Coupon.objects.get(code=coupon_code)
            
#             if not coupon.is_valid:
#                 messages.error(request, "This coupon is not valid or has expired.")
#             else:
#                 # Store coupon in session (you can customize this)
#                 request.session['applied_coupon'] = coupon_code
                
#                 if coupon.discount_type == 'percentage':
#                     messages.success(request, f"Coupon applied! You get {coupon.discount_value}% discount.")
#                 else:
#                     messages.success(request, f"Coupon applied! You get ₹{coupon.discount_value} discount.")
                    
#         except Coupon.DoesNotExist:
#             messages.error(request, "Invalid coupon code.")
    
#     return redirect(request.META.get('HTTP_REFERER', 'products:home'))

