from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

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
    # Keep base_price for general product display
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

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
        """Get price range string - FIXED to show proper range"""
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
            # For products without variants, check if base_price > 0 (simple stock logic)
            return True  # Adjust this based on your stock logic
        return self.variants.filter(is_active=True, stock_quantity__gt=0).exists()
    
    @property
    def total_stock(self):
        """Get total stock across all variants"""
        if not self.has_variants:
            return "Available"  # For products without variants
        return self.variants.filter(is_active=True).aggregate(
            total=models.Sum('stock_quantity'))['total'] or 0
    
    @property
    def available_colors(self):
        """Get list of available colors for this product"""
        return self.variants.filter(is_active=True).values_list('color', flat=True).distinct()
    
    @property
    def general_images(self):
        """Get general product images (non-variant specific)"""
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
        
        # Set default hex colors
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
        """Check if variant is in stock"""
        return self.stock_quantity > 0
    
    @property
    def discount_percentage(self):
        """Calculate discount percentage if original price exists"""
        if self.original_price and self.original_price > self.price:
            return round(((self.original_price - self.price) / self.original_price) * 100)
        return 0
    
    @property
    def variant_images(self):
        """Get images specific to this variant"""
        return self.images.all()
    
    @property
    def has_variant_images(self):
        """Check if variant has specific images"""
        return self.images.exists()
    
    @property
    def primary_variant_image(self):
        """Get primary image for this variant"""
        return self.images.filter(is_primary=True).first() or self.images.first()


# ------------------ PRODUCT VARIANT IMAGE ------------------
class ProductVariantImage(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="variant_images/")
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"Image for {self.variant} - {'Primary' if self.is_primary else 'Secondary'}"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per variant
        if self.is_primary:
            ProductVariantImage.objects.filter(variant=self.variant, is_primary=True).update(is_primary=False)
        
        super().save(*args, **kwargs)

        img = Image.open(self.image.path)
        max_size = (600, 600)
        img.thumbnail(max_size)

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.save(self.image.path, quality=90, optimize=True)


# ------------------ PRODUCT IMAGE (General Product Images) ------------------
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products_images/")
    is_primary = models.BooleanField(default=False)  # Added primary flag
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"General Image for {self.product.name}"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per product
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).update(is_primary=False)
            
        super().save(*args, **kwargs)

        img = Image.open(self.image.path)
        max_size = (600, 600)
        img.thumbnail(max_size)

        if img.mode in ("RGBA", "P"):
            img.convert("RGB")

        img.save(self.image.path, quality=90, optimize=True)


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
        unique_together = ('product', 'user')  # One review per user per product
    
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
        """Check if coupon is currently valid"""
        now = timezone.now()
        return (self.is_active and 
                self.valid_from <= now <= self.valid_to and
                (self.usage_limit is None or self.used_count < self.usage_limit))


# from django.db import models
# from django.contrib.auth.models import User
# from PIL import Image
# from django.utils import timezone
# from django.core.validators import MinValueValidator, MaxValueValidator
# from django.conf import settings

# # ------------------ CATEGORY ------------------
# class Category(models.Model):
#     name = models.CharField(max_length=100, unique=True)
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(default=timezone.now)

#     class Meta:
#         ordering = ['-created_at']

#     def __str__(self):
#         return self.name


# # ------------------ BRAND ------------------
# class Brand(models.Model):
#     name = models.CharField(max_length=100, unique=True)
#     is_active = models.BooleanField(default=True)

#     class Meta:
#         ordering = ['name']

#     def __str__(self):
#         return self.name


# # ------------------ PRODUCT ------------------
# class Product(models.Model):
#     name = models.CharField(max_length=200)
#     category = models.ForeignKey(
#         Category,
#         on_delete=models.CASCADE,
#         default=1  
#     )
#     brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
#     price = models.DecimalField(max_digits=10, decimal_places=2)
#     original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # NEW: For discounts
#     stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])  # NEW: Stock management
#     description = models.TextField(blank=True)
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(default=timezone.now)

#     class Meta:
#         ordering = ['-created_at']

#     def __str__(self):
#         return self.name
    
#     @property
#     def is_in_stock(self):
#         """Check if product is in stock"""
#         return self.stock_quantity > 0
    
#     @property
#     def discount_percentage(self):
#         """Calculate discount percentage if original price exists"""
#         if self.original_price and self.original_price > self.price:
#             return round(((self.original_price - self.price) / self.original_price) * 100)
#         return 0
    
#     @property
#     def average_rating(self):
#         """Calculate average rating"""
#         reviews = self.reviews.filter(is_active=True)
#         if reviews.exists():
#             return round(reviews.aggregate(avg_rating=models.Avg('rating'))['avg_rating'], 1)
#         return 0
    
#     @property
#     def review_count(self):
#         """Get total review count"""
#         return self.reviews.filter(is_active=True).count()


# # ------------------ PRODUCT IMAGE ------------------
# class ProductImage(models.Model):
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
#     image = models.ImageField(upload_to="products_images/")
#     created_at = models.DateTimeField(default=timezone.now)

#     class Meta:
#         ordering = ['-created_at']

#     def __str__(self):
#         return f"Image for {self.product.name}"

#     def save(self, *args, **kwargs):
#         super().save(*args, **kwargs)

#         img = Image.open(self.image.path)
#         max_size = (600, 600)
#         img.thumbnail(max_size)

#         if img.mode in ("RGBA", "P"):
#             img = img.convert("RGB")

#         img.save(self.image.path, quality=90, optimize=True)


# # ------------------ PRODUCT REVIEW ------------------
# class ProductReview(models.Model):
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     rating = models.IntegerField(
#         validators=[MinValueValidator(1), MaxValueValidator(5)],
#         help_text="Rating from 1 to 5 stars"
#     )
#     review_text = models.TextField(blank=True)
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(default=timezone.now)
    
#     class Meta:
#         ordering = ['-created_at']
#         unique_together = ('product', 'user')  # One review per user per product
    
#     def __str__(self):
#         return f"{self.user.username} - {self.product.name} ({self.rating} stars)"


# # ------------------ COUPON ------------------
# class Coupon(models.Model):
#     DISCOUNT_TYPE_CHOICES = [
#         ('percentage', 'Percentage'),
#         ('fixed', 'Fixed Amount'),
#     ]
    
#     code = models.CharField(max_length=50, unique=True)
#     discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
#     discount_value = models.DecimalField(max_digits=10, decimal_places=2)
#     minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
#     valid_from = models.DateTimeField()
#     valid_to = models.DateTimeField()
#     is_active = models.BooleanField(default=True)
#     usage_limit = models.IntegerField(null=True, blank=True)
#     used_count = models.IntegerField(default=0)
    
#     def __str__(self):
#         return self.code
    
#     @property
#     def is_valid(self):
#         """Check if coupon is currently valid"""
#         now = timezone.now()
#         return (self.is_active and 
#                 self.valid_from <= now <= self.valid_to and
#                 (self.usage_limit is None or self.used_count < self.usage_limit))