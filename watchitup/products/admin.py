from django.contrib import admin
from .models import Category, Brand, Product, ProductImage, ProductReview, Coupon


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
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'created_at')
    readonly_fields = ('created_at',)


# ------------------ PRODUCT REVIEW INLINE ------------------
class ProductReviewInline(admin.TabularInline):
    model = ProductReview
    extra = 0
    fields = ('user', 'rating', 'review_text', 'is_active', 'created_at')
    readonly_fields = ('created_at',)


# ------------------ PRODUCT ------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'price', 'original_price', 'stock_quantity', 'is_active', 'created_at')
    list_filter = ('category', 'brand', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('price', 'original_price', 'stock_quantity', 'is_active')
    inlines = [ProductImageInline, ProductReviewInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'brand')


# ------------------ PRODUCT IMAGE ------------------
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'created_at')
    list_filter = ('created_at',)


# ------------------ PRODUCT REVIEW ------------------
@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'is_active', 'created_at')
    list_filter = ('rating', 'is_active', 'created_at')
    search_fields = ('product__name', 'user__username', 'review_text')
    list_editable = ('is_active',)
    readonly_fields = ('created_at',)


# ------------------ COUPON ------------------
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'valid_from', 'valid_to', 'is_active', 'used_count', 'usage_limit')
    list_filter = ('discount_type', 'is_active', 'valid_from', 'valid_to')
    search_fields = ('code',)
    list_editable = ('is_active',)
    readonly_fields = ('used_count',)
    
    fieldsets = (
        ('Coupon Details', {
            'fields': ('code', 'discount_type', 'discount_value', 'minimum_amount')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_to', 'is_active')
        }),
        ('Usage Limits', {
            'fields': ('usage_limit', 'used_count')
        }),
    )

