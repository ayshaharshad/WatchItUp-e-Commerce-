from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils.translation import ngettext
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
        'email', 'username',
        'is_email_verified', 'is_active', 'is_staff',
        'created_at', 'profile_picture_preview'
    )
    list_filter = ('is_email_verified', 'is_active', 'is_staff')
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {'fields': ('profile_picture',)}),
        ('Permissions', {
            'fields': (
                'is_active', 'is_email_verified',
                'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            )
        }),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'username',
                'password1', 'password2',
                'is_email_verified', 'is_active', 'is_staff'
            ),
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'last_login')
    search_fields = ('email', 'username')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)

    def profile_picture_preview(self, obj):
        """Show a small preview of the user’s profile picture in admin list/detail."""
        if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
            return format_html(
                '<img src="{}" style="max-height: 50px; border-radius: 5px;" />',
                obj.profile_picture.url
            )
        return "No Image"
    profile_picture_preview.short_description = 'Profile Picture'

    def verify_emails(self, request, queryset):
        """Bulk action to verify selected user emails."""
        updated = queryset.update(is_email_verified=True)
        self.message_user(
            request,
            ngettext(
                "%d user’s email was verified successfully.",
                "%d users’ emails were verified successfully.",
                updated,
            ) % updated
        )
    verify_emails.short_description = "Mark selected users' emails as verified"

    actions = ['verify_emails']


admin.site.register(CustomUser, CustomUserAdmin)




# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin
# from django.utils.html import format_html
# from .models import CustomUser

# class CustomUserAdmin(UserAdmin):
#     model = CustomUser
#     list_display = ('email', 'username', 'phone_number', 'is_email_verified', 'is_active', 'is_staff', 'created_at', 'profile_picture_preview')
#     list_filter = ('is_email_verified', 'is_active', 'is_staff')
#     fieldsets = (
#         (None, {'fields': ('email', 'username', 'password')}),
#         ('Personal Info', {'fields': ('phone_number', 'profile_picture')}),
#         ('Permissions', {'fields': ('is_active', 'is_email_verified', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
#         ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
#     )
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('email', 'username', 'phone_number', 'password', 'is_email_verified', 'is_active', 'is_staff'),
#         }),
#     )
#     readonly_fields = ('created_at', 'updated_at')
#     search_fields = ('email', 'username')
#     ordering = ('email',)
#     filter_horizontal = ('groups', 'user_permissions',)

#     def profile_picture_preview(self, obj):
#         if obj.profile_picture:
#             return format_html('<img src="{}" style="max-height: 50px;" />', obj.profile_picture.url)
#         return "No Image"
#     profile_picture_preview.short_description = 'Profile Picture'

#     def verify_emails(self, request, queryset):
#         """Bulk action to verify user emails"""
#         updated = queryset.update(is_email_verified=True)
#         self.message_user(request, f"{updated} user(s) email(s) verified successfully.")
#     verify_emails.short_description = "Mark selected users' emails as verified"

#     actions = ['verify_emails']

# admin.site.register(CustomUser, CustomUserAdmin)
