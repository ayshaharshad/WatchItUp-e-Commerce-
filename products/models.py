from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
import uuid
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date




# ------------------ CATEGORY ------------------

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """
        Normalize category name to title case before saving.
        This ensures: 'men' -> 'Men', 'MEN' -> 'Men', 'mEn' -> 'Men'
        """
        if self.name:
            self.name = self.name.strip().title()
        super().save(*args, **kwargs)
    
    def clean(self):
        """
        Validate that no duplicate category exists (case-insensitive).
        This prevents creating 'Men' if 'men' already exists.
        """
        from django.core.exceptions import ValidationError
        
        if not self.name:
            raise ValidationError("Category name is required.")
        
        # Normalize the name
        normalized_name = self.name.strip().title()
        
        # Check for case-insensitive duplicates
        existing = Category.objects.filter(
            name__iexact=normalized_name
        )
        
        # Exclude current instance when editing
        if self.pk:
            existing = existing.exclude(pk=self.pk)
        
        if existing.exists():
            raise ValidationError({
                'name': f"Category '{normalized_name}' already exists (case-insensitive match)."
            })



# ------------------ BRAND ------------------
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name




# ------------------ PRODUCT ------------------
class Product(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        default=1  
    )
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    stock = models.PositiveIntegerField(default=0)
    max_quantity_per_order = models.PositiveIntegerField(default=10)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name
    
    @property
    def has_variants(self):
        """Check if product has variants"""
        return self.variants.filter(is_active=True).exists()
    
    @property
    def default_variant(self):
        """Get the default variant (first active variant)"""
        return self.variants.filter(is_active=True).first()
    
    @property
    def min_price(self):
        """Get minimum price from all variants or base price"""
        if self.has_variants:
            variants = self.variants.filter(is_active=True)
            if variants.exists():
                return variants.order_by('price').first().price
        return self.base_price
    
    @property
    def max_price(self):
        """Get maximum price from all variants or base price"""
        if self.has_variants:
            variants = self.variants.filter(is_active=True)
            if variants.exists():
                return variants.order_by('-price').first().price
        return self.base_price
    
    @property
    def price_range(self):
        """Get price range string"""
        if not self.has_variants:
            return f"₹{self.base_price}"
        
        min_price = self.min_price
        max_price = self.max_price
        if min_price == max_price:
            return f"₹{min_price}"
        return f"₹{min_price} - ₹{max_price}"
    
    @property
    def is_in_stock(self):
        """Check if product or any variant is in stock"""
        if self.has_variants:
            # If product has variants, check if any variant has stock
            return self.variants.filter(is_active=True, stock_quantity__gt=0).exists()
        else:
            # If no variants, check base product stock
            return self.stock > 0
    
    @property
    def total_stock(self):
        """Get total stock across all variants or base stock"""
        if self.has_variants:
            total = self.variants.filter(is_active=True).aggregate(
                total=models.Sum('stock_quantity'))['total'] or 0
            return total
        else:
            # Return base product stock for products without variants
            return self.stock
    
    @property
    def available_colors(self):
        """Get list of available colors for this product"""
        return self.variants.filter(is_active=True).values_list('color', flat=True).distinct()
    
    @property
    def general_images(self):
        """Get general product images"""
        return self.images.all()
    
    @property
    def has_general_images(self):
        """Check if product has general images"""
        return self.images.exists()
    
    @property
    def primary_general_image(self):
        """Get first general image"""
        return self.images.first()
    
    @property
    def average_rating(self):
        """Calculate average rating"""
        reviews = self.reviews.filter(is_active=True)
        if reviews.exists():
            return round(reviews.aggregate(avg_rating=models.Avg('rating'))['avg_rating'], 1)
        return 0
    
    @property
    def review_count(self):
        """Get total review count"""
        return self.reviews.filter(is_active=True).count()
    
    def get_active_product_offer(self):
        now = timezone.now()
        offers = self.product_offers.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-discount_value')
    
        return offers.first()

    def get_active_category_offer(self):
        """Get the best active category offer"""
        now = timezone.now()
        offers = self.category.category_offers.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('-discount_value')
        
        return offers.first()

    def get_best_offer(self):
        """Get the best offer (product or category) - returns larger discount"""
        product_offer = self.get_active_product_offer()
        category_offer = self.get_active_category_offer()
        
        if not product_offer and not category_offer:
            return None
        
        if not product_offer:
            return category_offer
        
        if not category_offer:
            return product_offer
        
        # Compare discounts and return the better one
        # Use base_price or min variant price for comparison
        test_price = self.min_price if self.has_variants else self.base_price
        
        product_discount = product_offer.calculate_discount(test_price)
        category_discount = category_offer.calculate_discount(test_price)
        
        return product_offer if product_discount >= category_discount else category_offer

    def get_offer_price(self, original_price):
        """Get final price after applying best offer"""
        best_offer = self.get_best_offer()
        
        if not best_offer:
            return original_price
        
        return best_offer.get_discounted_price(original_price)

    def has_active_offer(self):
        """Check if product has any active offer"""
        return self.get_best_offer() is not None

    


