from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse

class BlockedUserMiddleware:
    """
    Middleware to prevent blocked users from accessing the website.
    Place this after AuthenticationMiddleware in settings.py
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs that blocked users should still be able to access
        allowed_paths = [
            # Authentication paths
            '/accounts/login/',
            '/accounts/logout/',
            '/accounts/signup/',
            '/accounts/password-reset/',
            
            # Static files
            '/static/',
            '/media/',
            
            # Admin paths
            '/admin/',
            
            # API logout endpoint
            '/api/auth/logout/',
        ]
        
        # Admin panel paths (superusers should always have access)
        admin_panel_paths = [
            '/admin-panel/',
        ]
        
        # Check if user is authenticated but blocked
        if (request.user.is_authenticated and 
            not request.user.is_active and 
            not request.user.is_superuser):
            
            # Allow access to specific paths
            current_path = request.path
            if (any(current_path.startswith(path) for path in allowed_paths) or
                any(current_path.startswith(path) for path in admin_panel_paths)):
                response = self.get_response(request)
                return response
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': 'Account blocked',
                    'message': 'Your account has been blocked. Please contact support.',
                    'redirect': '/accounts/login/'
                }, status=403)
            
            # Block access and logout user
            logout(request)
            messages.error(
                request, 
                "Your account has been blocked. Please contact support for assistance."
            )
            return redirect('login')  # Change to your login URL name
        
        response = self.get_response(request)
        return response