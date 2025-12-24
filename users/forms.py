from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model, authenticate
from django.core.validators import RegexValidator
from django.db.models import Q
import logging
from .models import Address

logger = logging.getLogger(__name__)
User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address',
            'autofocus': True
        })
    )
    referral_code = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter referral code (optional)',
            'style': 'text-transform: uppercase;'
        }),
        help_text='Have a referral code? Enter it here to give your friend a reward!'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'referral_code')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Update field attributes
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username (letters, numbers, @/./+/-/_ only)'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password (min 8 characters)'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
        
        # Clear default help texts for cleaner UI
        self.fields['username'].help_text = ""
        self.fields['password1'].help_text = ""

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            logger.warning(f"Signup attempted with duplicate username: {username}")
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        email_lower = email.lower()
        if User.objects.filter(email=email_lower).exists():
            logger.warning(f"Signup attempted with duplicate email: {email}")
            raise forms.ValidationError("This email is already registered.")
        return email_lower

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if not password:
            raise forms.ValidationError("Password is required.")
        
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        
        if not any(char.isdigit() for char in password):
            raise forms.ValidationError("Password must contain at least one digit.")
        
        if not any(char.isupper() for char in password):
            raise forms.ValidationError("Password must contain at least one uppercase letter.")
        
        if not any(char.islower() for char in password):
            raise forms.ValidationError("Password must contain at least one lowercase letter.")
            
        return password
    
    def clean_referral_code(self):
        """Validate referral code"""
        code = self.cleaned_data.get('referral_code', '').strip().upper()
        
        if code:
            try:
                referrer = User.objects.get(referral_code=code, is_active=True)
                # Store referrer in form for later use
                self.referrer = referrer
            except User.DoesNotExist:
                raise forms.ValidationError("Invalid referral code.")
        else:
            self.referrer = None
        
        return code

class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        
        # Update field attributes
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autocomplete': 'username',
            'autofocus': True
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'current-password'
        })
        
        # Update labels
        self.fields['username'].label = "Username or Email"
        self.fields['password'].label = "Password"

    def clean(self):
        username_or_email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username_or_email is not None and password:
            # FIXED: Use get_user_model() instead of User to get the correct model
            User = get_user_model()
            
            # Try to find user by email or username
            user = User.objects.filter(
                Q(email__iexact=username_or_email) | Q(username__iexact=username_or_email)
            ).first()

            if user:
                # Use the correct field for authentication based on your custom user model
                # If your custom user model uses email as USERNAME_FIELD, use user.email
                # If it uses username, use user.username
                self.user_cache = authenticate(
                    self.request, 
                    username=user.email if hasattr(user, 'USERNAME_FIELD') and user.USERNAME_FIELD == 'email' else user.username,
                    password=password
                )
                
                if self.user_cache is None:
                    logger.warning(f"Failed login attempt for user: {username_or_email}")
                    raise forms.ValidationError(
                        "Invalid username/email or password.",
                        code='invalid_login'
                    )
                else:
                    self.confirm_login_allowed(self.user_cache)
            else:
                logger.warning(f"Login attempt with non-existent user: {username_or_email}")
                raise forms.ValidationError(
                    "Invalid username/email or password.",
                    code='invalid_login'
                )

        return self.cleaned_data

class OTPVerificationForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        label="Enter 6-digit OTP",
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center otp-input',
            'placeholder': '000000',
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'pattern': '[0-9]{6}',
            'autofocus': True,
            'style': 'letter-spacing: 0.5em; font-size: 1.2em;'
        }),
        validators=[RegexValidator(r'^\d{6}$', 'OTP must be exactly 6 digits.')]
    )

    def clean_otp(self):
        otp = self.cleaned_data.get('otp')
        if not otp:
            raise forms.ValidationError("OTP is required.")
        
        if not otp.isdigit():
            raise forms.ValidationError("OTP must contain only numbers.")
        
        if len(otp) != 6:
            raise forms.ValidationError("OTP must be exactly 6 digits.")
        
        return otp

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email address',
            'autofocus': True,
            'autocomplete': 'email'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email is required.")
        
        email = email.lower()
        
        # Don't raise an error here, let the view handle it
        # This allows for proper "security by obscurity" 
        return email

class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New Password (min 8 characters)',
            'autofocus': True,
            'autocomplete': 'new-password'
        })
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm New Password',
            'autocomplete': 'new-password'
        })
    )

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if not password:
            raise forms.ValidationError("Password is required.")
        
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        
        if not any(char.isdigit() for char in password):
            raise forms.ValidationError("Password must contain at least one digit.")
        
        if not any(char.isupper() for char in password):
            raise forms.ValidationError("Password must contain at least one uppercase letter.")
        
        if not any(char.islower() for char in password):
            raise forms.ValidationError("Password must contain at least one lowercase letter.")
        
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("Passwords don't match.")

        return cleaned_data
    

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'phone', 'profile_picture']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'})
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

class EmailChangeForm(forms.Form):
    new_email = forms.EmailField(
        label="New Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new email address',
            'autofocus': True
        })
    )

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        new_email = self.cleaned_data.get('new_email', '').lower()
        
        if self.user and new_email == self.user.email.lower():
            raise forms.ValidationError("This is your current email address.")
        
        if User.objects.filter(email=new_email).exists():
            raise forms.ValidationError("This email is already registered.")
        
        return new_email

class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password'
        })
    )
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        })
    )
    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if self.user and not self.user.check_password(current_password):
            raise forms.ValidationError("Current password is incorrect.")
        return current_password

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if not password:
            raise forms.ValidationError("Password is required.")
        
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        
        if not any(char.isdigit() for char in password):
            raise forms.ValidationError("Password must contain at least one digit.")
        
        if not any(char.isupper() for char in password):
            raise forms.ValidationError("Password must contain at least one uppercase letter.")
        
        if not any(char.islower() for char in password):
            raise forms.ValidationError("Password must contain at least one lowercase letter.")
        
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("New passwords don't match.")

        return cleaned_data

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['full_name', 'phone', 'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country', 'is_default']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address Line 1'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address Line 2 (Optional)'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal Code'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }


