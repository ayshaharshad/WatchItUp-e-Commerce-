from django.contrib import admin
from .models import (
    Category, Brand, Product, ProductImage, ProductReview, Coupon, 
    ProductVariant, ProductVariantImage, Cart, CartItem, 
    Order, OrderItem, OrderCancellation, OrderReturn,
    Wishlist, WishlistItem, Checkout, CheckoutItem
)

# ------------------ CATEGORY ------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    list_editable = ('is_active',)

# ------------------ BRAND ------------------
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('is_active',)

# ------------------ PRODUCT VARIANT IMAGE INLINE ------------------
class ProductVariantImageInline(admin.TabularInline):
    model = ProductVariantImage
    extra = 1
    fields = ('image', 'zoom_image', 'is_primary', 'created_at')
    readonly_fields = ('created_at',)

# ------------------ PRODUCT VARIANT INLINE ------------------
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('color', 'color_hex', 'price', 'original_price', 'stock_quantity', 'sku', 'is_active')
    readonly_fields = ('sku',)

# ------------------ PRODUCT IMAGE INLINE ------------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'zoom_image', 'is_primary', 'created_at')
    readonly_fields = ('created_at',)

# ------------------ PRODUCT REVIEW INLINE ------------------
class ProductReviewInline(admin.TabularInline):
    model = ProductReview
    extra = 0
    fields = ('user', 'variant', 'rating', 'review_text', 'is_active', 'created_at')
    readonly_fields = ('created_at',)

# ------------------ PRODUCT ------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'base_price', 'get_total_stock', 'is_active', 'created_at')
    list_filter = ('category', 'brand', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('base_price', 'is_active')
    inlines = [ProductVariantInline, ProductImageInline, ProductReviewInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'brand').prefetch_related('variants')
    
    def get_total_stock(self, obj):
        return obj.total_stock
    get_total_stock.short_description = 'Total Stock'

# ------------------ PRODUCT VARIANT ------------------
@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'color', 'price', 'original_price', 'stock_quantity', 'is_active', 'created_at')
    list_filter = ('color', 'is_active', 'created_at', 'product__category')
    search_fields = ('product__name', 'sku', 'color')
    list_editable = ('price', 'original_price', 'stock_quantity', 'is_active')
    inlines = [ProductVariantImageInline]
    readonly_fields = ('sku', 'created_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')

# ------------------ PRODUCT VARIANT IMAGE ------------------
@admin.register(ProductVariantImage)
class ProductVariantImageAdmin(admin.ModelAdmin):
    list_display = ('variant', 'is_primary', 'created_at')
    list_filter = ('is_primary', 'created_at')
    list_editable = ('is_primary',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('variant__product')

# ------------------ PRODUCT IMAGE ------------------
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'is_primary', 'created_at')
    list_filter = ('is_primary', 'created_at')
    list_editable = ('is_primary',)

# ------------------ PRODUCT REVIEW ------------------
@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'variant', 'user', 'rating', 'is_active', 'created_at')
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

# ------------------ CART ITEM INLINE ------------------
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ('product', 'variant', 'quantity', 'added_at')
    readonly_fields = ('added_at',)
    raw_id_fields = ('product', 'variant')

# ------------------ CART ------------------
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_total_items', 'get_subtotal', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'get_total_items', 'get_subtotal')
    inlines = [CartItemInline]
    
    def get_total_items(self, obj):
        return obj.total_items
    get_total_items.short_description = 'Total Items'
    
    def get_subtotal(self, obj):
        return f'₹{obj.subtotal}'
    get_subtotal.short_description = 'Subtotal'

# ------------------ CART ITEM ------------------
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'variant', 'quantity', 'get_item_total', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('cart__user__username', 'product__name')
    readonly_fields = ('added_at', 'updated_at', 'get_item_total')
    raw_id_fields = ('cart', 'product', 'variant')
    
    def get_item_total(self, obj):
        return f'₹{obj.item_total}'
    get_item_total.short_description = 'Item Total'

# ------------------ ORDER ITEM INLINE ------------------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product_name', 'variant_name', 'price', 'quantity', 'item_total', 'status')
    readonly_fields = ('product_name', 'variant_name', 'price', 'quantity', 'item_total')