# ------------------ PRODUCT VARIANT ------------------
class ProductVariant(models.Model):
    COLOR_CHOICES = [
        ('black', 'Black'),
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('rose_gold', 'Rose Gold'),
        ('blue', 'Blue'),
        ('white', 'White'),
        ('brown', 'Brown'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    color = models.CharField(max_length=20, choices=COLOR_CHOICES)
    color_hex = models.CharField(max_length=7, blank=True, help_text="Hex color code (e.g., #000000)")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    sku = models.CharField(max_length=100, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['color']
        unique_together = ('product', 'color')
    
    def __str__(self):
        return f"{self.product.name} - {self.get_color_display()}"
    
    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f"{self.product.name[:10].upper().replace(' ', '')}-{self.color.upper()}-{self.product.id}"
        
        color_hex_map = {
            'black': '#000000',
            'gold': '#FFD700',
            'silver': '#C0C0C0',
            'rose_gold': '#E8B4A0',
            'blue': '#0066CC',
            'white': '#FFFFFF',
            'brown': '#8B4513',
        }
        
        if not self.color_hex and self.color in color_hex_map:
            self.color_hex = color_hex_map[self.color]
            
        super().save(*args, **kwargs)
    
    @property
    def is_in_stock(self):
        return self.stock_quantity > 0
    
    @property
    def discount_percentage(self):
        if self.original_price and self.original_price > self.price:
            return round(((self.original_price - self.price) / self.original_price) * 100)
        return 0
    
    @property
    def variant_images(self):
        return self.images.all()
    
    @property
    def has_variant_images(self):
        return self.images.exists()
    
    @property
    def primary_variant_image(self):
        return self.images.filter(is_primary=True).first() or self.images.first()
    
    def get_variant_offer_price(self):
        """Get variant price after applying best offer"""
        best_offer = self.product.get_best_offer()
    
        if not best_offer:
            return self.price
    
        return best_offer.get_discounted_price(self.price)

    def get_variant_discount_amount(self):
        """Get discount amount for this variant"""
        best_offer = self.product.get_best_offer()
        
        if not best_offer:
            return Decimal('0')
        
        return best_offer.calculate_discount(self.price)

    def get_variant_discount_percentage(self):
        """Get discount percentage for display"""
        discount_amount = self.get_variant_discount_amount()
        
        if discount_amount > 0 and self.price > 0:
            return round((discount_amount / self.price) * 100)
        
        return 0



# ------------------ PRODUCT VARIANT IMAGE ------------------
class ProductVariantImage(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="variant_images/")
    zoom_image = models.ImageField(upload_to="variant_images/zoom/", blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"Image for {self.variant} - {'Primary' if self.is_primary else 'Secondary'}"

    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductVariantImage.objects.filter(variant=self.variant, is_primary=True).update(is_primary=False)
        
        super().save(*args, **kwargs)

        try:
            img = Image.open(self.image.path)
            max_size = (600, 600)
            img.thumbnail(max_size)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(self.image.path, quality=90, optimize=True)

            if self.zoom_image:
                zoom_img = Image.open(self.zoom_image.path)
                zoom_max_size = (1200, 1200)  # Higher resolution for zoom
                zoom_img.thumbnail(zoom_max_size)
                if zoom_img.mode in ("RGBA", "P"):
                    zoom_img = zoom_img.convert("RGB")
                zoom_img.save(self.zoom_image.path, quality=90, optimize=True)
        except Exception as e:
            print(f"Error processing image: {e}")


# ------------------ PRODUCT IMAGE (General Product Images) ------------------
class ProductImage(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products_images/")
    zoom_image = models.ImageField(upload_to="products_images/zoom/", blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"General Image for {self.product.name}"

    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).update(is_primary=False)
            
        super().save(*args, **kwargs)

        try:
            img = Image.open(self.image.path)
            max_size = (600, 600)
            img.thumbnail(max_size)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(self.image.path, quality=90, optimize=True)

            if self.zoom_image:
                zoom_img = Image.open(self.zoom_image.path)
                zoom_max_size = (1200, 1200)
                zoom_img.thumbnail(zoom_max_size)
                if zoom_img.mode in ("RGBA", "P"):
                    zoom_img = zoom_img.convert("RGB")
                zoom_img.save(self.zoom_image.path, quality=90, optimize=True)
        except Exception as e:
            print(f"Error processing image: {e}")


# ------------------ PRODUCT REVIEW ------------------
class ProductReview(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="reviews", null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    title = models.CharField(max_length=255, null=True, blank=True)
    review_text = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)  # For admin moderation
    is_verified_purchase = models.BooleanField(default=False)  # NEW - Auto-set if user bought it
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)  # NEW - Track edits
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'user')  # One review per user per product
    
    def __str__(self):
        variant_info = f" ({self.variant.get_color_display()})" if self.variant else ""
        return f"{self.user.username} - {self.product.name}{variant_info} ({self.rating} stars)"
    
    @property
    def star_display(self):
        """Return filled/empty stars for display"""
        return '★' * self.rating + '☆' * (5 - self.rating)



# |----------CART models---------------|

class Cart(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"Cart -{self.user.username}"
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    @property
    def subtotal(self):
        return sum(item.item_total for item in self.items.all())
    
    @property
    def total(self):
        return self.subtotal
    
class CartItem(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cart', 'product', 'variant')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    @property
    def item_total(self):
        """Calculate item total with offer support"""
        if self.variant:
            price = self.variant.price
        else:
            price = self.product.base_price
        
        # Apply offer if available
        best_offer = self.product.get_best_offer()
        if best_offer:
            price = best_offer.get_discounted_price(price)
        
        return price * self.quantity
    
    @property
    def available_stock(self):
        """Get available stock"""
        if self.variant:
            return self.variant.stock_quantity
        else:
            return self.product.stock
    
    @property
    def unit_price(self):
        """Get unit price with offer"""
        if self.variant:
            price = self.variant.price
        else:
            price = self.product.base_price
        
        best_offer = self.product.get_best_offer()
        if best_offer:
            price = best_offer.get_discounted_price(price)
        
        return price
    
    @property
    def display_name(self):
        """Get display name with variant info if applicable"""
        if self.variant:
            return f"{self.product.name} ({self.variant.get_color_display()})"
        else:
            return self.product.name
    
    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.product.is_active or not self.product.category.is_active:
            raise ValidationError("This product is unavailable")
        
        if self.variant and not self.variant.is_active:
            raise ValidationError("This variant is unavailable")
        
        if self.quantity > self.available_stock:
            raise ValidationError(f"Only {self.available_stock} items available")
        
# ------------------ COUPON (UPDATED) ------------------
class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                      help_text="Maximum discount for percentage coupons")
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    usage_limit = models.IntegerField(null=True, blank=True, help_text="Total usage limit")
    usage_per_user = models.IntegerField(default=1, help_text="Usage limit per user")
    used_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'
    
    def __str__(self):
        return self.code
    
    @property
    def is_valid(self):
        now = timezone.now()
        return (self.is_active and 
                self.valid_from <= now <= self.valid_to and
                (self.usage_limit is None or self.used_count < self.usage_limit))
    
    def calculate_discount(self, subtotal):
        """Calculate discount amount for given subtotal"""
        if self.discount_type == 'percentage':
            discount = subtotal * (self.discount_value / 100)
            if self.max_discount:
                discount = min(discount, self.max_discount)
        else:
            discount = self.discount_value
        
        return min(discount, subtotal)  # Discount can't exceed subtotal
    
    def can_use(self, user):
        """Check if user can use this coupon"""
        if not self.is_valid:
            return False, "Coupon is not valid"
        
        # Check usage per user
        usage_count = CouponUsage.objects.filter(coupon=self, user=user).count()
        if usage_count >= self.usage_per_user:
            return False, "You have already used this coupon"
        
        return True, "Coupon is valid"


class CouponUsage(models.Model):
    """Track coupon usage per user"""
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True)
    used_at = models.DateTimeField(auto_now_add=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        ordering = ['-used_at']
    
    def __str__(self):
        return f"{self.user.username} used {self.coupon.code}"




# |-------ORDER models (UPDATED)---------------|


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('return_requested', 'Return Requested'),
        ('return_approved', 'Return Approved'),
        ('returned', 'Returned'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('razorpay', 'Razorpay (Online)'),
        ('wallet', 'Wallet Payment'),  # ✅ Add wallet payment option
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    order_id = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')

    # Address fields (snapshot at order time)
    shipping_full_name = models.CharField(max_length=150)
    shipping_phone = models.CharField(max_length=20)
    shipping_line1 = models.CharField(max_length=255)
    shipping_line2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)

    # Order details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cod')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['order_id']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"Order {self.order_id}"

    def save(self, *args, **kwargs):
        if not self.order_id:
            # Generate unique order ID: ORD20250105001
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            last_order = Order.objects.filter(
                order_id__startswith=f'ORD{date_str}'
            ).order_by('-order_id').first()
            
            if last_order:
                last_num = int(last_order.order_id[-3:])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.order_id = f'ORD{date_str}{new_num:03d}'
        
        super().save(*args, **kwargs)

    @property
    def can_cancel(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'confirmed', 'processing'] and \
               self.payment_status != 'refunded'

    @property
    def can_return(self):
        """Check if order can be returned (within 7 days of delivery)"""
        # Must be delivered
        if self.status != 'delivered':
            return False
    
        # Must have delivery date
        if not self.delivered_at:
            return False
    
        # Check if already returned or return requested
        if self.status in ['returned', 'return_requested', 'return_approved']:
            return False
    
    # Must be within 7 days
        from datetime import timedelta
        return timezone.now() <= self.delivered_at + timedelta(days=7)
    
    @property
    def active_items_count(self):
        """Count of active (non-cancelled) items"""
        return self.items.filter(status='active').count()
    
    @property
    def cancellable_amount(self):
        """Calculate refundable amount for cancellation"""
        if self.payment_method == 'cod' and self.status == 'pending':
            return 0  # No refund for COD pending orders
        return self.total
    
    @property
    def can_cancel(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'confirmed', 'processing'] and \
               self.payment_status != 'refunded'

    @property
    def can_return(self):
        """Check if order can be returned (within 7 days of delivery)"""
        # Must be delivered
        if self.status != 'delivered':
            return False
    
        # Must have delivery date
        if not self.delivered_at:
            return False
    
        # Check if already returned or return requested
        if self.status in ['returned', 'return_requested', 'return_approved', 'cancelled']:
            return False
    
        # Must be within 7 days
        from datetime import timedelta
        return timezone.now() <= self.delivered_at + timedelta(days=7)
    
    @property
    def is_returnable(self):
        """Alias for can_return"""
        return self.can_return
    
    @property
    def return_deadline(self):
        """Get the deadline for return request"""
        if self.delivered_at:
            from datetime import timedelta
            return self.delivered_at + timedelta(days=7)
        return None
    
    @property
    def days_until_return_deadline(self):
        """Calculate days remaining for return"""
        if not self.delivered_at:
            return None
        
        deadline = self.return_deadline
        if deadline:
            days = (deadline - timezone.now()).days
            return max(0, days)
        return None
    @property
    def active_items(self):
        """Get only active (non-cancelled, non-returned) items"""
        return self.items.filter(status='active')
    
    @property
    def cancelled_items(self):
        """Get cancelled items"""
        return self.items.filter(status='cancelled')
    
    @property
    def returned_items(self):
        """Get returned items"""
        return self.items.filter(status='returned')
    
    @property
    def active_subtotal(self):
        """Calculate subtotal for ACTIVE items only"""
        return sum(item.item_total for item in self.active_items)
    
    @property
    def active_tax(self):
        """Calculate tax for ACTIVE items only"""
        return self.active_subtotal * Decimal('0.18')
    
    @property
    def active_total(self):
        """Calculate total for ACTIVE items only"""
        active_subtotal = self.active_subtotal
        if active_subtotal == 0:
            return Decimal('0')
        
        tax = self.active_tax
        shipping = Decimal('0') if active_subtotal > 500 else Decimal('50')
        
        return active_subtotal + tax + shipping
    
    @property
    def refunded_amount(self):
        """Calculate total refunded amount"""
        cancelled_total = sum(item.item_total for item in self.cancelled_items)
        returned_total = sum(item.item_total for item in self.returned_items)
        return cancelled_total + returned_total
    
    @property
    def cancelled_total(self):
        """Calculate total from cancelled items"""
        return sum(item.item_total for item in self.cancelled_items)
    
    @property
    def returned_total(self):
        """Calculate total from returned items"""
        return sum(item.item_total for item in self.returned_items)
    
    @property
    def display_status(self):
        """
        Smart status display for mixed-status orders
        Returns human-readable status based on item statuses
        """
        active_count = self.active_items.count()
        cancelled_count = self.cancelled_items.count()
        returned_count = self.returned_items.count()
        total_items = self.items.count()
        
        # All items cancelled
        if cancelled_count == total_items:
            return 'cancelled'
        
        # All items returned
        if returned_count == total_items:
            return 'returned'
        
        # All items active - use original status
        if active_count == total_items:
            return self.status
        
        # Mixed statuses - prioritize what needs attention
        if returned_count > 0 and active_count > 0:
            return 'partially_returned'
        
        if cancelled_count > 0 and active_count > 0:
            return 'partially_cancelled'
        
        if cancelled_count > 0 and returned_count > 0:
            return 'mixed_cancellation_return'
        
        return self.status
    
    @property
    def status_badge_info(self):
        """
        Return status info for frontend display
        Returns: dict with 'text', 'color', 'icon'
        """
        status_map = {
            'pending': {'text': 'Pending', 'color': 'warning', 'icon': 'clock'},
            'confirmed': {'text': 'Confirmed', 'color': 'info', 'icon': 'check-circle'},
            'processing': {'text': 'Processing', 'color': 'primary', 'icon': 'cog'},
            'shipped': {'text': 'Shipped', 'color': 'primary', 'icon': 'truck'},
            'out_for_delivery': {'text': 'Out for Delivery', 'color': 'purple', 'icon': 'shipping-fast'},
            'delivered': {'text': 'Delivered', 'color': 'success', 'icon': 'box-check'},
            'cancelled': {'text': 'Cancelled', 'color': 'danger', 'icon': 'times-circle'},
            'return_requested': {'text': 'Return Requested', 'color': 'warning', 'icon': 'undo'},
            'return_approved': {'text': 'Return Approved', 'color': 'info', 'icon': 'check'},
            'returned': {'text': 'Returned', 'color': 'secondary', 'icon': 'box-open'},
            'refunded': {'text': 'Refunded', 'color': 'dark', 'icon': 'money-bill-wave'},
            'partially_cancelled': {'text': 'Partially Cancelled', 'color': 'orange', 'icon': 'exclamation-triangle'},
            'partially_returned': {'text': 'Partially Returned', 'color': 'teal', 'icon': 'exchange-alt'},
            'mixed_cancellation_return': {'text': 'Mixed Status', 'color': 'gray', 'icon': 'list'},
        }
        
        display_status = self.display_status
        return status_map.get(display_status, status_map['pending'])
    
    @property
    def has_mixed_statuses(self):
        """Check if order has items with different statuses"""
        statuses = set(self.items.values_list('status', flat=True))
        return len(statuses) > 1


class RazorpayPayment(models.Model):
    """Track Razorpay payment transactions"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='razorpay_payments')
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, default='created')  # created, paid, failed
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment for {self.order.order_id} - {self.status}"



class OrderItem(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey('ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Snapshot of product details at order time
    product_name = models.CharField(max_length=255)
    product_image = models.ImageField(upload_to='orders/', null=True, blank=True)
    variant_name = models.CharField(max_length=100, blank=True)
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    item_total = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    @property
    def can_cancel(self):
        """Check if item can be cancelled"""
        return self.status == 'active' and self.order.can_cancel
    
    @property
    def can_return(self):
        """Check if item can be returned"""
        return self.status == 'active' and self.order.can_return


class OrderCancellation(models.Model):
    CANCELLATION_TYPE_CHOICES = [
        ('full_order', 'Full Order'),
        ('single_item', 'Single Item'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='cancellations',default=1)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, null=True, blank=True)
    cancellation_type = models.CharField(max_length=20, choices=CANCELLATION_TYPE_CHOICES, default='full_order')
    
    reason = models.TextField()
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_status = models.CharField(max_length=20, default='pending',
                                     choices=[('pending', 'Pending'), ('processed', 'Processed')])
    
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    cancelled_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-cancelled_at']

    def __str__(self):
        if self.order_item:
            return f"Item Cancellation - {self.order_item.product_name}"
        return f"Order Cancellation - {self.order.order_id}"


class OrderReturn(models.Model):
    RETURN_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved - Awaiting Return'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed - Refunded'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='returns')
    reason = models.TextField()
    additional_comments = models.TextField(blank=True)
    
    images = models.ImageField(upload_to='returns/', null=True, blank=True,
                              help_text="Optional: Upload images showing product condition")
    
    status = models.CharField(max_length=20, choices=RETURN_STATUS_CHOICES, default='pending')
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_status = models.CharField(max_length=20, default='pending',
                                     choices=[('pending', 'Pending'), ('processed', 'Processed')])
    
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    
    # Admin review fields
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_returns',
        help_text="Admin who reviewed this return"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, help_text="Internal admin notes")
    
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Return Request - {self.order.order_id} ({self.status})"
    
    @property
    def can_be_approved(self):
        """Check if return can be approved"""
        return self.status == 'pending'
    
    @property
    def can_be_rejected(self):
        """Check if return can be rejected"""
        return self.status == 'pending'
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def is_approved(self):
        return self.status == 'approved'
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    def __str__(self):
        return f"Return Request #{self.id} - {self.order.order_id} ({self.get_status_display()})"

    


#|------------------WISHLIST----------------------|


class Wishlist(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wishlist - {self.user.username}"

    @property
    def total_items(self):
        return self.items.count()


class WishlistItem(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('wishlist', 'product', 'variant')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.product.name} in {self.user.username}'s wishlist"

#|------------------CHECKOUT---------------------|

class Checkout(models.Model):
    """
    Temporary checkout session model - stores cart items being checked out
    Gets converted to Order upon payment confirmation
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='checkouts')
    session_id = models.CharField(max_length=100, unique=True, editable=False)
    
    # Selected shipping address
    address = models.ForeignKey('users.Address', on_delete=models.SET_NULL, null=True)
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment
    payment_method = models.CharField(max_length=20, choices=[
        ('cod', 'Cash on Delivery'),
        ('online', 'Online Payment'),
    ], default='cod')
    
    # Status
    is_completed = models.BooleanField(default=False)
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # Session expires after 30 minutes
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"Checkout {self.session_id} - {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.session_id:
            import uuid
            self.session_id = str(uuid.uuid4())
        
        if not self.expires_at:
            from django.utils import timezone
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(minutes=30)
        
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def calculate_totals(self):
        """Calculate all totals based on items"""
        self.subtotal = sum(item.item_total for item in self.items.all())
        # Add tax calculation logic here (e.g., 18% GST)
        self.tax = self.subtotal * 0.18  # Example: 18% tax
        # Shipping logic
        self.shipping_charge = 0 if self.subtotal > 500 else 50  # Free shipping over 500
        # Discount logic (can be extended with coupon codes)
        self.discount = 0
        # Final total
        self.total = self.subtotal + self.tax + self.shipping_charge - self.discount
        self.save()


class CheckoutItem(models.Model):
    checkout = models.ForeignKey(Checkout, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE, null=True, blank=True)
    
    # Snapshot of data at checkout time
    product_name = models.CharField(max_length=255)
    product_image = models.ImageField(upload_to='checkout/', null=True, blank=True)
    variant_name = models.CharField(max_length=100, blank=True)
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    item_total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Stock validation
    is_available = models.BooleanField(default=True)
    stock_at_checkout = models.PositiveIntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    def validate_stock(self):
        """Check if product is still available with required quantity"""
        current_stock = self.variant.stock if self.variant else self.product.stock
        product_active = self.product.is_active and self.product.category.is_active
        
        self.is_available = product_active and current_stock >= self.quantity
        self.stock_at_checkout = current_stock
        self.save()
        
        return self.is_available
    
# ==================== OFFER MODELS ====================

class ProductOffer(models.Model):
    """Offer for specific products"""
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    name = models.CharField(max_length=200, help_text="Offer name (e.g., 'Summer Sale')")
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='product_offers')
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="For percentage: enter 10 for 10%. For fixed: enter amount"
    )
    max_discount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum discount for percentage offers"
    )
    
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Product Offer'
        verbose_name_plural = 'Product Offers'
    
    def __str__(self):
        return f"{self.name} - {self.product.name}"
    
    def clean(self):
        """Validate offer dates and discount values"""
        if self.end_date <= self.start_date:
            raise ValidationError("End date must be after start date.")
        
        if self.discount_type == 'percentage':
            if self.discount_value > 100:
                raise ValidationError("Percentage discount cannot exceed 100%.")
        
        if self.discount_type == 'fixed' and self.max_discount:
            raise ValidationError("Max discount only applies to percentage offers.")
    
    @property
    def discount_percentage(self):
        return self.discount_value

    @property
    def is_valid(self):
        """Check if offer is currently valid"""
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date
    
    def calculate_discount(self, price):
        """Calculate discount amount for given price"""
        if not self.is_valid:
            return Decimal('0')
        
        if self.discount_type == 'percentage':
            discount = price * (self.discount_value / 100)
            if self.max_discount:
                discount = min(discount, self.max_discount)
        else:
            discount = self.discount_value
        
        return min(discount, price)  # Discount can't exceed price
    
    def get_discounted_price(self, price):
        """Get final price after discount"""
        return price - self.calculate_discount(price)


