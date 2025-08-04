from rest_framework import serializers
from django.db import transaction
from users.serializers import UserSerializer
from reviews.serializers import ReviewSerializer
from .models import Product, ProductImage, Category, Wishlist


class CategorySerializer(serializers.ModelSerializer):
    """
    Category serializer
    """
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'products_count', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_products_count(self, obj):
        return obj.products.count()


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Product Image serializer
    """
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = [
            'id', 'image', 'image_url',
            'alt_text', 'is_primary', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None


class ProductListSerializer(serializers.ModelSerializer):
    """
    Product list serializer (minimal data for list views)
    """
    category_name = serializers.CharField(
        source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    qty_left = serializers.ReadOnlyField()
    total_reviews = serializers.ReadOnlyField()
    average_rating = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'brand', 'category_name', 'price',
            'primary_image', 'qty_left', 'total_reviews',
            'average_rating', 'is_in_stock', 'created_at'
        ]

    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return {
                'id': primary_image.id,
                'url': primary_image.image.url,
                'alt_text': primary_image.alt_text
            }
        # Return first image if no primary image
        first_image = obj.images.first()
        if first_image:
            return {
                'id': first_image.id,
                'url': first_image.image.url,
                'alt_text': first_image.alt_text
            }
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Product detail serializer (full data for detail views)
    """
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    user = UserSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)

    # Virtual properties
    qty_left = serializers.ReadOnlyField()
    total_reviews = serializers.ReadOnlyField()
    average_rating = serializers.ReadOnlyField()
    is_in_stock = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'brand', 'category', 'category_id',
            'sizes', 'user', 'images', 'reviews', 'price',
            'total_qty', 'total_sold', 'qty_left', 'total_reviews',
            'average_rating', 'is_in_stock', 'is_low_stock',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def validate_sizes(self, value):
        """Validate sizes against allowed choices"""
        valid_sizes = [choice[0] for choice in Product.SIZE_CHOICES]
        for size in value:
            if size not in valid_sizes:
                raise serializers.ValidationError(
                    f"Invalid size: {size}. Valid sizes are: {', '.join(valid_sizes)}"
                )
        return value

    def validate_colors(self, value):
        """Validate colors list"""
        if not value or not isinstance(value, list):
            raise serializers.ValidationError(
                "Colors must be a non-empty list")
        return value

    def validate(self, attrs):
        """Cross-field validation"""
        if 'total_sold' in attrs and 'total_qty' in attrs:
            if attrs['total_sold'] > attrs['total_qty']:
                raise serializers.ValidationError(
                    "Total sold cannot exceed total quantity"
                )
        return attrs


class ProductCreateSerializer(serializers.ModelSerializer):
    """
    Product creation serializer
    """
    category_id = serializers.IntegerField()
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        help_text="List of images to upload"
    )

    class Meta:
        model = Product
        fields = [
            'name', 'description', 'brand', 'category_id', 'sizes',
            'price', 'total_qty', 'uploaded_images'
        ]

    def validate_category_id(self, value):
        """Validate category exists"""
        if not Category.objects.filter(id=value).exists():
            raise serializers.ValidationError("Category does not exist")
        return value

    def validate_sizes(self, value):
        """Validate sizes"""
        valid_sizes = [choice[0] for choice in Product.SIZE_CHOICES]
        for size in value:
            if size not in valid_sizes:
                raise serializers.ValidationError(
                    f"Invalid size: {size}. Valid sizes are: {', '.join(valid_sizes)}"
                )
        return value

    @transaction.atomic
    def create(self, validated_data):
        """Create product with images"""
        uploaded_images = validated_data.pop('uploaded_images', [])
        category_id = validated_data.pop('category_id')

        # Set category and user
        validated_data['category_id'] = category_id
        validated_data['user'] = self.context['request'].user

        # Create product
        product = Product.objects.create(**validated_data)

        # Create images
        for i, image in enumerate(uploaded_images):
            ProductImage.objects.create(
                product=product,
                image=image,
                is_primary=(i == 0),  # First image is primary
                alt_text=f"{product.name} image {i+1}"
            )

        return product


class ProductUpdateSerializer(serializers.ModelSerializer):
    """
    Product update serializer
    """
    category_id = serializers.IntegerField(required=False)

    class Meta:
        model = Product
        fields = [
            'name', 'description', 'brand', 'category_id', 'sizes',
            'price', 'total_qty', 'total_sold'
        ]

    def validate_category_id(self, value):
        """Validate category exists"""
        if not Category.objects.filter(id=value).exists():
            raise serializers.ValidationError("Category does not exist")
        return value

    def update(self, instance, validated_data):
        """Update product"""
        category_id = validated_data.pop('category_id', None)

        if category_id:
            instance.category_id = category_id

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class WishlistSerializer(serializers.ModelSerializer):
    """
    Wishlist serializer
    """
    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'product_id', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_category_id(self, value):
        """Validate category exists"""
        if not Category.objects.filter(id=value).exists():
            raise serializers.ValidationError("Category does not exist")
        return value

    def create(self, validated_data):
        """Create wishlist item"""
        validated_data['user'] = self.context['request'].user
        product_id = validated_data.pop('product_id')
        validated_data['product_id'] = product_id
        return super().create(validated_data)