# ------------------ ORDER ------------------
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'status', 'payment_method', 'total', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('order_id', 'user__username', 'user__email', 'shipping_full_name', 'shipping_phone')
    readonly_fields = ('order_id', 'created_at', 'updated_at')
    list_editable = ('status',)
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'user', 'status', 'payment_method', 'notes')
        }),
        ('Shipping Address', {
            'fields': (
                'shipping_full_name', 'shipping_phone',
                'shipping_line1', 'shipping_line2',
                'shipping_city', 'shipping_state',
                'shipping_postal_code', 'shipping_country'
            )
        }),
        ('Pricing', {
            'fields': ('subtotal', 'tax', 'shipping_charge', 'discount', 'total')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'delivered_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

# ------------------ ORDER ITEM ------------------
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'variant_name', 'quantity', 'price', 'item_total', 'status')
    list_filter = ('status', 'created_at')
    search_fields = ('order__order_id', 'product_name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('order', 'product', 'variant')

# ------------------ ORDER CANCELLATION ------------------
@admin.register(OrderCancellation)
class OrderCancellationAdmin(admin.ModelAdmin):
    list_display = ('get_order_id', 'get_item_name', 'cancelled_by', 'cancelled_at')
    list_filter = ('cancelled_at',)
    search_fields = ('order__order_id', 'cancelled_by__username', 'reason')
    readonly_fields = ('cancelled_at',)
    raw_id_fields = ('order', 'order_item', 'cancelled_by')
    
    def get_order_id(self, obj):
        return obj.order.order_id if obj.order else 'Item Cancellation'
    get_order_id.short_description = 'Order ID'
    
    def get_item_name(self, obj):
        return obj.order_item.product_name if obj.order_item else 'Full Order'
    get_item_name.short_description = 'Item'

# ------------------ ORDER RETURN ------------------
@admin.register(OrderReturn)
class OrderReturnAdmin(admin.ModelAdmin):
    list_display = ('order', 'requested_by', 'approved', 'requested_at', 'approved_at')
    list_filter = ('approved', 'requested_at', 'approved_at')
    search_fields = ('order__order_id', 'requested_by__username', 'reason')
    readonly_fields = ('requested_at',)
    list_editable = ('approved',)
    raw_id_fields = ('order', 'requested_by')

# ------------------ WISHLIST ITEM INLINE ------------------
class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0
    fields = ('product', 'variant', 'added_at')
    readonly_fields = ('added_at',)
    raw_id_fields = ('product', 'variant')

# ------------------ WISHLIST ------------------
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_total_items', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'get_total_items')
    inlines = [WishlistItemInline]
    
    def get_total_items(self, obj):
        return obj.total_items
    get_total_items.short_description = 'Total Items'

# ------------------ WISHLIST ITEM ------------------
@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('wishlist', 'product', 'variant', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('wishlist__user__username', 'product__name')
    readonly_fields = ('added_at',)
    raw_id_fields = ('wishlist', 'product', 'variant')

# ------------------ CHECKOUT ITEM INLINE ------------------
class CheckoutItemInline(admin.TabularInline):
    model = CheckoutItem
    extra = 0
    fields = ('product_name', 'variant_name', 'price', 'quantity', 'item_total', 'is_available')
    readonly_fields = ('product_name', 'variant_name', 'price', 'quantity', 'item_total', 'is_available')

# ------------------ CHECKOUT ------------------
@admin.register(Checkout)
class CheckoutAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'total', 'payment_method', 'is_completed', 'created_at', 'expires_at')
    list_filter = ('is_completed', 'payment_method', 'created_at')
    search_fields = ('session_id', 'user__username')
    readonly_fields = ('session_id', 'created_at', 'expires_at')
    raw_id_fields = ('user', 'address', 'order')
    inlines = [CheckoutItemInline]
    
    fieldsets = (
        ('Session Info', {
            'fields': ('session_id', 'user', 'is_completed', 'order')
        }),
        ('Address', {
            'fields': ('address',)
        }),
        ('Pricing', {
            'fields': ('subtotal', 'tax', 'shipping_charge', 'discount', 'total')
        }),
        ('Payment', {
            'fields': ('payment_method',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at')
        }),
    )

# ------------------ CHECKOUT ITEM ------------------
@admin.register(CheckoutItem)
class CheckoutItemAdmin(admin.ModelAdmin):
    list_display = ('checkout', 'product_name', 'variant_name', 'quantity', 'price', 'item_total', 'is_available')
    list_filter = ('is_available', 'created_at')
    search_fields = ('checkout__session_id', 'product_name')
    readonly_fields = ('created_at',)
    raw_id_fields = ('checkout', 'product', 'variant')

# Customize Admin Site Header
admin.site.site_header = 'WatchItUp Admin'
admin.site.site_title = 'WatchItUp Admin Portal'
admin.site.index_title = 'Welcome to WatchItUp Administration'

