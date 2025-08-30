# from django.contrib import admin
# from users.models import CustomUser
# from products.models import Category, Brand, Product, ProductImage


# # ---------------- USER ADMIN ----------------
# @admin.register(CustomUser)
# class CustomUserAdmin(admin.ModelAdmin):
#     list_display = ('email', 'username', 'phone_number', 'is_email_verified', 'is_staff', 'created_at')
#     list_filter = ('is_email_verified', 'is_staff', 'is_superuser')
#     search_fields = ('email', 'username', 'phone_number')
#     ordering = ('-created_at',)


# # ---------------- CATEGORY ADMIN ----------------
# @admin.register(Category)
# class CategoryAdmin(admin.ModelAdmin):
#     list_display = ('name', 'is_active', 'created_at')
#     list_filter = ('is_active',)
#     search_fields = ('name',)


# # ---------------- BRAND ADMIN ----------------
# @admin.register(Brand)
# class BrandAdmin(admin.ModelAdmin):
#     list_display = ('name', 'is_active')
#     list_filter = ('is_active',)
#     search_fields = ('name',)


# # ---------------- PRODUCT ADMIN ----------------
# class ProductImageInline(admin.TabularInline):
#     model = ProductImage
#     extra = 1


# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#     list_display = ('name', 'category', 'brand', 'price', 'is_active', 'created_at')
#     list_filter = ('category', 'brand', 'is_active')
#     search_fields = ('name', 'category__name', 'brand__name')
#     ordering = ('-created_at',)
#     inlines = [ProductImageInline]
