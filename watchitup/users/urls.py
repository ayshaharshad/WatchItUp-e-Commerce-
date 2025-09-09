# users/urls.py

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
    path('profile/', views.profile_view, name='profile'),

    # Password reset flow
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/', views.reset_password_view, name='reset_password'),

    # OTP verification
    path('verify-otp/<str:purpose>/', views.verify_otp_view, name='verify_otp'),
    
    # Resend OTP - AJAX endpoint
    path('resend-otp/<str:purpose>/', views.resend_otp_view, name='resend_otp'),
    
    # Resend OTP - Non-AJAX fallback
    path('resend-otp-fallback/<str:purpose>/', views.resend_otp_fallback, name='resend_otp_fallback'),

    
    

    

]






# # users/urls.py
# from django.urls import path
# from . import views

# urlpatterns = [
#     path('', views.root_redirect_view, name='root_redirect'),
#     path('signup/', views.signup_view, name='signup'),
#     path('login/', views.login_view, name='login'),
#     path('logout/', views.logout_view, name='logout'),
#     path('profile/', views.profile_view, name='profile'),
#     path('forgot-password/', views.forgot_password_view, name='forgot_password'),
#     path('reset-password/', views.reset_password_view, name='reset_password'),
#     path('verify-otp/<str:purpose>/', views.verify_otp_view, name='verify_otp'),
#     path('resend-otp/<str:purpose>/', views.resend_otp_view, name='resend_otp'),
#     path('test-email/', views.test_email, name='test_email'),
# ]