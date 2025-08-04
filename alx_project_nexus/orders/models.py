import random
import string
from django.db import models
from django.utils import timezone
from users.models import User


def generate_order_number():
    """Generate random order number"""
    random_txt = ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=7))
    random_numbers = random.randint(10000, 99999)
    return f"{random_txt}{random_numbers}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    order_items = models.JSONField(
        help_text="List of order items as JSON"
    )

    shipping_address = models.JSONField(
        help_text="Shipping address as JSON object"
    )

    order_number = models.CharField(
        max_length=20,
        unique=True,
        default=generate_order_number,
        db_index=True
    )

    # For stripe payment
    payment_status = models.CharField(
        max_length=50,
        default="Not paid"
    )

    payment_method = models.CharField(
        max_length=100,
        default="Not specified"
    )

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    currency = models.CharField(
        max_length=10,
        default="Not specified"
    )

    # For admin
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def __str__(self):
        return f"Order {self.order_number} - {self.user.email}"

    def save(self, *args, **kwargs):
        # Auto-set delivered_at when status changes to delivered
        if self.status == 'delivered' and not self.delivered_at:
            self.delivered_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_paid(self):
        """Check if order is paid"""
        return self.payment_status.lower() == 'paid'

    @property
    def total_items(self):
        """Get total number of items in order"""
        if isinstance(self.order_items, list):
            return sum(item.get('quantity', 1) for item in self.order_items)
        return 0
