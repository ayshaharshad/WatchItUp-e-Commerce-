import random, logging, json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
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



from .forms import CustomUserCreationForm, CustomAuthenticationForm, OTPVerificationForm, ForgotPasswordForm, ResetPasswordForm
from .models import CustomUser

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
    if request.user.is_authenticated:
        return redirect('products:home')
        
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                # Create user but don't activate yet
                user = form.save(commit=False)
                user.is_active = False
                user.is_email_verified = False
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
            # Form has validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'users/signup.html', {'form': form})

# ------------------ LOGIN ------------------
@never_cache
def login_view(request):
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

# ------------------ LOGOUT ------------------
def logout_view(request):
    username = request.user.username if request.user.is_authenticated else None
    logout(request)
    if username:
        messages.success(request, f"Goodbye, {username}! You've been logged out successfully.")
    return redirect('users:login')

# ------------------ OTP VERIFY ------------------
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
                        
                        clear_otp_session(request)
                        # FIXED: 
                        login(request, user, backend='users.backends.EmailOrUsernameModelBackend')
                        messages.success(request, f"Welcome to Watchitup, {user.username}! Your email has been verified.")
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

# ------------------ PROFILE ------------------
@never_cache
@login_required
def profile_view(request):
    return render(request, 'users/profile.html', {'user': request.user})


















































