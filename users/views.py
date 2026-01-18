import random, logging, json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from django.db import transaction
from datetime import timedelta
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Wallet, WalletTransaction
from django.views.decorators.http import require_http_methods




from .forms import (CustomUserCreationForm, CustomAuthenticationForm, OTPVerificationForm, 
                   ForgotPasswordForm, ResetPasswordForm, UserProfileForm, EmailChangeForm, ChangePasswordForm, AddressForm)
from .models import CustomUser, Address, EmailChangeRequest

logger = logging.getLogger(__name__)

# ------------------ UTILS ------------------
def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp, purpose='verification'):
    """Send OTP email with proper error handling"""
    try:
        subject_map = {
            'signup': 'Welcome to Watchitup - Verify Your Email',
            'reset': 'Watchitup - Password Reset OTP'
        }
        
        subject = subject_map.get(purpose, 'Watchitup - OTP Verification')
        message = f"""
        Hello!
        
        Your OTP for Watchitup is: {otp}
        
        This OTP will expire in 5 minutes.
        
        If you didn't request this, please ignore this email.
        
        Best regards,
        Watchitup Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False
        )
        logger.info(f"OTP email sent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        return False

def clear_otp_session(request):
    """Clear OTP-related session data"""
    keys_to_remove = ['otp', 'otp_user', 'otp_timestamp', 'otp_verified']
    for key in keys_to_remove:
        request.session.pop(key, None)

def is_otp_valid(request):
    """Check if OTP is still valid (within time limit)"""
    timestamp = request.session.get('otp_timestamp')
    if not timestamp:
        return False
    
    otp_age = timezone.now().timestamp() - timestamp
    return otp_age <= getattr(settings, 'OTP_EXPIRY_TIME', 300)

# ------------------ ROOT REDIRECT ------------------
def root_redirect_view(request):
    if request.user.is_authenticated:
        return redirect('products:home')
    return redirect('users:login')

# ------------------ SIGNUP ------------------
@never_cache
@transaction.atomic
def signup_view(request):
    
    # Clear old messages at the start
    list(messages.get_messages(request))

    if request.user.is_authenticated:
        return redirect('products:home')
    
    ref_code = request.GET.get('ref', '').strip().upper()
        
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                # Create user but don't activate yet
                user = form.save(commit=False)
                user.is_active = False
                user.is_email_verified = False
                user.save()

                # Handle referral
                referral_code = form.cleaned_data.get('referral_code')
                if referral_code and hasattr(form, 'referrer'):
                    user.referred_by = form.referrer
                
                user.save()

                # Generate and store OTP
                otp = generate_otp()
                request.session['otp'] = otp
                request.session['otp_user'] = user.id
                request.session['otp_timestamp'] = timezone.now().timestamp()
                request.session.set_expiry(600)  # 10 minutes

                # Send OTP email
                if send_otp_email(user.email, otp, 'signup'):
                    messages.success(request, f"Account created! Please check your email ({user.email}) for the OTP.")
                    return redirect('users:verify_otp', purpose='signup')
                else:
                    # If email fails, delete the user and show error
                    user.delete()
                    messages.error(request, "Failed to send verification email. Please try again.")
                    
            except Exception as e:
                logger.error(f"Signup error: {str(e)}")
                messages.error(request, "An error occurred during signup. Please try again.")
    else:
        # Pre-fill referral code if present in URL
        initial_data = {}
        if ref_code:
            initial_data['referral_code'] = ref_code
        
        form = CustomUserCreationForm(initial=initial_data)
    
    return render(request, 'users/signup.html', {'form': form, 'ref_code': ref_code})


def process_referral_signup(user):
    """
    Process referral after successful signup.
    Call this function in verify_otp_view after user is activated.
    """
    from products.models import Coupon, ReferralCoupon
    from datetime import timedelta
    
    if not user.referred_by:
        return
    
    try:
        # Create referral coupon for referrer
        referrer = user.referred_by
        
        # Generate unique coupon code
        coupon_code = f"REF{referrer.referral_code[:4]}{user.id}"
        
        # Create coupon (10% discount, valid for 30 days)
        coupon = Coupon.objects.create(
            code=coupon_code,
            discount_type='percentage',
            discount_value=Decimal('10'),  # 10% discount
            minimum_amount=Decimal('500'),  # Minimum order ₹500
            max_discount=Decimal('200'),  # Max ₹200 discount
            valid_from=timezone.now(),
            valid_to=timezone.now() + timedelta(days=30),
            is_active=True,
            usage_limit=1,
            usage_per_user=1
        )
        
        # Create referral coupon record
        ReferralCoupon.objects.create(
            referrer=referrer,
            referred_user=user,
            coupon=coupon
        )
        
        # Increment referrer's count
        referrer.referral_count += 1
        referrer.save()
        
        logger.info(f"Referral processed: {referrer.username} referred {user.username}")
        
    except Exception as e:
        logger.error(f"Error processing referral: {str(e)}")

# ------------------ LOGIN ------------------
@never_cache
def login_view(request):

    # Clear old messages at the start
    list(messages.get_messages(request))

    if request.user.is_authenticated:
        return redirect('products:home')
        
    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if not user.is_active:
                    messages.error(request, "Your account is inactive. Please contact support.")
                elif not user.is_email_verified:
                    messages.error(request, "Please verify your email address before logging in.")
                else:
                    
                    login(request, user, backend='users.backends.EmailOrUsernameModelBackend')
                    messages.success(request, f"Welcome back, {user.username}!")
                    next_url = request.GET.get('next', 'products:home')
                    return redirect(next_url)
            else:
                messages.error(request, "Invalid email/username or password.")
        else:
            # Form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'users/login.html', {'form': form})


# # ------------------ LOGOUT ------------------

def logout_view(request):
    username = request.user.username if request.user.is_authenticated else None
    logout(request)
    # Clear all queued messages
    list(messages.get_messages(request))  

    if username:
        messages.success(request, f"Goodbye, {username}! You've been logged out successfully.")
    return redirect('users:login')



@never_cache
def verify_otp_view(request, purpose):

    if not request.session.get('otp') or not request.session.get('otp_user'):
        messages.error(request, "No OTP verification in progress. Please start over.")
        if purpose == 'signup':
            return redirect('users:signup')
        else:
            return redirect('users:forgot_password')
    
    if not is_otp_valid(request):
        messages.error(request, "OTP has expired. Please request a new one.")
        return redirect('users:resend_otp', purpose=purpose)
    
    if request.method == "POST":
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']
            stored_otp = request.session.get('otp')
            
            if entered_otp == stored_otp:
                try:
                    user = get_object_or_404(CustomUser, id=request.session['otp_user'])
                    
                    if purpose == 'signup':
                        user.is_active = True
                        user.is_email_verified = True
                        user.save()

                        process_referral_signup(user)
                        
                        clear_otp_session(request)
                        # FIXED: 
                        login(request, user, backend='users.backends.EmailOrUsernameModelBackend')
                        
                        # Show success message with referral info
                        if user.referred_by:
                            messages.success(
                                request, 
                                f"Welcome {user.username}! You were referred by {user.referred_by.username}. "
                                f"They've received a special coupon as a thank you!"
                            )
                        else:
                            messages.success(request, f"Welcome to Watchitup, {user.username}!")
                        return redirect('products:home')
                        
                    elif purpose == 'reset':
                        request.session['otp_verified'] = True
                        messages.success(request, "OTP verified. You can now reset your password.")
                        return redirect('users:reset_password')
                        
                except CustomUser.DoesNotExist:
                    clear_otp_session(request)
                    messages.error(request, "User not found. Please try again.")
                    return redirect('users:signup' if purpose == 'signup' else 'users:forgot_password')
            else:
                messages.error(request, "Invalid OTP. Please check and try again.")
        else:
            for error in form.errors.get('otp', []):
                messages.error(request, error)
    else:
        form = OTPVerificationForm()
    
    # Calculate remaining time for template
    timestamp = request.session.get('otp_timestamp', 0)
    current_time = timezone.now().timestamp()
    time_remaining = max(0, int(getattr(settings, 'OTP_EXPIRY_TIME', 300) - (current_time - timestamp)))
    
    context = {
        'form': form,
        'purpose': purpose,
        'time_remaining': time_remaining
    }
    return render(request, 'users/verify_otp.html', context)

# ------------------ RESEND OTP ------------------
@require_POST
def resend_otp_view(request, purpose):
    if not request.session.get('otp_user'):
        return JsonResponse({'success': False, 'message': 'No active OTP session'})
    
    try:
        user = get_object_or_404(CustomUser, id=request.session['otp_user'])
        otp = generate_otp()
        
        # Update session with new OTP
        request.session['otp'] = otp
        request.session['otp_timestamp'] = timezone.now().timestamp()
        
        # Send email
        email_purpose = 'signup' if purpose == 'signup' else 'reset'
        if send_otp_email(user.email, otp, email_purpose):
            return JsonResponse({
                'success': True, 
                'message': f'New OTP sent to {user.email}'
            })
        else:
            return JsonResponse({
                'success': False, 
                'message': 'Failed to send email. Please try again.'
            })
            
    except Exception as e:
        logger.error(f"Resend OTP error: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': 'An error occurred. Please try again.'
        })

# Non-AJAX fallback
def resend_otp_fallback(request, purpose):
    if not request.session.get('otp_user'):
        messages.error(request, "No active OTP session.")
        return redirect('users:signup' if purpose == 'signup' else 'users:forgot_password')
    
    try:
        user = get_object_or_404(CustomUser, id=request.session['otp_user'])
        otp = generate_otp()
        request.session['otp'] = otp
        request.session['otp_timestamp'] = timezone.now().timestamp()
        
        email_purpose = 'signup' if purpose == 'signup' else 'reset'
        if send_otp_email(user.email, otp, email_purpose):
            messages.success(request, f"New OTP sent to {user.email}")
        else:
            messages.error(request, "Failed to send email. Please try again.")
            
    except Exception as e:
        logger.error(f"Resend OTP fallback error: {str(e)}")
        messages.error(request, "An error occurred. Please try again.")
    
    return redirect('users:verify_otp', purpose=purpose)

# ------------------ FORGOT PASSWORD ------------------
@never_cache
def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect('products:home')
        
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = CustomUser.objects.get(email=email)
                
                # Generate OTP and store in session
                otp = generate_otp()
                request.session['otp'] = otp
                request.session['otp_user'] = user.id
                request.session['otp_timestamp'] = timezone.now().timestamp()
                request.session.set_expiry(600)  # 10 minutes
                
                # Send OTP email
                if send_otp_email(user.email, otp, 'reset'):
                    messages.success(request, f"Reset OTP sent to {email}")
                    return redirect('users:verify_otp', purpose='reset')
                else:
                    messages.error(request, "Failed to send reset email. Please try again.")
                    
            except CustomUser.DoesNotExist:
                # Don't reveal if email exists or not for security
                messages.success(request, f"If an account with {email} exists, a reset OTP has been sent.")
                return redirect('users:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = ForgotPasswordForm()
    
    return render(request, 'users/forgot_password.html', {'form': form})

# ------------------ RESET PASSWORD ------------------
@never_cache
def reset_password_view(request):
    if not request.session.get('otp_verified') or not request.session.get('otp_user'):
        messages.error(request, "Please verify your OTP first.")
        return redirect('users:forgot_password')
    
    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            try:
                user = get_object_or_404(CustomUser, id=request.session['otp_user'])
                new_password = form.cleaned_data['new_password']
                
                user.set_password(new_password)
                user.save()
                
                # Clear all session data
                clear_otp_session(request)
                
                messages.success(request, "Password reset successful! Please login with your new password.")
                return redirect('users:login')
                
            except CustomUser.DoesNotExist:
                clear_otp_session(request)
                messages.error(request, "User not found. Please try again.")
                return redirect('users:forgot_password')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = ResetPasswordForm()
    
    return render(request, 'users/reset_password.html', {'form': form})


# ------------------ PROFILE VIEWS ------------------

@login_required
def profile_view(request):
    """Display user profile with basic info and addresses"""
    addresses = Address.objects.filter(user=request.user)
    context = {
        'user': request.user,
        'addresses': addresses
    }
    return render(request, 'users/profile/profile.html', context)

@login_required
@transaction.atomic
def edit_profile_view(request):
    """
    Enhanced edit user profile with comprehensive validation
    """
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        
        if form.is_valid():
            try:
                # Handle profile picture deletion if requested
                if 'delete_picture' in request.POST and request.user.profile_picture:
                    # Delete the old picture file
                    old_picture = request.user.profile_picture
                    request.user.profile_picture = None
                    request.user.save()
                    
                    # Delete file from storage
                    if old_picture:
                        try:
                            old_picture.delete(save=False)
                        except Exception as e:
                            logger.warning(f"Failed to delete old profile picture: {e}")
                
                # Save the form
                user = form.save(commit=False)
                
                # Additional server-side checks (belt and suspenders approach)
                if user.username:
                    user.username = user.username.strip()
                if user.first_name:
                    user.first_name = user.first_name.strip().title()
                if user.last_name:
                    user.last_name = user.last_name.strip().title()
                if user.phone:
                    user.phone = user.phone.strip()
                
                user.save()
                
                messages.success(
                    request, 
                    '<i class="fas fa-check-circle me-2"></i>Profile updated successfully!',
                    extra_tags='safe'
                )
                return redirect('users:profile')
                
            except Exception as e:
                logger.error(f"Error updating profile for user {request.user.id}: {str(e)}")
                messages.error(
                    request,
                    '<i class="fas fa-exclamation-triangle me-2"></i>An error occurred while updating your profile. Please try again.',
                    extra_tags='safe'
                )
        else:
            # Form has validation errors
            # Django messages will show field-specific errors from the template
            messages.error(
                request,
                '<i class="fas fa-exclamation-triangle me-2"></i>Please correct the errors below.',
                extra_tags='safe'
            )
    else:
        form = UserProfileForm(instance=request.user)
    
    context = {
        'form': form,
        'user': request.user
    }
    return render(request, 'users/profile/edit_profile.html', context)


# ------------------ EMAIL CHANGE VIEWS ------------------

@login_required
def change_email_view(request):
    """Request email change with OTP verification"""
    if request.method == 'POST':
        form = EmailChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            new_email = form.cleaned_data['new_email']
            
            # Clear any existing email change requests for this user
            EmailChangeRequest.objects.filter(user=request.user).delete()
            
            # Generate OTP and create request
            otp = generate_otp()
            expires_at = timezone.now() + timedelta(minutes=5)
            
            email_change_request = EmailChangeRequest.objects.create(
                user=request.user,
                new_email=new_email,
                otp=otp,
                expires_at=expires_at
            )
            
            # Store in session for verification
            request.session['email_change_otp'] = otp
            request.session['email_change_new_email'] = new_email
            request.session['email_change_timestamp'] = timezone.now().timestamp()
            request.session.set_expiry(300)  # 5 minutes
            
            # Send OTP to new email
            if send_otp_email(new_email, otp, 'email_change'):
                messages.success(request, f'OTP sent to {new_email}. Please verify to change your email.')
                return redirect('users:verify_email_change')
            else:
                messages.error(request, 'Failed to send OTP. Please try again.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = EmailChangeForm(user=request.user)
    
    return render(request, 'users/profile/change_email.html', {'form': form})

@login_required
def verify_email_change_view(request):
    """Verify OTP for email change"""
    if not all(k in request.session for k in ['email_change_otp', 'email_change_new_email']):
        messages.error(request, 'No email change request found. Please start over.')
        return redirect('users:change_email')
    
    # Check if OTP is still valid
    timestamp = request.session.get('email_change_timestamp', 0)
    if timezone.now().timestamp() - timestamp > 300:  # 5 minutes
        messages.error(request, 'OTP has expired. Please request a new one.')
        return redirect('users:change_email')
    
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']
            stored_otp = request.session.get('email_change_otp')
            new_email = request.session.get('email_change_new_email')
            
            if entered_otp == stored_otp:
                try:
                    # Update user's email
                    request.user.email = new_email
                    request.user.save()
                    
                    # Clear session data
                    keys_to_clear = ['email_change_otp', 'email_change_new_email', 'email_change_timestamp']
                    for key in keys_to_clear:
                        request.session.pop(key, None)
                    
                    # Clear database request
                    EmailChangeRequest.objects.filter(user=request.user).delete()
                    
                    messages.success(request, f'Email successfully changed to {new_email}')
                    return redirect('users:profile')
                    
                except Exception as e:
                    logger.error(f"Email change error: {str(e)}")
                    messages.error(request, 'An error occurred while changing email.')
            else:
                messages.error(request, 'Invalid OTP. Please try again.')
        else:
            for error in form.errors.get('otp', []):
                messages.error(request, error)
    else:
        form = OTPVerificationForm()
    
    # Calculate remaining time
    timestamp = request.session.get('email_change_timestamp', 0)
    time_remaining = max(0, int(300 - (timezone.now().timestamp() - timestamp)))
    
    context = {
        'form': form,
        'new_email': request.session.get('email_change_new_email'),
        'time_remaining': time_remaining
    }
    return render(request, 'users/profile/verify_email_change.html', context)

# ------------------ PASSWORD CHANGE VIEWS ------------------

@login_required
def change_password_view(request):
    """Change user password - CORRECT real-world implementation"""
    if request.method == 'POST':
        form = ChangePasswordForm(user=request.user, data=request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            
            # Change the password
            request.user.set_password(new_password)
            request.user.save()
            
            # ✅ CRITICAL: Keep the user logged in after password change
            # This prevents the user from being logged out after changing password
            update_session_auth_hash(request, request.user)
            
            # Optional: Log out all OTHER sessions (security best practice)
            # This kicks out anyone else who might be using the account
            # but keeps the current session active
            from django.contrib.sessions.models import Session
            from django.utils import timezone
            
            # Get all sessions for this user except current one
            current_session_key = request.session.session_key
            user_sessions = Session.objects.filter(expire_date__gte=timezone.now())
            
            for session in user_sessions:
                session_data = session.get_decoded()
                if session_data.get('_auth_user_id') == str(request.user.id):
                    if session.session_key != current_session_key:
                        session.delete()  # Delete other sessions
            
            messages.success(request, 'Password changed successfully! All other login sessions have been terminated for security.')
            return redirect('users:profile')  # ✅ Stay logged in, go to profile
            
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = ChangePasswordForm(user=request.user)
    
    return render(request, 'users/profile/change_password.html', {'form': form})

# ------------------ ADDRESS MANAGEMENT VIEWS ------------------


@login_required
def addresses_view(request):
    """Display all user addresses"""
    addresses = Address.objects.filter(user=request.user)
    context = {
        'addresses': addresses
    }
    return render(request, 'users/addresses/addresses.html', context)

@login_required
@require_POST
def set_default_address_view(request, address_id):
    """Set an address as default"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    # Remove default from all other addresses
    Address.objects.filter(user=request.user).update(is_default=False)
    
    # Set this address as default
    address.is_default = True
    address.save()
    
    messages.success(request, f'"{address.full_name}" set as default address.')
    return redirect('users:addresses')


