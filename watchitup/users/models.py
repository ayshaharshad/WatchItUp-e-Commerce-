# users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
import os

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    def delete(self, *args, **kwargs):
        if self.profile_picture and self.profile_picture.path:
            try:
                os.remove(self.profile_picture.path)
            except (ValueError, FileNotFoundError):
                pass
        super().delete(*args, **kwargs)















# from django.contrib.auth.models import AbstractUser
# from django.db import models
# from django.utils import timezone
# from phonenumber_field.modelfields import PhoneNumberField
# import os

# class CustomUser(AbstractUser):
#     email = models.EmailField(unique=True)
#     phone_number = PhoneNumberField(blank=True, null=True)
#     is_email_verified = models.BooleanField(default=False)
#     profile_picture = models.ImageField(
#         upload_to='profile_pics/',
#         blank=True,
#         null=True
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     USERNAME_FIELD = 'email'
#     REQUIRED_FIELDS = ['username']

#     class Meta:
#         indexes = [
#             models.Index(fields=['email']),
#             models.Index(fields=['is_email_verified']),
#         ]

#     def __str__(self):
#         return self.email

#     def delete(self, *args, **kwargs):
#         if self.profile_picture and self.profile_picture.path:
#             try:
#                 if os.path.isfile(self.profile_picture.path):
#                     os.remove(self.profile_picture.path)
#             except ValueError:
#             # Happens if the file is not on disk
#                 pass
#         super().delete(*args, **kwargs)