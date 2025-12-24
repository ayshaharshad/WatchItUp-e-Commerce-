from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils.translation import ngettext
from .models import CustomUser, Address


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
        'email', 'username',
        'is_email_verified', 'is_active', 'is_staff',
        'referral_code', 'referral_count',  # ✅ Added referral fields
        'created_at', 'profile_picture_preview'
    )
    list_filter = ('is_email_verified', 'is_active', 'is_staff')
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone', 'profile_picture')}),
        # ✅ ADD REFERRAL SECTION
        ('Referral Information', {
            'fields': ('referral_code', 'referred_by', 'referral_count'),
            'classes': ('collapse',)  # Collapsible section
        }),
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
    raw_id_fields = ('referred_by',)  # ✅ Better UX for foreign key

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

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'city', 'state', 'postal_code', 'is_default', 'is_active')
    list_filter = ('is_default', 'is_active', 'country', 'state')
    search_fields = ('user__username', 'user__email', 'full_name', 'phone', 'city')
    list_editable = ('is_default', 'is_active')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'full_name', 'phone')
        }),
        ('Address Details', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Settings', {
            'fields': ('is_default', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


admin.site.register(CustomUser, CustomUserAdmin)




