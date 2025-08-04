from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import BaseUserManager


class CustomUserManager(BaseUserManager):
    def create_user(self, email, fullname, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, fullname=fullname, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, fullname, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)

        return self.create_user(email, fullname, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    # Override username to use email instead
    username = None
    email = models.EmailField(unique=True)
    fullname = models.CharField(max_length=255)

    # Role-based flags
    is_admin = models.BooleanField(default=False, help_text="Admin user with full system access")
    has_shipping_address = models.BooleanField(default=False)

    # @property
    # def is_regular_user(self):
    #     """Check if user is a regular user (not admin)"""
    #     return not self.is_admin and not self.is_staff and not self.is_superuser

    objects = CustomUserManager()  # ← Add this line
      
    # Set email as the unique identifier
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['fullname']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email


class ShippingAddress(models.Model):
    """
    User shipping address model
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='shipping_address'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    province = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shipping_addresses'
        verbose_name = 'Shipping Address'
        verbose_name_plural = 'Shipping Addresses'

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.city}"

    def save(self, *args, **kwargs):
        # Automatically set has_shipping_address to True when address is saved
        super().save(*args, **kwargs)
        if not self.user.has_shipping_address:
            self.user.has_shipping_address = True
            self.user.save(update_fields=['has_shipping_address'])
