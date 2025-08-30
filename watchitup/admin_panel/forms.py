# forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from products.models import Category, Product, ProductImage

# ------------------------- # Login Form (Superuser login with email + password) # -------------------------
class AdminLoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput())

# ------------------------- # Category Form # -------------------------
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]

# ------------------------- # Product Form # -------------------------
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "category", "price", "description"]

# ------------------------- # Custom Widget for multiple file upload # -------------------------
class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

# ------------------------- # Product Image Form (Multiple uploads with validation) # -------------------------
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