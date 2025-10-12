# users/urls.py - Fixed URL structure

from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Root redirect
    path('', views.root_redirect_view, name='root_redirect'),
    
    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password reset flow
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/', views.reset_password_view, name='reset_password'),

    # OTP verification (for signup/password reset)
    path('verify-otp/<str:purpose>/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/<str:purpose>/', views.resend_otp_view, name='resend_otp'),
    path('resend-otp-fallback/<str:purpose>/', views.resend_otp_fallback, name='resend_otp_fallback'),
    
    # Profile Management
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    
    # Email Change
    path('profile/change-email/', views.change_email_view, name='change_email'),
    path('profile/verify-email-change/', views.verify_email_change_view, name='verify_email_change'),
    
    # Address Management - FIXED PATHS
    path('addresses/', views.addresses_view, name='addresses'),
    path('addresses/add/', views.add_address_view, name='add_address'),
    path('addresses/<int:address_id>/edit/', views.edit_address_view, name='edit_address'),
    path('addresses/<int:address_id>/delete/', views.delete_address_view, name='delete_address'),
    path('addresses/<int:address_id>/set-default/', views.set_default_address_view, name='set_default_address'),
]