# Add this new view for AJAX address submission from checkout
@login_required
@require_POST
def add_address_ajax_view(request):
    """Add address via AJAX from checkout page"""
    form = AddressForm(request.POST)
    
    if form.is_valid():
        address = form.save(commit=False)
        address.user = request.user
        address.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Address added successfully!',
            'address': {
                'id': address.id,
                'full_name': address.full_name,
                'address_line1': address.address_line1,
                'address_line2': address.address_line2,
                'city': address.city,
                'state': address.state,
                'postal_code': address.postal_code,
                'phone': address.phone,
                'is_default': address.is_default,
                'full_address': address.full_address
            }
        })
    else:
        # Return form errors
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [str(error) for error in error_list]
        
        return JsonResponse({
            'success': False,
            'errors': errors
        })
@login_required
def add_address_view(request):
    """Add new address with optional redirect to checkout"""
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, 'Address added successfully!')
            
            # ✅ FIX: Check if coming from checkout
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url == 'checkout':
                # Redirect back to checkout view in products app
                return redirect('products:checkout_view')  # ✅ FIXED: Use correct namespace
            
            return redirect('users:addresses')  # Default redirect to addresses page
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = AddressForm()
    
    # ✅ FIX: Get the next parameter to pass to template
    next_url = request.GET.get('next', '')
    
    return render(request, 'users/addresses/add_address.html', {
        'form': form,
        'next': next_url  # Pass to template
    })



