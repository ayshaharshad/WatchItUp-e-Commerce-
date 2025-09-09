from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import user_passes_test, login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.views.decorators.http import require_http_methods

# Models
from products.models import Category, Product, ProductImage
from .forms import AdminLoginForm, CategoryForm, ProductForm

User = get_user_model()

# ---------------- DECORATORS ----------------
superuser_required = user_passes_test(
    lambda u: u.is_superuser, 
    login_url="admin_login"
)

# ---------------- LOGIN ----------------
def admin_login(request):
    if request.method == "POST":
        form = AdminLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_superuser:
                login(request, user)
                return redirect("dashboard")
            else:
                messages.error(request, "Only superusers can log in here.")
    else:
        form = AdminLoginForm()
    return render(request, "admin_panel/login.html", {"form": form})


@login_required(login_url="admin_login")
def admin_logout(request):
    logout(request)
    return redirect("admin_login")


# ---------------- DASHBOARD ----------------
@superuser_required
def dashboard(request):
    return render(request, "admin_panel/dashboard.html")



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
@require_http_methods(["GET", "POST"])  # SECURITY: Only allow GET and POST
def block_unblock_user(request, user_id):
    # SECURITY: Prevent blocking superusers
    user = get_object_or_404(User, id=user_id)
    
    if user.is_superuser:
        messages.error(request, "Cannot block/unblock superuser accounts.")
        return redirect("user_list")
    
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
        # Handle GET request (original functionality)
        user.is_active = not user.is_active
        user.save()
        status = "unblocked" if user.is_active else "blocked"
        messages.success(request, f"User '{user.username}' has been {status} successfully.")
    
    return redirect("user_list")


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
            return redirect("category_list")
    else:
        form = CategoryForm()
    return render(request, "admin_panel/add_category.html", {"form": form})


@superuser_required
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("category_list")
    return render(request, "admin_panel/edit_category.html", {"form": form})


@superuser_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.is_active = False
    category.save()
    return redirect("category_list")


# ---------------- PRODUCT MANAGEMENT ----------------
@superuser_required
def product_list(request):
    search = request.GET.get("q", "")
    products = Product.objects.filter(is_active=True)
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
            product = form.save()
            if "images" in request.FILES:
                for img in request.FILES.getlist("images"):
                    ProductImage.objects.create(product=product, image=img)
            messages.success(request, "Product added successfully.")
            return redirect("product_list")
        else:
            print(f"Form errors: {form.errors}")  # For debugging
    else:
        form = ProductForm()
    return render(request, "admin_panel/add_product.html", {"form": form})

@superuser_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == "POST":
        try:
            # Update product fields directly
            product.name = request.POST.get('name')
            product.category_id = request.POST.get('category')
            product.price = request.POST.get('price')
            product.original_price = request.POST.get('original_price') or None
            product.stock_quantity = int(request.POST.get('stock_quantity', 0))
            product.description = request.POST.get('description', '')
            
            product.save()
            
            # Handle images if uploaded
            uploaded_images = request.FILES.getlist('images')
            if uploaded_images:
                # Delete old images
                product.images.all().delete()
                # Add new images
                for img in uploaded_images:
                    ProductImage.objects.create(product=product, image=img)
            
            messages.success(request, "Product updated successfully!")
            return redirect("product_list")
            
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            print(f"Edit product error: {e}")
    
    # Get form for categories (we still need this for the dropdown)
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
    return redirect("product_list")