class CategoryOffer(models.Model):
    """Offer for entire categories"""
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    name = models.CharField(max_length=200, help_text="Offer name (e.g., 'Men's Watch Sale')")
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='category_offers')
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="For percentage: enter 10 for 10%. For fixed: enter amount"
    )
    max_discount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum discount for percentage offers"
    )
    
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Category Offer'
        verbose_name_plural = 'Category Offers'
    
    def __str__(self):
        return f"{self.name} - {self.category.name}"
    
    def clean(self):
    # Validate discount_value
        if self.discount_value is None:
            raise ValidationError("Discount value is required.")
    
        if self.discount_value < 0:
            raise ValidationError("Discount value cannot be negative.")
    
        if self.discount_type == 'percentage' and self.discount_value > 100:
            raise ValidationError("Percentage discount cannot exceed 100%.")

        # Validate dates
        if self.end_date and self.start_date:
            if self.end_date <= self.start_date:
                raise ValidationError("End date must be after start date.")
        
        if self.end_date < timezone.now():
            raise ValidationError("End date cannot be in the past.")
    
        # Validate max_discount
        if self.discount_type == 'fixed' and self.max_discount:
            raise ValidationError("Max discount only applies to percentage offers.")

    @property
    def discount_percentage(self):
        return self.discount_value

    @property
    def is_valid(self):
        """Check if offer is currently valid"""
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date
    
    def calculate_discount(self, price):
        """Calculate discount amount for given price"""
        if not self.is_valid:
            return Decimal('0')
        
        if self.discount_type == 'percentage':
            discount = price * (self.discount_value / 100)
            if self.max_discount:
                discount = min(discount, self.max_discount)
        else:
            discount = self.discount_value
        
        return min(discount, price)
    
    def get_discounted_price(self, price):
        """Get final price after discount"""
        return price - self.calculate_discount(price)


class ReferralCoupon(models.Model):
    """Coupons generated from referrals"""
    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='referral_coupons_earned'
    )
    referred_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='referral_signup'
    )
    coupon = models.ForeignKey('Coupon', on_delete=models.CASCADE, related_name='referral_coupons')
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('referrer', 'referred_user')
    
    def __str__(self):
        return f"{self.referrer.username} referred {self.referred_user.username}"







