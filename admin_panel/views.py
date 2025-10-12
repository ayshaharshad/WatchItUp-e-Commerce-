from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import user_passes_test, login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db import transaction



# Models
from products.models import Category, Product, ProductImage, ProductVariant, ProductVariantImage, Order, OrderItem
from .forms import (
    AdminLoginForm, CategoryForm, ProductForm, ProductVariantForm, 
    ProductVariantEditForm, BulkVariantForm, OrderStatusForm, OrderFilterForm
)

User = get_user_model()

# ---------------- DECORATORS ----------------
superuser_required = user_passes_test(
    lambda u: u.is_superuser, 
    login_url="admin_panel:admin_login"
)

# ---------------- LOGIN ----------------
def admin_login(request):
    if request.method == "POST":
        form = AdminLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_superuser:
                login(request, user)
                return redirect("admin_panel:dashboard")
            else:
                messages.error(request, "Only superusers can log in here.")
    else:
        form = AdminLoginForm()
    return render(request, "admin_panel/login.html", {"form": form})

@login_required(login_url="admin_panel:admin_login")
def admin_logout(request):
    logout(request)
    return redirect("admin_panel:admin_login")

# ---------------- DASHBOARD ----------------
@superuser_required
def dashboard(request):
    total_products = Product.objects.filter(is_active=True).count()
    total_variants = ProductVariant.objects.filter(is_active=True).count()
    total_stock = ProductVariant.objects.filter(is_active=True).aggregate(
        total=Sum('stock_quantity'))['total'] or 0
    low_stock_variants = ProductVariant.objects.filter(
        is_active=True, stock_quantity__lte=5, stock_quantity__gt=0
    ).count()
    
    context = {
        'total_products': total_products,
        'total_variants': total_variants,
        'total_stock': total_stock,
        'low_stock_variants': low_stock_variants,
    }
    return render(request, "admin_panel/dashboard.html", context)

# ---------------- USER MANAGEMENT ----------------
@superuser_required
def user_list(request):
    search = request.GET.get("q", "")
    users = User.objects.filter(is_superuser=False)
    if search:
        users = users.filter(Q(username__icontains=search) | Q(email__icontains=search))
    users = users.order_by("-id")
    paginator = Paginator(users, 10)
    page = request.GET.get("page")
    users = paginator.get_page(page)
    return render(request, "admin_panel/user_list.html", {"users": users, "search": search})

@superuser_required
@require_http_methods(["GET", "POST"])
def block_unblock_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if user.is_superuser:
        messages.error(request, "Cannot block/unblock superuser accounts.")
        return redirect("admin_panel:user_list")

    if request.method == "POST":
        action = request.POST.get('action')

        if action == 'block':
            if user.is_active:
                user.is_active = False
                user.save()
                messages.success(request, f"User '{user.username}' has been blocked successfully.")
            else:
                messages.info(request, f"User '{user.username}' is already blocked.")

        elif action == 'unblock':
            if not user.is_active:
                user.is_active = True
                user.save()
                messages.success(request, f"User '{user.username}' has been unblocked successfully.")
            else:
                messages.info(request, f"User '{user.username}' is already active.")
        else:
            messages.error(request, "Invalid action specified.")
    else:
        user.is_active = not user.is_active
        user.save()
        status = "unblocked" if user.is_active else "blocked"
        messages.success(request, f"User '{user.username}' has been {status} successfully.")

    return redirect("admin_panel:user_list")

# ---------------- CATEGORY MANAGEMENT ----------------
@superuser_required
def category_list(request):
    search = request.GET.get("q", "")
    categories = Category.objects.filter(is_active=True)
    if search:
        categories = categories.filter(name__icontains=search)
    categories = categories.order_by("-id")
    paginator = Paginator(categories, 10)
    page = request.GET.get("page")
    categories = paginator.get_page(page)
    return render(request, "admin_panel/category_list.html", {"categories": categories, "search": search})

