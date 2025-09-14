from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Simple custom social account adapter for Google SSO
    """
    
    def pre_social_login(self, request, sociallogin):
        """
        Handle existing users - link accounts if email matches
        """
        email = sociallogin.account.extra_data.get('email')
        
        if email:
            try:
                existing_user = User.objects.get(email=email)
                if not sociallogin.is_existing:
                    sociallogin.connect(request, existing_user)
                    logger.info(f"Linked Google account to existing user: {email}")
            except User.DoesNotExist:
                pass
    
    def populate_user(self, request, sociallogin, data):
        """
        Set user data from Google account
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Trust Google's email verification
        user.is_email_verified = True
        
        # Create unique username from email if needed
        if not user.username and user.email:
            base_username = user.email.split('@')[0]
            username = base_username
            counter = 1
            
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user.username = username
        
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """
        Save and activate the Google user
        """
        user = super().save_user(request, sociallogin, form)
        
        if sociallogin.account.provider == 'google':
            user.is_active = True
            user.is_email_verified = True  # No OTP needed for Google users
            user.save()
            
            messages.success(
                request, 
                f"Welcome to Watchitup, {user.username}! Your Google account has been linked successfully."
            )
            
        return user



# # users/adapters.py

# from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
# from allauth.account.utils import user_email, user_field, user_username
# from django.contrib.auth import get_user_model
# import logging

# logger = logging.getLogger(__name__)
# User = get_user_model()

# class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
#     """
#     Custom social account adapter for Google SSO integration.
    
#     This is REQUIRED because:
#     1. It handles user creation when someone signs up via Google
#     2. It maps Google account data to your CustomUser model
#     3. It automatically verifies email for Google users (since Google already verified it)
#     4. It prevents duplicate accounts by checking existing emails
#     """
    
#     def pre_social_login(self, request, sociallogin):
#         """
#         Called before social login process completes.
#         This prevents duplicate accounts by linking existing users.
#         """
#         # Get email from social account
#         email = sociallogin.account.extra_data.get('email')
        
#         if email:
#             try:
#                 # Check if user with this email already exists
#                 existing_user = User.objects.get(email=email)
                
#                 if not sociallogin.is_existing:
#                     # Link the social account to existing user
#                     sociallogin.connect(request, existing_user)
#                     logger.info(f"Linked Google account to existing user: {email}")
                    
#             except User.DoesNotExist:
#                 # No existing user, will create new one
#                 logger.info(f"New Google user will be created: {email}")
#                 pass
    
#     def populate_user(self, request, sociallogin, data):
#         """
#         Populate user information from social account data.
#         Called when creating a new user via social login.
#         """
#         user = super().populate_user(request, sociallogin, data)
        
#         # Get additional data from Google
#         extra_data = sociallogin.account.extra_data
        
#         # Set email as verified since it comes from Google
#         user.is_email_verified = True
        
#         # Generate username from email if not provided
#         if not user.username and user.email:
#             base_username = user.email.split('@')[0]
#             username = base_username
#             counter = 1
            
#             # Ensure username is unique
#             while User.objects.filter(username=username).exists():
#                 username = f"{base_username}{counter}"
#                 counter += 1
            
#             user.username = username
        
#         logger.info(f"Populated new Google user: {user.email}")
#         return user
    
#     def save_user(self, request, sociallogin, form=None):
#         """
#         Save the social user to database.
#         """
#         user = super().save_user(request, sociallogin, form)
        
#         # Ensure user is active and email verified for Google users
#         if sociallogin.account.provider == 'google':
#             user.is_active = True
#             user.is_email_verified = True
#             user.save()
            
#         logger.info(f"Saved Google user: {user.email}")
#         return user