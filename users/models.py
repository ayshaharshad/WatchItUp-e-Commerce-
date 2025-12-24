from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
import os
from django.core.validators import RegexValidator
import string
import random
from decimal import Decimal

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        blank=True,
        null=True
    )
    
    # Add phone number field
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        null=True,
        help_text="Phone number (optional)"
    )
    referral_code = models.CharField(
        max_length=10, 
        unique=True, 
        blank=True, 
        null=True,
        help_text="Unique referral code for this user"
    )
    referred_by = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='referrals',
        help_text="User who referred this user"
    )
    referral_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of successful referrals"
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

    def save(self, *args, **kwargs):
        # Generate referral code on user creation
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Create wallet for new users
        if is_new:
            Wallet.objects.get_or_create(user=self)
    
    @staticmethod
    def generate_referral_code():
        """Generate a unique 8-character referral code"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not CustomUser.objects.filter(referral_code=code).exists():
                return code
    
    def get_referral_link(self):
        """Get full referral signup link"""
        from django.urls import reverse
        from django.contrib.sites.shortcuts import get_current_site
        # You can customize this to include your domain
        return f"/signup/?ref={self.referral_code}"
    
    @property
    def total_referrals(self):
        """Get total number of users referred"""
        return self.referrals.filter(is_active=True).count()
    
    @property
    def pending_referral_coupons(self):
        """Get unused referral coupons"""
        from products.models import ReferralCoupon
        return ReferralCoupon.objects.filter(
            referrer=self,
            is_used=False
        ).count()
    
    @property
    def wallet_balance(self):
        """Get user's wallet balance"""
        try:
            return self.wallet.balance
        except Wallet.DoesNotExist:
            return Decimal('0.00')


class Wallet(models.Model):
    """User wallet for storing refunds and making payments"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Current wallet balance"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}'s Wallet - ₹{self.balance}"
    
    def add_money(self, amount, transaction_type, description, reference_id=None):
        """Add money to wallet and create transaction record"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        self.balance += Decimal(str(amount))
        self.save()
        
        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=self.balance,
            description=description,
            reference_id=reference_id
        )
        
        return self.balance
    
    def deduct_money(self, amount, transaction_type, description, reference_id=None):
        """Deduct money from wallet and create transaction record"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if self.balance < Decimal(str(amount)):
            raise ValueError("Insufficient wallet balance")
        
        self.balance -= Decimal(str(amount))
        self.save()
        
        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type=transaction_type,
            amount=-amount,  # Negative for deduction
            balance_after=self.balance,
            description=description,
            reference_id=reference_id
        )
        
        return self.balance
    
    def has_sufficient_balance(self, amount):
        """Check if wallet has sufficient balance"""
        return self.balance >= Decimal(str(amount))


class WalletTransaction(models.Model):
    """Transaction history for wallet"""
    TRANSACTION_TYPES = [
        ('credit_refund_cancel', 'Order Cancellation Refund'),
        ('credit_refund_return', 'Order Return Refund'),
        ('credit_admin', 'Admin Credit'),
        ('debit_purchase', 'Order Purchase'),
        ('debit_admin', 'Admin Debit'),
    ]
    
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(
        max_length=30,
        choices=TRANSACTION_TYPES,
        help_text="Type of transaction"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Transaction amount (positive for credit, negative for debit)"
    )
    balance_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Wallet balance after this transaction"
    )
    description = models.CharField(
        max_length=255,
        help_text="Transaction description"
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Order ID or other reference"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['wallet', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.wallet.user.username} - {self.get_transaction_type_display()} - ₹{abs(self.amount)}"
    
    @property
    def is_credit(self):
        """Check if transaction is a credit"""
        return self.amount > 0
    
    @property
    def is_debit(self):
        """Check if transaction is a debit"""
        return self.amount < 0


class Address(models.Model):
    """User shipping address model"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    
    full_name = models.CharField(max_length=150)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(validators=[phone_regex], max_length=17)
    
    address_line1 = models.CharField(max_length=255, verbose_name="Address Line 1")
    address_line2 = models.CharField(max_length=255, blank=True, verbose_name="Address Line 2")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="India")
    
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name_plural = "Addresses"
    
    def __str__(self):
        return f"{self.full_name} - {self.city}, {self.state}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default address per user
        if self.is_default:
            Address.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        # If this is the user's first address, make it default
        if not self.pk and not Address.objects.filter(user=self.user).exists():
            self.is_default = True
        
        super().save(*args, **kwargs)
    
    @property
    def full_address(self):
        """Return formatted full address"""
        parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        return ', '.join([p for p in parts if p])


class EmailChangeRequest(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    new_email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} -> {self.new_email}"

    class Meta:
        ordering = ['-created_at']


