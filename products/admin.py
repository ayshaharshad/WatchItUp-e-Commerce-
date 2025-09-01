from django.contrib import admin
from .models import Category, Brand, Product, ProductImage


# ------------------ CATEGORY ------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)


# ------------------ BRAND ------------------
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


# ------------------ PRODUCT IMAGE INLINE ------------------
class ProductImageInline(admin.TabularInline):  # Or StackedInline for bigger forms
    model = ProductImage
    extra = 1   # Number of empty forms to show
    fields = ('image', 'created_at')
    readonly_fields = ('created_at',)


# ------------------ PRODUCT ------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'price', 'is_active', 'created_at')
    list_filter = ('category', 'brand', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    inlines = [ProductImageInline]   # Show product images inside Product admin page


# ------------------ PRODUCT IMAGE ------------------
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'created_at')
    list_filter = ('created_at',)
