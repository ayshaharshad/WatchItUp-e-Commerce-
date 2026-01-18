from django import forms
from django.contrib.auth.forms import AuthenticationForm
from products.models import Category, Product, ProductImage, ProductVariant, ProductVariantImage, Order, OrderItem, Coupon, CouponUsage, ProductOffer, CategoryOffer
from django.utils import timezone 
# ------------------------- 
# Login Form (Superuser login with email + password)
# -------------------------
class AdminLoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput())

# -------------------------
# Category Form
# -------------------------
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

# -------------------------
# Product Form (Fixed to match template expectations)
# -------------------------
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "category", "brand", "base_price", "stock", "description"]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter product description'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add empty option for brand (make it optional)
        self.fields['brand'].empty_label = "Select a brand (optional)"
        # Filter active categories only
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        
    # Add a property to make 'price' accessible in template (maps to base_price)
    @property
    def price(self):
        return self['base_price']

# -------------------------
# Product Variant Form
# -------------------------
class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ["product", "color", "color_hex", "price", "original_price", "stock_quantity"]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'color': forms.Select(attrs={'class': 'form-control'}),
            'color_hex': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'placeholder': '#000000'
            }),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'original_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active products
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
        
    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        original_price = cleaned_data.get('original_price')
        
        if original_price and price and original_price <= price:
            raise forms.ValidationError("Original price must be greater than current price.")
        
        return cleaned_data

# -------------------------
# Product Variant Edit Form (for editing existing variants)
# -------------------------
class ProductVariantEditForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ["color", "color_hex", "price", "original_price", "stock_quantity", "is_active"]
        widgets = {
            'color': forms.Select(attrs={'class': 'form-control'}),
            'color_hex': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'placeholder': '#000000'
            }),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'original_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        original_price = cleaned_data.get('original_price')
        
        if original_price and price and original_price <= price:
            raise forms.ValidationError("Original price must be greater than current price.")
        
        return cleaned_data

# -------------------------
# Custom Widget for multiple file upload
# -------------------------
class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

# -------------------------
# Product Variant Image Form (Multiple uploads with validation)
# -------------------------
class ProductVariantImageForm(forms.ModelForm):
    image = forms.ImageField(
        widget=MultiFileInput(attrs={"multiple": True}),
        required=False  # Make image upload optional
    )

    class Meta:
        model = ProductVariantImage
        fields = ["image"]

    def clean_image(self):
        images = self.files.getlist("image")
        if images and len(images) < 1:  # Allow at least 1 image if uploaded
            raise forms.ValidationError("At least 1 image is required if uploading.")
        return images

# -------------------------
# Product Image Form (Keep for backward compatibility)
# -------------------------
class ProductImageForm(forms.ModelForm):
    image = forms.ImageField(
        widget=MultiFileInput(attrs={"multiple": True}),
        required=False  # Images are optional
    )

    class Meta:
        model = ProductImage
        fields = ["image"]

    def clean_image(self):
        images = self.files.getlist("image")
        
        # Validate: Allow 0 to 3 images
        if images and len(images) > 3:
            raise forms.ValidationError("You can upload a maximum of 3 images per product.")
        
        return images

# -------------------------
# Bulk Variant Creation Form
# -------------------------
class BulkVariantForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    colors = forms.MultipleChoiceField(
        choices=ProductVariant.COLOR_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    base_price = forms.DecimalField(
        max_digits=10, 
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'})
    )
    stock_quantity = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        colors = cleaned_data.get('colors')
        
        if product and colors:
            # Check if any of the selected colors already exist for this product
            existing_variants = ProductVariant.objects.filter(
                product=product,
                color__in=colors
            )
            
            if existing_variants.exists():
                existing_colors = [v.get_color_display() for v in existing_variants]
                raise forms.ValidationError(
                    f"Variants already exist for colors: {', '.join(existing_colors)}"
                )
        
        return cleaned_data


# -------------------------
# Order Status Update Form
# -------------------------

class OrderStatusForm(forms.Form):
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
        ('returned', 'Returned'),  # ✅ ADDED THIS
        ('refunded', 'Refunded'),  # ✅ ADDED THIS
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add notes about status change (optional)'
        })
    )
    
    def __init__(self, *args, current_status=None, **kwargs):
        super().__init__(*args, **kwargs)
        if current_status:
            self.fields['status'].initial = current_status


