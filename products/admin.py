from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    Category, Brand, Product, ProductImage, ProductReview, Coupon, CouponUsage,
    ProductVariant, ProductVariantImage, Cart, CartItem, 
    Order, OrderItem, OrderCancellation, OrderReturn, RazorpayPayment,
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

# ------------------ COUPON USAGE INLINE ------------------
class CouponUsageInline(admin.TabularInline):
    model = CouponUsage
    extra = 0
    fields = ('user', 'order', 'discount_amount', 'used_at')
    readonly_fields = ('user', 'order', 'discount_amount', 'used_at')
    can_delete = False

# ------------------ COUPON ------------------
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'minimum_amount', 'valid_from', 'valid_to', 
                    'is_active', 'used_count', 'usage_limit', 'get_validity_status')
    list_filter = ('discount_type', 'is_active', 'valid_from', 'valid_to')
    search_fields = ('code',)
    list_editable = ('is_active',)
    readonly_fields = ('used_count',)
    inlines = [CouponUsageInline]
    
    fieldsets = (
        ('Coupon Details', {
            'fields': ('code', 'discount_type', 'discount_value', 'minimum_amount', 'max_discount')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_to', 'is_active')
        }),
        ('Usage Limits', {
            'fields': ('usage_limit', 'usage_per_user', 'used_count')
        }),
    )
    
    def get_validity_status(self, obj):
        if obj.is_valid:
            return format_html('<span style="color: green;">✓ Valid</span>')
        return format_html('<span style="color: red;">✗ Invalid</span>')
    get_validity_status.short_description = 'Status'

# ------------------ COUPON USAGE ------------------
@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ('coupon', 'user', 'order', 'discount_amount', 'used_at')
    list_filter = ('used_at', 'coupon')
    search_fields = ('coupon__code', 'user__username', 'order__order_id')
    readonly_fields = ('coupon', 'user', 'order', 'discount_amount', 'used_at')
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

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

# ------------------ RAZORPAY PAYMENT INLINE ------------------
class RazorpayPaymentInline(admin.TabularInline):
    model = RazorpayPayment
    extra = 0
    fields = ('razorpay_order_id', 'razorpay_payment_id', 'amount', 'status', 'created_at')
    readonly_fields = ('razorpay_order_id', 'razorpay_payment_id', 'amount', 'status', 'created_at')
    can_delete = False

# ------------------ ORDER ITEM INLINE ------------------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product_name', 'variant_name', 'price', 'quantity', 'item_total', 'status')
    readonly_fields = ('product_name', 'variant_name', 'price', 'quantity', 'item_total')

# ------------------ ORDER CANCELLATION INLINE ------------------
class OrderCancellationInline(admin.TabularInline):
    model = OrderCancellation
    extra = 0
    fields = ('cancellation_type', 'reason', 'refund_amount', 'refund_status', 'cancelled_at')
    readonly_fields = ('cancellation_type', 'reason', 'refund_amount', 'cancelled_at')

# ------------------ ORDER RETURN INLINE ------------------
class OrderReturnInline(admin.TabularInline):
    model = OrderReturn
    extra = 0
    fields = ('reason', 'status', 'refund_amount', 'refund_status', 'requested_at')
    readonly_fields = ('reason', 'requested_at')

# ------------------ ORDER ------------------
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'status', 'payment_method', 'payment_status', 
                    'get_total', 'created_at', 'get_order_actions')
    list_filter = ('status', 'payment_method', 'payment_status', 'created_at')
    search_fields = ('order_id', 'user__username', 'user__email', 'shipping_full_name', 'shipping_phone')
    readonly_fields = ('order_id', 'created_at', 'updated_at', 'cancelled_at')
    list_editable = ('status',)
    inlines = [OrderItemInline, RazorpayPaymentInline, OrderCancellationInline, OrderReturnInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'user', 'status', 'payment_method', 'payment_status', 'notes')
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
            'fields': ('subtotal', 'tax', 'shipping_charge', 'discount', 'coupon', 'total')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'delivered_at', 'cancelled_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'coupon')
    
    def get_total(self, obj):
        return f'₹{obj.total}'
    get_total.short_description = 'Total'
    
    def get_order_actions(self, obj):
        actions = []
        if obj.status == 'pending':
            actions.append('⏳ Pending')
        elif obj.status == 'confirmed':
            actions.append('✓ Confirmed')
        elif obj.status == 'delivered':
            actions.append('📦 Delivered')
        elif obj.status == 'cancelled':
            actions.append('✗ Cancelled')
        
        if obj.payment_status == 'completed':
            actions.append('💰 Paid')
        elif obj.payment_status == 'pending':
            actions.append('⏰ Payment Pending')
        
        return ' | '.join(actions)
    get_order_actions.short_description = 'Actions'
    
    actions = ['mark_as_confirmed', 'mark_as_shipped', 'mark_as_delivered']
    
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'{updated} orders marked as confirmed.')
    mark_as_confirmed.short_description = 'Mark selected orders as Confirmed'
    
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(status='shipped')
        self.message_user(request, f'{updated} orders marked as shipped.')
    mark_as_shipped.short_description = 'Mark selected orders as Shipped'
    
    def mark_as_delivered(self, request, queryset):
        updated = queryset.update(status='delivered', delivered_at=timezone.now())
        self.message_user(request, f'{updated} orders marked as delivered.')
    mark_as_delivered.short_description = 'Mark selected orders as Delivered'