@superuser_required
def add_category(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category added successfully.")
            return redirect("admin_panel:category_list")
    else:
        form = CategoryForm()
    return render(request, "admin_panel/add_category.html", {"form": form})

@superuser_required
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Category updated successfully.")
        return redirect("admin_panel:category_list")
    return render(request, "admin_panel/edit_category.html", {"form": form, "category": category})

@superuser_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.is_active = False
    category.save()
    messages.success(request, "Category deleted successfully.")
    return redirect("admin_panel:category_list")

# ---------------- PRODUCT MANAGEMENT ----------------
@superuser_required
def product_list(request):
    search = request.GET.get("q", "")
    products = Product.objects.filter(is_active=True).select_related('category', 'brand').prefetch_related('variants')
    if search:
        products = products.filter(Q(name__icontains=search) | Q(description__icontains=search))
    products = products.order_by("-id")
    paginator = Paginator(products, 10)
    page = request.GET.get("page")
    products = paginator.get_page(page)
    return render(request, "admin_panel/product_list.html", {"products": products, "search": search})


@superuser_required
def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save the product
                    product = form.save()
                    
                    # Handle multiple images (now potentially cropped)
                    uploaded_images = request.FILES.getlist("images")
                    if uploaded_images:
                        for img in uploaded_images:
                            # Optional: Validate image size/type if needed after cropping
                            if img.size > 5 * 1024 * 1024:  # Example: Limit to 5MB
                                raise ValueError("Image too large after cropping.")
                            ProductImage.objects.create(product=product, image=img)
                    
                    messages.success(
                        request, 
                        f"Product '{product.name}' added successfully! You can now add variants with specific colors, sizes, and prices."
                    )
                    return redirect("admin_panel:add_product_variant", product_id=product.id)
            
            except Exception as e:
                messages.error(request, f"Error saving product: {str(e)}")
                print(f"Product creation error: {e}")  # For debugging
        else:
            # (Existing error handling remains)
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        error_messages.append(error)
                    else:
                        error_messages.append(f"{field.title()}: {error}")
            
            if error_messages:
                messages.error(request, "Please correct the following errors: " + "; ".join(error_messages))
            else:
                messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm()
    
    return render(request, "admin_panel/add_product.html", {"form": form})

# @superuser_required
# def add_product(request):
#     if request.method == "POST":
#         form = ProductForm(request.POST, request.FILES)
#         if form.is_valid():
#             try:
#                 with transaction.atomic():
#                     # Save the product
#                     product = form.save()
                    
#                     # Handle multiple images
#                     uploaded_images = request.FILES.getlist("images")
#                     if uploaded_images:
#                         for img in uploaded_images:
#                             ProductImage.objects.create(product=product, image=img)
                    
#                     messages.success(
#                         request, 
#                         f"Product '{product.name}' added successfully! You can now add variants with specific colors, sizes, and prices."
#                     )
#                     return redirect("admin_panel:add_product_variant", product_id=product.id)
            
#             except Exception as e:
#                 messages.error(request, f"Error saving product: {str(e)}")
#                 print(f"Product creation error: {e}")  # For debugging
#         else:
#             # Display form errors
#             error_messages = []
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     if field == '__all__':
#                         error_messages.append(error)
#                     else:
#                         error_messages.append(f"{field.title()}: {error}")
            
#             if error_messages:
#                 messages.error(request, "Please correct the following errors: " + "; ".join(error_messages))
#             else:
#                 messages.error(request, "Please correct the errors below.")
#     else:
#         form = ProductForm()
    
#     return render(request, "admin_panel/add_product.html", {"form": form})
@superuser_required
def edit_product(request, pk):
    """Fixed edit_product view to handle product base info only"""
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        try:
            # Update only the base product information
            product.name = request.POST.get('name')
            product.category_id = request.POST.get('category')
            product.brand_id = request.POST.get('brand') or None
            product.base_price = request.POST.get('base_price')
            product.stock = request.POST.get('stock', 0)  # NEW: Handle stock field
            product.description = request.POST.get('description', '')

            product.save()

            # Handle ONLY main product images (not variant images)
            uploaded_images = request.FILES.getlist('images')
            if uploaded_images:
                # Clear only ProductImage, NOT ProductVariantImage
                product.images.all().delete()
                for img in uploaded_images:
                    ProductImage.objects.create(product=product, image=img)

            messages.success(request, "Product updated successfully!")
            return redirect("admin_panel:product_list")

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    form = ProductForm(instance=product)
    return render(request, "admin_panel/edit_product.html", {
        "form": form,
        "product": product
    })

@superuser_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = False
    product.save()
    messages.success(request, "Product deleted successfully.")
    return redirect("admin_panel:product_list")

# ---------------- PRODUCT VARIANT MANAGEMENT ----------------
@superuser_required
def variant_list(request):
    search = request.GET.get("q", "")
    product_filter = request.GET.get("product", "")
    color_filter = request.GET.get("color", "")
    
    variants = ProductVariant.objects.filter(is_active=True).select_related('product')
    
    if search:
        variants = variants.filter(
            Q(product__name__icontains=search) | 
            Q(sku__icontains=search) |
            Q(color__icontains=search)
        )
    
    if product_filter:
        variants = variants.filter(product_id=product_filter)
        
    if color_filter:
        variants = variants.filter(color=color_filter)
    
    variants = variants.order_by("-id")
    
    paginator = Paginator(variants, 15)
    page = request.GET.get("page")
    variants = paginator.get_page(page)
    
    products = Product.objects.filter(is_active=True).order_by('name')
    colors = ProductVariant.COLOR_CHOICES
    
    context = {
        'variants': variants,
        'search': search,
        'products': products,
        'colors': colors,
        'product_filter': product_filter,
        'color_filter': color_filter,
    }
    
    return render(request, "admin_panel/variant_list.html", context)

@superuser_required
def add_product_variant(request, product_id=None):
    """Fixed add_product_variant to handle variant images properly"""
    product = None
    if product_id:
        product = get_object_or_404(Product, pk=product_id, is_active=True)

    if request.method == "POST":
        form = ProductVariantForm(request.POST)
        if form.is_valid():
            variant = form.save()
            
            # Handle variant images (separate from product images)
            if "images" in request.FILES:
                for i, img in enumerate(request.FILES.getlist("images")):
                    ProductVariantImage.objects.create(
                        variant=variant, 
                        image=img,
                        is_primary=(i == 0)  # First image is primary
                    )
            messages.success(request, f"Variant '{variant}' added successfully.")
            return redirect("admin_panel:variant_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        initial_data = {}
        if product:
            initial_data['product'] = product
        form = ProductVariantForm(initial=initial_data)

    context = {
        'form': form,
        'product': product,
    }
    return render(request, "admin_panel/add_variant.html", context)


@superuser_required
def edit_product_variant(request, pk):
    """Fixed edit_product_variant view to handle variant images separately"""
    variant = get_object_or_404(ProductVariant, pk=pk)

    if request.method == "POST":
        form = ProductVariantEditForm(request.POST, instance=variant)
        if form.is_valid():
            form.save()
            
            # Handle variant images separately - only if new images are uploaded
            uploaded_images = request.FILES.getlist('images')
            if uploaded_images:
                # Clear only THIS variant's images, not the main product images
                variant.images.all().delete()
                for i, img in enumerate(uploaded_images):
                    ProductVariantImage.objects.create(
                        variant=variant,
                        image=img,
                        is_primary=(i == 0)  # First image is primary
                    )
            messages.success(request, "Variant updated successfully!")
            return redirect("admin_panel:variant_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductVariantEditForm(instance=variant)

    context = {
        'form': form,
        'variant': variant,
    }
    return render(request, "admin_panel/edit_variant.html", context)

@superuser_required
def delete_product_variant(request, pk):
    variant = get_object_or_404(ProductVariant, pk=pk)
    variant.is_active = False
    variant.save()
    messages.success(request, f"Variant '{variant}' deleted successfully.")
    return redirect("admin_panel:variant_list")

@superuser_required
def bulk_create_variants(request):
    if request.method == "POST":
        form = BulkVariantForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            colors = form.cleaned_data['colors']
            base_price = form.cleaned_data['base_price']
            stock_quantity = form.cleaned_data['stock_quantity']
            
            created_count = 0
            with transaction.atomic():
                for color in colors:
                    ProductVariant.objects.create(
                        product=product,
                        color=color,
                        price=base_price,
                        stock_quantity=stock_quantity
                    )
                    created_count += 1
            
            messages.success(request, f"Successfully created {created_count} variants for '{product.name}'.")
            return redirect("admin_panel:variant_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = BulkVariantForm()
    
    return render(request, "admin_panel/bulk_create_variants.html", {"form": form})

@superuser_required
def variant_stock_update(request):
    if request.method == "POST":
        updates = request.POST.getlist('stock_updates')
        updated_count = 0
        
        for update in updates:
            if update.strip():
                try:
                    variant_id, new_stock = update.split(':')
                    variant = ProductVariant.objects.get(id=int(variant_id), is_active=True)
                    variant.stock_quantity = int(new_stock)
                    variant.save()
                    updated_count += 1
                except (ValueError, ProductVariant.DoesNotExist):
                    continue
        
        messages.success(request, f"Updated stock for {updated_count} variants.")
        return redirect("admin_panel:variant_list")
    
    low_stock_variants = ProductVariant.objects.filter(
        is_active=True,
        stock_quantity__lte=5
    ).select_related('product').order_by('stock_quantity')
    
    return render(request, "admin_panel/variant_stock_update.html", {
        'low_stock_variants': low_stock_variants
    })

@superuser_required  
def product_variant_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    variants = product.variants.filter(is_active=True).prefetch_related('images').order_by('color')
    
    context = {
        'product': product,
        'variants': variants,
    }
    return render(request, "admin_panel/product_variant_detail.html", context)


# -------------------- ORDER MANAGEMENT --------------------

@superuser_required
def order_list(request):
    """List all orders with search, filter, sort and pagination"""
    # Get filter parameters
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    payment_filter = request.GET.get('payment_method', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    sort_by = request.GET.get('sort', '-created_at')
    
    # Base queryset
    orders = Order.objects.select_related('user').prefetch_related('items').all()
    
    # Apply search
    if search:
        orders = orders.filter(
            Q(order_id__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(shipping_full_name__icontains=search) |
            Q(shipping_phone__icontains=search)
        )
    
    # Apply filters
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if payment_filter:
        orders = orders.filter(payment_method=payment_filter)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            orders = orders.filter(created_at__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            orders = orders.filter(created_at__lte=date_to_obj)
        except ValueError:
            pass
    
    # Apply sorting
    valid_sort_fields = [
        'created_at', '-created_at',
        'total', '-total',
        'status', '-status',
        'order_id', '-order_id'
    ]
    if sort_by in valid_sort_fields:
        orders = orders.order_by(sort_by)
    else:
        orders = orders.order_by('-created_at')
    
    # Statistics
    total_orders = orders.count()
    total_revenue = orders.aggregate(total=Sum('total'))['total'] or 0
    
    # Pagination
    paginator = Paginator(orders, 20)
    page = request.GET.get('page')
    orders_page = paginator.get_page(page)
    
    # Filter form
    filter_form = OrderFilterForm(request.GET)
    
    context = {
        'orders': orders_page,
        'filter_form': filter_form,
        'search': search,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'date_from': date_from,
        'date_to': date_to,
        'sort_by': sort_by,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
    }
    
    return render(request, 'admin_panel/order_list.html', context)


@superuser_required
def order_detail(request, order_id):
    """View detailed information about a specific order"""
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related('items__product', 'items__variant'),
        order_id=order_id
    )
    
    # Get order items
    order_items = order.items.all()
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    
    return render(request, 'admin_panel/order_detail.html', context)


@superuser_required
def update_order_status(request, order_id):
    """Update order status with proper timezone import"""
    order = get_object_or_404(Order, order_id=order_id)
    
    if request.method == 'POST':
        form = OrderStatusForm(request.POST, current_status=order.status)
        if form.is_valid():
            new_status = form.cleaned_data['status']
            notes = form.cleaned_data.get('notes', '')
            
            # Update order status
            old_status = order.status
            order.status = new_status
            
            # If status is delivered, set delivered_at timestamp
            if new_status == 'delivered' and not order.delivered_at:
                order.delivered_at = timezone.now()  # timezone is imported at top
            
            # If order is cancelled, restore stock
            if new_status == 'cancelled' and old_status != 'cancelled':
                for item in order.items.all():
                    if item.variant:
                        item.variant.stock_quantity += item.quantity
                        item.variant.save()
            
            # If order was cancelled and now confirmed, reduce stock again
            if old_status == 'cancelled' and new_status in ['confirmed', 'pending']:
                for item in order.items.all():
                    if item.variant:
                        item.variant.stock_quantity -= item.quantity
                        item.variant.save()
            
            # Add notes if provided
            if notes:
                timestamp = timezone.now().strftime('%Y-%m-%d %H:%M')
                new_note = f"[{timestamp}] Status changed from {old_status} to {new_status}: {notes}"
                if order.notes:
                    order.notes = f"{order.notes}\n{new_note}"
                else:
                    order.notes = new_note
            
            order.save()
            
            messages.success(request, f"Order {order.order_id} status updated to {order.get_status_display()}")
            return redirect('admin_panel:order_detail', order_id=order.order_id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = OrderStatusForm(current_status=order.status)
    
    context = {
        'order': order,
        'form': form,
    }
    
    return render(request, 'admin_panel/update_order_status.html', context)


@superuser_required
def cancel_order(request, order_id):
    """Cancel an order and restore stock"""
    order = get_object_or_404(Order, order_id=order_id)
    
    if not order.can_cancel:
        messages.error(request, "This order cannot be cancelled.")
        return redirect('admin_panel:order_detail', order_id=order.order_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'Cancelled by admin')
        
        # Update order status
        order.status = 'cancelled'
        order.notes = f"{order.notes}\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] Cancelled: {reason}" if order.notes else f"Cancelled: {reason}"
        order.save()
        
        # Restore stock
        for item in order.items.all():
            if item.variant:
                item.variant.stock_quantity += item.quantity
                item.variant.save()
        
        # Create cancellation record
        from products.models import OrderCancellation
        OrderCancellation.objects.create(
            order=order,
            reason=reason,
            cancelled_by=request.user
        )
        
        messages.success(request, f"Order {order.order_id} has been cancelled and stock restored.")
        return redirect('admin_panel:order_detail', order_id=order.order_id)
    
    context = {
        'order': order,
    }
    
    return render(request, 'admin_panel/cancel_order.html', context)


@superuser_required
def order_inventory_report(request):
    """View inventory/stock management report"""
    # Get all variants with stock information
    variants = ProductVariant.objects.filter(
        is_active=True
    ).select_related('product').order_by('stock_quantity')
    
    # Low stock variants (stock <= 10)
    low_stock = variants.filter(stock_quantity__lte=10)
    
    # Out of stock variants
    out_of_stock = variants.filter(stock_quantity=0)
    
    # Get recent orders to show stock movement
    recent_orders = Order.objects.filter(
        created_at__gte=timezone.now() - timezone.timedelta(days=30)
    ).select_related('user').order_by('-created_at')[:10]
    
    # Calculate stock statistics
    total_variants = variants.count()
    low_stock_count = low_stock.count()
    out_of_stock_count = out_of_stock.count()
    total_stock_value = sum(v.price * v.stock_quantity for v in variants)
    
    context = {
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'recent_orders': recent_orders,
        'total_variants': total_variants,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'total_stock_value': total_stock_value,
    }
    
    return render(request, 'admin_panel/order_inventory_report.html', context)


@superuser_required
def clear_order_filters(request):
    """Clear all order filters and redirect to order list"""
    return redirect('admin_panel:order_list')









