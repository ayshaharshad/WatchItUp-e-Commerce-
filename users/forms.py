from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model, authenticate
from django.core.validators import RegexValidator
from django.db.models import Q
import logging
from .models import Address
from .validators import (
    AlphabeticValidator, 
    PhoneNumberValidator,
    username_regex_validator,
    phone_regex_validator,
    name_regex_validator
)
import re

logger = logging.getLogger(__name__)
User = get_user_model()



class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username (letters, numbers, @/./+/-/_ only)'
        }),
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message='Username can only contain letters, numbers, and @/./+/-/_ characters.',
                code='invalid_username'
            )
        ],
        help_text=''
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address',
            'autofocus': True
        })
    )
    
    # This is for entering the REFERRER's code (who invited you)
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
        fields = ('username', 'email', 'password1', 'password2')  

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password (min 8 characters)'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
        
        self.fields['password1'].help_text = ""
        self.fields['password2'].help_text = ""

    def clean_username(self):
        username = self.cleaned_data.get('username')
        
        # Check if username exists
        if User.objects.filter(username=username).exists():
            logger.warning(f"Signup attempted with duplicate username: {username}")
            raise forms.ValidationError("This username is already taken.")
        
        # Validate minimum length
        if len(username) < 3:
            raise forms.ValidationError("Username must be at least 3 characters long.")
        
        # Validate maximum length
        if len(username) > 30:
            raise forms.ValidationError("Username must be at most 30 characters long.")
        
        # Check if username contains at least one alphanumeric character
        if not re.search(r'[a-zA-Z0-9]', username):
            raise forms.ValidationError("Username must contain at least one letter or number.")
        
        # Reserved usernames
        reserved_usernames = [
            'admin', 'root', 'administrator', 'moderator', 'mod', 
            'support', 'help', 'user', 'guest', 'test', 'system',
            'api', 'www', 'mail', 'ftp', 'blog', 'shop'
        ]
        if username.lower() in reserved_usernames:
            raise forms.ValidationError("This username is reserved and cannot be used.")
        
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        email_lower = email.lower()
        if User.objects.filter(email=email_lower).exists():
            logger.warning(f"Signup attempted with duplicate email: {email}")
            raise forms.ValidationError("This email is already registered.")
        return email_lower
    
    def clean_password2(self):
        """
        Validate that password2 matches password1
        """
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")
        
        return password2
    
    def clean_referral_code(self):
        """
        FIXED: Validate referral code (the code of the person who referred this user)
        This should NOT be assigned to the new user - it's used to find who referred them
        """
        code = self.cleaned_data.get('referral_code', '').strip().upper()
        
        if code:
            # Try to find the user who owns this referral code (the referrer)
            try:
                referrer = User.objects.get(referral_code=code, is_active=True)
                # Store the referrer object for later use in the view
                self.referrer = referrer
                logger.info(f"Valid referral code {code} from user {referrer.email}")
            except User.DoesNotExist:
                logger.warning(f"Invalid referral code attempted: {code}")
                raise forms.ValidationError("Invalid referral code.")
        else:
            # No referral code provided - that's fine
            self.referrer = None
        
        # IMPORTANT: Return the code, NOT assign it to the new user
        # The new user will get their OWN unique code generated automatically
        return code

    def save(self, commit=True):
        """
        Save the user but DON'T assign the referral code to them
        The referral code entered is for finding who referred them
        They'll get their own unique code automatically
        """
        user = super().save(commit=False)
        
        # The user will get their own referral code in the model's save() method
        # We don't touch it here
        
        if commit:
            user.save()
        
        return user


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
    

# class UserProfileForm(forms.ModelForm):
#     class Meta:
#         model = User
#         fields = ['username', 'first_name', 'last_name', 'phone', 'profile_picture']
#         widgets = {
#             'username': forms.TextInput(attrs={'class': 'form-control'}),
#             'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
#             'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
#             'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'}),
#             'profile_picture': forms.FileInput(attrs={'class': 'form-control'})
#         }

#     def clean_username(self):
#         username = self.cleaned_data.get('username')
#         if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
#             raise forms.ValidationError("This username is already taken.")
#         return username