# -------------------------
# Order Search/Filter Form
# -------------------------
class OrderFilterForm(forms.Form):
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('return_requested', 'Return Requested'),  # ✅ ADDED
        ('return_approved', 'Return Approved'),    # ✅ ADDED
        ('returned', 'Returned'),                  # ✅ ADDED
        ('refunded', 'Refunded'),                  # ✅ ADDED
    ]
    
    PAYMENT_CHOICES = [
        ('', 'All Payment Methods'), 
        ('cod', 'Cash on Delivery'), 
        ('razorpay', 'Online Payment'),
        ('wallet', 'Wallet Payment'),  # ✅ ADDED
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by Order ID, Customer Name, Phone...'
        })
    )
    status = forms.ChoiceField(
        required=False,
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    payment_method = forms.ChoiceField(
        required=False,
        choices=PAYMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
# -------------------------
# Coupon Form
# -------------------------
class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = [
            'code', 'discount_type', 'discount_value', 'minimum_amount',
            'max_discount', 'valid_from', 'valid_to', 'is_active',
            'usage_limit', 'usage_per_user'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., SAVE20',
                'style': 'text-transform: uppercase;'
            }),
            'discount_type': forms.Select(attrs={'class': 'form-control'}),
            'discount_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter discount value'
            }),
            'minimum_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Minimum order value (0 for no minimum)'
            }),
            'max_discount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Max discount (leave empty for no cap)'
            }),
            'valid_from': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'valid_to': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'usage_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Total usage limit (leave empty for unlimited)'
            }),
            'usage_per_user': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'value': '1'
            }),
        }
        help_texts = {
            'code': 'Unique coupon code (will be converted to uppercase)',
            'discount_type': 'Choose percentage or fixed amount discount',
            'discount_value': 'For percentage: enter 10 for 10%. For fixed: enter amount',
            'max_discount': 'Maximum discount for percentage coupons (optional)',
            'usage_limit': 'Total number of times this coupon can be used (optional)',
            'usage_per_user': 'Number of times each user can use this coupon',
        }
    
    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        if not code:
            raise forms.ValidationError("Coupon code is required.")
        
        # Check for duplicate codes (exclude current instance if editing)
        existing = Coupon.objects.filter(code=code)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        
        if existing.exists():
            raise forms.ValidationError("This coupon code already exists.")
        
        return code
    
    def clean_discount_value(self):
        discount_value = self.cleaned_data.get('discount_value')
        discount_type = self.cleaned_data.get('discount_type')
        
        if discount_value is None or discount_value <= 0:
            raise forms.ValidationError("Discount value must be greater than 0.")
        
        # Validate percentage discount
        if discount_type == 'percentage' and discount_value > 100:
            raise forms.ValidationError("Percentage discount cannot exceed 100%.")
        
        return discount_value
    
    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        discount_type = cleaned_data.get('discount_type')
        max_discount = cleaned_data.get('max_discount')
        
        # Validate date range
        if valid_from and valid_to:
            if valid_to <= valid_from:
                raise forms.ValidationError("End date must be after start date.")
            
            
            # REPLACE WITH THIS (allow past dates when editing, only warn for new coupons):
            if not self.instance.pk:  # Only for new coupons
                # Make timezone-aware comparison
                now = timezone.now()
                # Allow dates that are at least within the last hour (to account for time zone differences)
                if valid_from < (now - timezone.timedelta(hours=1)):
                    raise forms.ValidationError("Start date cannot be in the past.")
        
        # Validate max_discount for percentage coupons
        if discount_type == 'fixed' and max_discount:
            raise forms.ValidationError(
                "Max discount only applies to percentage-based coupons."
            )
        
        return cleaned_data