# ------------------ RAZORPAY PAYMENT ------------------
@admin.register(RazorpayPayment)
class RazorpayPaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'razorpay_order_id', 'razorpay_payment_id', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('razorpay_order_id', 'razorpay_payment_id', 'order__order_id')
    readonly_fields = ('order', 'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature',
                      'amount', 'currency', 'status', 'created_at', 'updated_at')
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

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
    list_display = ('get_order_id', 'cancellation_type', 'get_item_name', 'refund_amount', 
                    'refund_status', 'cancelled_by', 'cancelled_at')
    list_filter = ('cancellation_type', 'refund_status', 'cancelled_at')
    search_fields = ('order__order_id', 'cancelled_by__username', 'reason')
    readonly_fields = ('order', 'order_item', 'cancellation_type', 'reason', 'refund_amount',
                      'cancelled_by', 'cancelled_at')
    list_editable = ('refund_status',)
    raw_id_fields = ('order', 'order_item', 'cancelled_by')
    
    fieldsets = (
        ('Cancellation Details', {
            'fields': ('order', 'order_item', 'cancellation_type', 'reason')
        }),
        ('Refund Information', {
            'fields': ('refund_amount', 'refund_status', 'processed_at')
        }),
        ('Metadata', {
            'fields': ('cancelled_by', 'cancelled_at')
        }),
    )
    
    def get_order_id(self, obj):
        return obj.order.order_id
    get_order_id.short_description = 'Order ID'
    
    def get_item_name(self, obj):
        return obj.order_item.product_name if obj.order_item else 'Full Order'
    get_item_name.short_description = 'Item'
    
    actions = ['mark_refund_processed']
    
    def mark_refund_processed(self, request, queryset):
        updated = queryset.update(refund_status='processed', processed_at=timezone.now())
        self.message_user(request, f'{updated} refunds marked as processed.')
    mark_refund_processed.short_description = 'Mark refund as Processed'

# ------------------ ORDER RETURN ------------------
@admin.register(OrderReturn)
class OrderReturnAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'refund_amount', 'refund_status', 'requested_by', 'requested_at')
    list_filter = ('status', 'refund_status', 'requested_at', 'approved_at')
    search_fields = ('order__order_id', 'requested_by__username', 'reason')
    readonly_fields = ('order', 'reason', 'additional_comments', 'requested_by', 'requested_at')
    list_editable = ('status', 'refund_status')
    raw_id_fields = ('order', 'requested_by')
    
    fieldsets = (
        ('Return Request', {
            'fields': ('order', 'reason', 'additional_comments', 'images')
        }),
        ('Status', {
            'fields': ('status', 'rejection_reason')
        }),
        ('Refund Information', {
            'fields': ('refund_amount', 'refund_status')
        }),
        ('Timestamps', {
            'fields': ('requested_by', 'requested_at', 'approved_at', 'rejected_at', 'completed_at')
        }),
    )
    
    actions = ['approve_return', 'reject_return', 'mark_completed']
    
    def approve_return(self, request, queryset):
        updated = queryset.filter(status='requested').update(
            status='approved', 
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} return requests approved.')
    approve_return.short_description = 'Approve selected returns'
    
    def reject_return(self, request, queryset):
        updated = queryset.filter(status='requested').update(
            status='rejected',
            rejected_at=timezone.now()
        )
        self.message_user(request, f'{updated} return requests rejected.')
    reject_return.short_description = 'Reject selected returns'
    
    def mark_completed(self, request, queryset):
        updated = queryset.filter(status='approved').update(
            status='completed',
            completed_at=timezone.now(),
            refund_status='processed'
        )
        self.message_user(request, f'{updated} returns marked as completed.')
    mark_completed.short_description = 'Mark as Completed'

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