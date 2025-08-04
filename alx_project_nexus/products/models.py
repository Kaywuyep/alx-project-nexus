from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from cloudinary.models import CloudinaryField
from users.models import User


class Category(models.Model):
    """
    Product Category model
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Product model with all features necccessary
    """
    SIZE_CHOICES = [
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', 'Double Extra Large'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField()
    brand = models.CharField(max_length=100)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products'
    )
    sizes = models.JSONField(
        default=list,
        help_text="List of available sizes: S, M, L, XL, XXL"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='products',
        help_text="User who created this product"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    total_qty = models.PositiveIntegerField(
        default=0,
        help_text="Total quantity in stock"
    )
    total_sold = models.PositiveIntegerField(
        default=0,
        help_text="Total quantity sold"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['brand']),
            models.Index(fields=['price']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.name} - {self.brand}"

    @property
    def qty_left(self):
        """
        Virtual property: Calculate quantity left in stock
        Equivalent to ProductSchema.virtual("qtyLeft")
        """
        return self.total_qty - self.total_sold

    @property
    def total_reviews(self):
        """
        Virtual property: Get total number of reviews
        Equivalent to ProductSchema.virtual("totalReviews")
        """
        return self.reviews.count()

    @property
    def average_rating(self):
        """
        Virtual property: Calculate average rating from reviews
        Equivalent to ProductSchema.virtual("averageRating")
        """
        reviews = self.reviews.all()
        if not reviews:
            return 0.0

        ratings_total = sum(review.rating for review in reviews)
        average = ratings_total / len(reviews)
        return round(average, 1)

    @property
    def is_in_stock(self):
        """
        Check if product is in stock
        """
        return self.qty_left > 0

    @property
    def is_low_stock(self, threshold=5):
        """
        Check if product is low in stock
        """
        return 0 < self.qty_left <= threshold

    def clean(self):
        """
        Custom validation
        """

        # Validate sizes
        valid_sizes = [choice[0] for choice in self.SIZE_CHOICES]
        if self.sizes:
            for size in self.sizes:
                if size not in valid_sizes:
                    raise ValidationError(
                        f"Invalid size: {size}. Valid sizes are: {', '.join(valid_sizes)}")

        # Validate total_sold doesn't exceed total_qty
        if self.total_sold > self.total_qty:
            raise ValidationError("Total sold cannot exceed total quantity")


class ProductImage(models.Model):
    """
    Product Images model using Cloudinary
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = CloudinaryField(
        'image',
        folder='products/',
        transformation=[
            {'width': 800, 'height': 800, 'crop': 'fill'},
            {'quality': 'auto'},
            {'format': 'auto'}
        ]
    )
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Alternative text for accessibility"
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary image for the product"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_images'
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['-is_primary', 'created_at']

    def __str__(self):
        return f"Image for {self.product.name}"

    def save(self, *args, **kwargs):
        # If this is set as primary, remove primary from other images
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)

        super().save(*args, **kwargs)


class Wishlist(models.Model):
    """
    User Wishlist model
    Referenced in User model
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='wishlists'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlisted_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wishlists'
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'
        # Prevent duplicate wishlist entries
        unique_together = ['user', 'product']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.fullname} - {self.product.name}"