@login_required
def edit_address_view(request, address_id):
    """Edit existing address with optional redirect to checkout"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, 'Address updated successfully!')
            
            # FIXED: Check if coming from checkout
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url == 'checkout':
                return redirect('products:checkout_view')
            
            return redirect('users:profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = AddressForm(instance=address)
    
    # FIXED: Get the next parameter to pass to template
    next_url = request.GET.get('next', '')
    
    return render(request, 'users/addresses/edit_address.html', {
        'form': form,
        'address': address,
        'next': next_url
    })


@login_required
def delete_address_view(request, address_id):
    """Delete address"""
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted successfully!')
        
        # FIXED: Check if coming from checkout
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url == 'checkout':
            return redirect('products:checkout_view')
        
        return redirect('users:profile')
    
    # FIXED: Pass next parameter to template for delete confirmation
    next_url = request.GET.get('next', '')
    
    return render(request, 'users/addresses/delete_address.html', {
        'address': address,
        'next': next_url
    })

# ------------------ UTILITY FUNCTIONS ------------------

def send_otp_email(email, otp, purpose='verification'):
    """Enhanced send OTP email function"""
    try:
        subject_map = {
            'signup': 'Welcome to Watchitup - Verify Your Email',
            'reset': 'Watchitup - Password Reset OTP',
            'email_change': 'Watchitup - Email Change Verification'
        }
        
        subject = subject_map.get(purpose, 'Watchitup - OTP Verification')
        
        if purpose == 'email_change':
            message = f"""
            Hello!
            
            You have requested to change your email address on Watchitup.
            
            Your verification OTP is: {otp}
            
            This OTP will expire in 5 minutes.
            
            If you didn't request this change, please ignore this email and your current email will remain unchanged.
            
            Best regards,
            Watchitup Team
            """
        else:
            message = f"""
            Hello!
            
            Your OTP for Watchitup is: {otp}
            
            This OTP will expire in 5 minutes.
            
            If you didn't request this, please ignore this email.
            
            Best regards,
            Watchitup Team
            """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False
        )
        logger.info(f"OTP email sent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        return False


# ------------------ WALLET VIEWS ------------------

@login_required
def wallet_view(request):
    """Display user's wallet balance and transaction history"""
    # Get or create wallet
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # Get all transactions
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')
    
    # Add abs_amount attribute for template display
    for t in transactions:
        t.abs_amount = abs(t.amount)
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(transactions, 15)
    
    try:
        transactions_page = paginator.page(page)
    except PageNotAnInteger:
        transactions_page = paginator.page(1)
    except EmptyPage:
        transactions_page = paginator.page(paginator.num_pages)
    
    # Calculate totals
    total_credits = sum(t.amount for t in transactions if t.is_credit)
    total_debits = abs(sum(t.amount for t in transactions if t.is_debit))
    
    context = {
        'wallet': wallet,
        'transactions': transactions_page,
        'total_credits': total_credits,
        'total_debits': total_debits,
        'total_transactions': transactions.count()
    }
    return render(request, 'users/profile/wallet.html', context)


@login_required
def wallet_transaction_detail(request, transaction_id):
    """View detailed information about a specific transaction"""
    transaction = get_object_or_404(
        WalletTransaction,
        id=transaction_id,
        wallet__user=request.user
    )
    
    context = {
        'transaction': transaction
    }
    return render(request, 'users/wallet/transaction_detail.html', context)









































