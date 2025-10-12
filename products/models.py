from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
import uuid

# ------------------ CATEGORY ------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


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
    def is_in_stock(self):
        return self.stock > 0
    
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
        """Get minimum price from all variants"""
        variants = self.variants.filter(is_active=True)
        if variants.exists():
            return variants.order_by('price').first().price
        return self.base_price
    
    @property
    def max_price(self):
        """Get maximum price from all variants"""
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
        """Check if any variant is in stock"""
        if not self.has_variants:
            return True
        return self.variants.filter(is_active=True, stock_quantity__gt=0).exists()
    
    @property
    def total_stock(self):
        """Get total stock across all variants"""
        if not self.has_variants:
            return "Available"
        return self.variants.filter(is_active=True).aggregate(
            total=models.Sum('stock_quantity'))['total'] or 0
    
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


# ------------------ PRODUCT VARIANT IMAGE ------------------
class ProductVariantImage(models.Model):
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
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="reviews", null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    review_text = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'user')
    
    def __str__(self):
        variant_info = f" ({self.variant.get_color_display()})" if self.variant else ""
        return f"{self.user.username} - {self.product.name}{variant_info} ({self.rating} stars)"


# ------------------ COUPON ------------------
class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    usage_limit = models.IntegerField(null=True, blank=True)
    used_count = models.IntegerField(default=0)
    
    def __str__(self):
        return self.code
    
    @property
    def is_valid(self):
        now = timezone.now()
        return (self.is_active and 
                self.valid_from <= now <= self.valid_to and
                (self.usage_limit is None or self.used_count < self.usage_limit))
    
# |----------CART models---------------|

class Cart(models.Model):
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
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE)
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
        price = self.variant.price if self.variant else self.product.price
        return price * self.quantity
    
    @property
    def available_stock(self):
        return self.variant.stock if self.variant else self.product.stock
    
    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.product.is_active or not self.product.category.is_active:
            raise ValidationError("This product is unavailable")
        
        if self.quantity > self.available_stock:
            raise ValidationError(f"Only {self.available_stock} items available")
        
# |-------ORDER models---------------|

class Order(models.Model):
    STATUS_CHOICES =[
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]

    PAYMENT_CHOICES = [
        ('cod','Cash on Delivery'),
        ('online', 'Online Payment'),
    ]

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
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

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
        return self.status in ['pending', 'confirmed']

    @property
    def can_return(self):
        return self.status == 'delivered'


class OrderItem(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]

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


class OrderCancellation(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, null=True, blank=True)
    reason = models.TextField(blank=True)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    cancelled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.order:
            return f"Cancellation - {self.order.order_id}"
        return f"Item Cancellation - {self.order_item.id}"


class OrderReturn(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    reason = models.TextField()
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Return Request - {self.order.order_id}"
    

#|------------------WISHLIST----------------------|


class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wishlist - {self.user.username}"

    @property
    def total_items(self):
        return self.items.count()


class WishlistItem(models.Model):
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
    
    