class UserProfileForm(forms.ModelForm):
    """
    Enhanced user profile form with comprehensive validation
    """
    
    # Override fields with custom validators and widgets
    username = forms.CharField(
        max_length=30,
        min_length=3,
        required=True,
        validators=[],  # rely on clean_username only
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username (letters, numbers, @/./+/-/_ only)',
            'pattern': '[a-zA-Z0-9@.+_-]{3,30}',
            'title': 'Letters, numbers, and @ . + - _ only'
        }),
        help_text='3–30 characters. Letters, numbers, and @ . + - _ only.'
    )
    
    first_name = forms.CharField(
        max_length=150,
        required=False,
        validators=[AlphabeticValidator()],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name',
            'pattern': '[a-zA-Z\s]+',
            'title': 'Only alphabetic characters allowed'
        }),
        help_text='Alphabetic characters only.'
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=False,
        validators=[AlphabeticValidator()],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name',
            'pattern': '[a-zA-Z\s]+',
            'title': 'Only alphabetic characters allowed'
        }),
        help_text='Alphabetic characters only.'
    )
    
    phone = forms.CharField(
        max_length=10,
        min_length=10,
        required=False,
        validators=[PhoneNumberValidator()],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '9876543210',
            'pattern': '[6-9][0-9]{9}',
            'inputmode': 'numeric',
            'maxlength': '10',
            'title': '10-digit phone number starting with 6, 7, 8, or 9'
        }),
        help_text='10-digit Indian mobile number (e.g., 9876543210)'
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'phone', 'profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make all fields optional except username
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['phone'].required = False
        self.fields['profile_picture'].required = False
    
    def clean_username(self):
        """
        Comprehensive username validation
        """
        username = self.cleaned_data.get('username', '').strip()
        
        if not username:
            raise forms.ValidationError("Username is required.")
        
        # Length validation
        if len(username) < 3:
            raise forms.ValidationError("Username must be at least 3 characters long.")
        
        if len(username) > 30:
            raise forms.ValidationError("Username must not exceed 30 characters.")
        
        # Format validation - only letters, numbers, underscore
        if not re.match(r'^[a-zA-Z0-9@.+_-]+$', username):
            raise forms.ValidationError(
        "Username can only contain letters, numbers, and @ . + - _."
    )
        
        # Cannot start or end with underscore
        # if username.startswith('_') or username.endswith('_'):
        #     raise forms.ValidationError("Username cannot start or end with underscore.")
        
        # No consecutive underscores
        # if '__' in username:
        #     raise forms.ValidationError("Username cannot contain consecutive underscores.")
        
        # Cannot be only numbers
        if username.isdigit():
            raise forms.ValidationError("Username cannot contain only numbers.")
        
        # Check if username exists (exclude current user)
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This username is already taken.")
        
        # Reserved usernames
        reserved = [
            'admin', 'root', 'administrator', 'moderator', 'support',
            'help', 'user', 'guest', 'test', 'system', 'null', 'undefined'
        ]
        if username.lower() in reserved:
            raise forms.ValidationError("This username is reserved and cannot be used.")
        
        return username
    
    def clean_first_name(self):
        """
        Validate first name - alphabetic characters only
        """
        first_name = self.cleaned_data.get('first_name', '').strip()
        
        if not first_name:
            return first_name  # Optional field
        
        # Length validation
        if len(first_name) > 150:
            raise forms.ValidationError("First name is too long (max 150 characters).")
        
        if len(first_name) < 2:
            raise forms.ValidationError("First name must be at least 2 characters long.")
        
        # Only alphabetic characters and spaces
        if not re.match(r'^[a-zA-Z\s]+$', first_name):
            raise forms.ValidationError(
                "First name can only contain alphabetic characters and spaces."
            )
        
        # No leading/trailing spaces
        if first_name != first_name.strip():
            raise forms.ValidationError("First name cannot have leading or trailing spaces.")
        
        # No consecutive spaces
        if '  ' in first_name:
            raise forms.ValidationError("First name cannot contain consecutive spaces.")
        
        # Capitalize first letter of each word
        first_name = first_name.title()
        
        return first_name
    
    def clean_last_name(self):
        """
        Validate last name - alphabetic characters only
        """
        last_name = self.cleaned_data.get('last_name', '').strip()
        
        if not last_name:
            return last_name  # Optional field
        
        # Length validation
        if len(last_name) > 150:
            raise forms.ValidationError("Last name is too long (max 150 characters).")
        
        if len(last_name) < 2:
            raise forms.ValidationError("Last name must be at least 2 characters long.")
        
        # Only alphabetic characters and spaces
        if not re.match(r'^[a-zA-Z\s]+$', last_name):
            raise forms.ValidationError(
                "Last name can only contain alphabetic characters and spaces."
            )
        
        # No leading/trailing spaces
        if last_name != last_name.strip():
            raise forms.ValidationError("Last name cannot have leading or trailing spaces.")
        
        # No consecutive spaces
        if '  ' in last_name:
            raise forms.ValidationError("Last name cannot contain consecutive spaces.")
        
        # Capitalize first letter of each word
        last_name = last_name.title()
        
        return last_name
    
    def clean_phone(self):
        """
        Validate Indian phone number - exactly 10 digits
        """
        phone = self.cleaned_data.get('phone', '').strip()
        
        if not phone:
            return ''  # Optional field
        
        # Remove any spaces, dashes, or parentheses
        phone_cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        
        # Must be exactly 10 digits
        if not phone_cleaned.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        
        if len(phone_cleaned) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        
        # Indian mobile numbers start with 6, 7, 8, or 9
        if phone_cleaned[0] not in ['6', '7', '8', '9']:
            raise forms.ValidationError(
                "Phone number must start with 6, 7, 8, or 9."
            )
        
        # Check for patterns like 9999999999
        if len(set(phone_cleaned)) == 1:
            raise forms.ValidationError("Please enter a valid phone number.")
        
        # Check for sequential patterns (optional strict check)
        # Uncomment if you want to prevent 1234567890
        # if phone_cleaned in ['0123456789', '1234567890']:
        #     raise forms.ValidationError("Please enter a valid phone number.")
        
        return phone_cleaned
    
    def clean_profile_picture(self):
        """
        Validate profile picture upload
        """
        picture = self.cleaned_data.get('profile_picture')
        
        if picture:
            # Check file size (max 5MB)
            if picture.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image file size must not exceed 5MB.")
            
            # Check file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            import os
            ext = os.path.splitext(picture.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError(
                    f"Invalid file type. Allowed: {', '.join(valid_extensions)}"
                )
            
            # Validate image format
            try:
                from PIL import Image
                img = Image.open(picture)
                img.verify()
            except Exception:
                raise forms.ValidationError("Invalid image file. Please upload a valid image.")
        
        return picture
    
    def clean(self):
        """
        Form-level validation
        """
        cleaned_data = super().clean()
        
        # Additional cross-field validation can go here
        first_name = cleaned_data.get('first_name', '')
        last_name = cleaned_data.get('last_name', '')
        
        # If both names are provided, ensure they're not identical
        if first_name and last_name and first_name.lower() == last_name.lower():
            raise forms.ValidationError(
                "First name and last name cannot be identical."
            )
        
        return cleaned_data

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


