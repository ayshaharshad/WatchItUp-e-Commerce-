from django import forms
from django.contrib.auth.forms import AuthenticationForm
from products.models import Category, Product, ProductImage, ProductVariant, ProductVariantImage

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

# -------------------------
# Product Form (Updated for variants)
# -------------------------
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "category", "brand", "base_price", "description"]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

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
        required=False  # Make image upload optional
    )

    class Meta:
        model = ProductImage
        fields = ["image"]

    def clean_image(self):
        images = self.files.getlist("image")
        if images and len(images) < 1:  # Allow at least 1 image if uploaded
            raise forms.ValidationError("At least 1 image is required if uploading.")
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







# # forms.py
# from django import forms
# from django.contrib.auth.forms import AuthenticationForm
# from products.models import Category, Product, ProductImage

# # ------------------------- # Login Form (Superuser login with email + password) # -------------------------
# class AdminLoginForm(AuthenticationForm):
#     username = forms.EmailField(label="Email", widget=forms.EmailInput())

# # ------------------------- # Category Form # -------------------------
# class CategoryForm(forms.ModelForm):
#     class Meta:
#         model = Category
#         fields = ["name"]

# # ------------------------- # Product Form # -------------------------
# class ProductForm(forms.ModelForm):
#     class Meta:
#         model = Product
#         fields = ["name", "category", "price", "original_price", "stock_quantity", "description"]
#         widgets = {
#             'name': forms.TextInput(attrs={'class': 'form-control'}),
#             'category': forms.Select(attrs={'class': 'form-control'}),
#             'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
#             'original_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
#             'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
#             'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
#         }

# # ------------------------- # Custom Widget for multiple file upload # -------------------------
# class MultiFileInput(forms.ClearableFileInput):
#     allow_multiple_selected = True

# # ------------------------- # Product Image Form (Multiple uploads with validation) # -------------------------
# class ProductImageForm(forms.ModelForm):
#     image = forms.ImageField(
#         widget=MultiFileInput(attrs={"multiple": True}),
#         required=False  # Make image upload optional
#     )

#     class Meta:
#         model = ProductImage
#         fields = ["image"]

#     def clean_image(self):
#         images = self.files.getlist("image")
#         if images and len(images) < 1:  # Allow at least 1 image if uploaded
#             raise forms.ValidationError("At least 1 image is required if uploading.")
#         return images