# -------------------------
# Coupon Filter Form
# -------------------------
class CouponFilterForm(forms.Form):
    DISCOUNT_TYPE_CHOICES = [
        ('', 'All Types'),
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    STATUS_CHOICES = [
        ('', 'All Status'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by code...'
        })
    )
    
    discount_type = forms.ChoiceField(
        required=False,
        choices=DISCOUNT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

# ==================== ADD THESE NEW OFFER FORMS ====================

class ProductOfferForm(forms.ModelForm):
    """Form for creating/editing product offers"""
    class Meta:
        model = ProductOffer
        fields = [
            'name', 'product', 'discount_type', 'discount_value',
            'max_discount', 'start_date', 'end_date', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Summer Sale - Rolex Watches'
            }),
            'product': forms.Select(attrs={'class': 'form-control'}),
            'discount_type': forms.Select(attrs={'class': 'form-control'}),
            'discount_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter discount value'
            }),
            'max_discount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Max discount (optional for percentage)'
            }),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'name': 'Descriptive name for the offer',
            'discount_type': 'Choose percentage or fixed amount',
            'discount_value': 'For percentage: enter 10 for 10%. For fixed: enter amount',
            'max_discount': 'Maximum discount for percentage offers (optional)',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active products
        self.fields['product'].queryset = Product.objects.filter(is_active=True).order_by('name')
        
        # Set input format for datetime fields
        self.fields['start_date'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['end_date'].input_formats = ['%Y-%m-%dT%H:%M']
    
    def clean_discount_value(self):
        discount_value = self.cleaned_data.get('discount_value')
        discount_type = self.cleaned_data.get('discount_type')
        
        if discount_value is None or discount_value <= 0:
            raise forms.ValidationError("Discount value must be greater than 0.")
        
        if discount_type == 'percentage' and discount_value > 100:
            raise forms.ValidationError("Percentage discount cannot exceed 100%.")
        
        return discount_value
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        discount_type = cleaned_data.get('discount_type')
        max_discount = cleaned_data.get('max_discount')
        product = cleaned_data.get('product')
        
        # Validate dates
        if start_date and end_date:
            if end_date <= start_date:
                raise forms.ValidationError("End date must be after start date.")
            
            # Allow past dates only when editing existing offers
            if not self.instance.pk:
                now = timezone.now()
                if start_date < (now - timezone.timedelta(hours=1)):
                    raise forms.ValidationError("Start date cannot be in the past.")
        
        # Validate max_discount
        if discount_type == 'fixed' and max_discount:
            raise forms.ValidationError("Max discount only applies to percentage offers.")
        
        # Check for overlapping offers
        if product and start_date and end_date:
            overlapping = ProductOffer.objects.filter(
                product=product,
                is_active=True,
                start_date__lt=end_date,
                end_date__gt=start_date
            )
            
            if self.instance.pk:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            
            if overlapping.exists():
                raise forms.ValidationError(
                    f"An active offer already exists for this product during the selected period."
                )
        
        return cleaned_data


class CategoryOfferForm(forms.ModelForm):
    """Form for creating/editing category offers"""
    class Meta:
        model = CategoryOffer
        fields = [
            'name', 'category', 'discount_type', 'discount_value',
            'max_discount', 'start_date', 'end_date', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Men\'s Watches Mega Sale'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'discount_type': forms.Select(attrs={'class': 'form-control'}),
            'discount_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Enter discount value'
            }),
            'max_discount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Max discount (optional for percentage)'
            }),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M'),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'name': 'Descriptive name for the category offer',
            'discount_type': 'Choose percentage or fixed amount',
            'discount_value': 'For percentage: enter 10 for 10%. For fixed: enter amount',
            'max_discount': 'Maximum discount for percentage offers (optional)',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active categories
        self.fields['category'].queryset = Category.objects.filter(is_active=True).order_by('name')
        
        # Set input format for datetime fields
        self.fields['start_date'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['end_date'].input_formats = ['%Y-%m-%dT%H:%M']
    
    def clean_discount_value(self):
        discount_value = self.cleaned_data.get('discount_value')
        discount_type = self.cleaned_data.get('discount_type')
        
        if discount_value is None or discount_value <= 0:
            raise forms.ValidationError("Discount value must be greater than 0.")
        
        if discount_type == 'percentage' and discount_value > 100:
            raise forms.ValidationError("Percentage discount cannot exceed 100%.")
        
        return discount_value
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        discount_type = cleaned_data.get('discount_type')
        max_discount = cleaned_data.get('max_discount')
        category = cleaned_data.get('category')
        
        # Validate dates
        if start_date and end_date:
            if end_date <= start_date:
                raise forms.ValidationError("End date must be after start date.")
            
            # Allow past dates only when editing
            if not self.instance.pk:
                now = timezone.now()
                if start_date < (now - timezone.timedelta(hours=1)):
                    raise forms.ValidationError("Start date cannot be in the past.")
        
        # Validate max_discount
        if discount_type == 'fixed' and max_discount:
            raise forms.ValidationError("Max discount only applies to percentage offers.")
        
        # Check for overlapping offers
        if category and start_date and end_date:
            overlapping = CategoryOffer.objects.filter(
                category=category,
                is_active=True,
                start_date__lt=end_date,
                end_date__gt=start_date
            )
            
            if self.instance.pk:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            
            if overlapping.exists():
                raise forms.ValidationError(
                    f"An active offer already exists for this category during the selected period."
                )
        
        return cleaned_data


class OfferFilterForm(forms.Form):
    """Filter form for offers"""
    DISCOUNT_TYPE_CHOICES = [
        ('', 'All Types'),
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    STATUS_CHOICES = [
        ('', 'All Status'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired'),
        ('upcoming', 'Upcoming'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by offer name...'
        })
    )
    
    discount_type = forms.ChoiceField(
        required=False,
        choices=DISCOUNT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class SalesReportFilterForm(forms.Form):
    """Form for filtering sales reports"""
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom Range'),
    ]
    
    period = forms.ChoiceField(
        choices=PERIOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'period-select'}),
        initial='monthly',
        required=False
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'start-date'
        })
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'end-date'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        period = cleaned_data.get('period')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        # Validate custom date range
        if period == 'custom':
            if not start_date or not end_date:
                raise forms.ValidationError("Both start and end dates are required for custom range.")
            
            if start_date > end_date:
                raise forms.ValidationError("Start date must be before end date.")
            
            # Check if date range is not too large (e.g., max 1 year)
            if (end_date - start_date).days > 365:
                raise forms.ValidationError("Date range cannot exceed 1 year.")
        
        return cleaned_data