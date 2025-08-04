from rest_framework import generics, permissions, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from django.db.models import F, Avg
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Product, ProductImage, Category, Wishlist
from .serializers import (
    ProductListSerializer, ProductDetailSerializer, ProductCreateSerializer,
    ProductUpdateSerializer, CategorySerializer,
    WishlistSerializer, ProductImageSerializer
)
from users.permissions import IsAdminUser, IsOwnerOrAdmin, IsAdminOrReadOnly
# type: ignore


# Custom FilterSet for Product to handle JSONField
class ProductFilterSet(django_filters.FilterSet):
    # Custom filter for sizes JSONField
    sizes = django_filters.CharFilter(
        method='filter_sizes', help_text='Filter by size (e.g., S, M, L, XL)')

    def filter_sizes(self, queryset, name, value):
        """
        Custom filtering for sizes JSONField
        Assumes sizes is stored as a list in JSON format
        """
        return queryset.filter(sizes__icontains=value)

    class Meta:
        model = Product
        fields = ['category', 'brand']  # Removed 'sizes' from auto-filtering


class CategoryListCreateView(generics.ListCreateAPIView):
    """
    List categories or create new category (Admin only for creation)
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @extend_schema(
        summary="List categories",
        description="Get list of all product categories",
        responses={200: CategorySerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create category (Admin only)",
        description="Create a new product category - Admin access required",
        request=CategorySerializer,
        responses={201: CategorySerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update or delete category (Admin only for modification)
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'id'

    @extend_schema(
        summary="Get category details",
        description="Retrieve detailed information about a specific category",
        responses={200: CategorySerializer}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ProductListCreateView(generics.ListCreateAPIView):
    """
    List products or create new product
    """
    queryset = Product.objects.select_related('category', 'user').prefetch_related('images', 'reviews')
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilterSet  # Changed from filterset_fields to filterset_class
    search_fields = ['name', 'description', 'brand']
    ordering_fields = ['price', 'created_at', 'average_rating', 'total_sold']
    ordering = ['-created_at']
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateSerializer
        return ProductListSerializer

    def get_permissions(self):
        """
        Get list: Anyone can view
        Create: Only authenticated users (admin for now, can be changed)
        """
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by price range
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')

        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        # Filter by stock status
        in_stock = self.request.query_params.get('in_stock')
        if in_stock and in_stock.lower() == 'true':
            queryset = queryset.filter(total_qty__gt=F('total_sold'))

        # Filter by rating
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            # This requires a complex annotation
            queryset = queryset.annotate(
                avg_rating=Avg('reviews__rating')
            ).filter(avg_rating__gte=min_rating)

        return queryset

    @extend_schema(
        summary="List products",
        description="Get list of all products with filtering and search capabilities",
        parameters=[
            OpenApiParameter(
                'category', OpenApiTypes.INT,
                description='Filter by category ID'),
            OpenApiParameter(
                'brand', OpenApiTypes.STR,
                description='Filter by brand'),
            OpenApiParameter(
                'sizes', OpenApiTypes.STR,
                description='Filter by size (e.g., S, M, L, XL)'),
            OpenApiParameter(
                'min_price', OpenApiTypes.NUMBER,
                description='Minimum price filter'),
            OpenApiParameter(
                'max_price', OpenApiTypes.NUMBER,
                description='Maximum price filter'),
            OpenApiParameter(
                'in_stock', OpenApiTypes.BOOL,
                description='Filter products in stock'),
            OpenApiParameter(
                'min_rating', OpenApiTypes.NUMBER,
                description='Minimum rating filter'),
            OpenApiParameter(
                'search', OpenApiTypes.STR,
                description='Search in name, description, brand'),
        ],
        responses={200: ProductListSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create product (Admin only)",
        description="Create a new product with images - Admin access required",
        request=ProductCreateSerializer,
        responses={201: ProductDetailSerializer}
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save()
            return Response({
                'message': 'Product created successfully',
                'product': ProductDetailSerializer(product).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update or delete product
    """
    queryset = Product.objects.select_related('category', 'user').prefetch_related(
        'images', 'reviews__user'
    )
    serializer_class = ProductDetailSerializer
    lookup_field = 'id'

    def get_permissions(self):
        """
        GET: Anyone can view
        PUT/PATCH: Only product owner or admin
        DELETE: Only product owner or admin
        """
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsOwnerOrAdmin()]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductUpdateSerializer
        return ProductDetailSerializer

    @extend_schema(
        summary="Get product details",
        description="Retrieve detailed information about a specific product",
        responses={200: ProductDetailSerializer}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update product",
        description="Update product information - Owner or Admin access required",
        request=ProductUpdateSerializer,
        responses={200: ProductDetailSerializer}
    )
    def patch(self, request, *args, **kwargs):
        product = self.get_object()
        serializer = ProductUpdateSerializer(
            product, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Product updated successfully',
                'product': ProductDetailSerializer(product).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Delete product",
        description="Delete a product - Owner or Admin access required",
        responses={204: OpenApiResponse(description="Product deleted successfully")}
    )
    def delete(self, request, *args, **kwargs):
        product = self.get_object()
        product.delete()
        return Response({
            'message': 'Product deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


class ProductImageUploadView(APIView):
    """
    Upload additional images to existing product
    """
    permission_classes = [IsOwnerOrAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Upload product images",
        description="Upload additional images to an existing product",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'images': {'type': 'array', 'items': {'type': 'string', 'format': 'binary'}},
                    'is_primary': {'type': 'boolean'}
                }
            }
        },
        responses={201: ProductImageSerializer(many=True)}
    )
    def post(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)

            # Check permissions
            if not (request.user.is_admin or product.user == request.user):
                return Response({
                    'error': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)

            uploaded_files = request.FILES.getlist('images')
            is_primary = request.data.get('is_primary', False)

            if not uploaded_files:
                return Response({
                    'error': 'No images provided'
                }, status=status.HTTP_400_BAD_REQUEST)

            created_images = []
            for i, image_file in enumerate(uploaded_files):
                image = ProductImage.objects.create(
                    product=product,
                    image=image_file,
                    is_primary=(is_primary and i == 0),
                    alt_text=f"{product.name} image"
                )
                created_images.append(image)

            return Response({
                'message': f'{len(created_images)} images uploaded successfully',
                'images': ProductImageSerializer(created_images, many=True).data
            }, status=status.HTTP_201_CREATED)

        except Product.DoesNotExist:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)


class WishlistView(generics.ListCreateAPIView):
    """
    List user's wishlist or add product to wishlist
    """
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related('product')

    @extend_schema(
        summary="Get user wishlist",
        description="Get current user's wishlist items",
        responses={200: WishlistSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Add to wishlist",
        description="Add a product to user's wishlist",
        request=WishlistSerializer,
        responses={201: WishlistSerializer}
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Check if product already in wishlist
            product_id = serializer.validated_data['product_id']
            if Wishlist.objects.filter(user=request.user, product_id=product_id).exists():
                return Response({
                    'error': 'Product already in wishlist'
                }, status=status.HTTP_400_BAD_REQUEST)

            wishlist_item = serializer.save()
            return Response({
                'message': 'Product added to wishlist',
                'wishlist_item': WishlistSerializer(wishlist_item).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WishlistDetailView(generics.DestroyAPIView):
    """
    Remove product from wishlist
    """
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)

    @extend_schema(
        summary="Remove from wishlist",
        description="Remove a product from user's wishlist",
        responses={204: OpenApiResponse(description="Product removed from wishlist")}
    )
    def delete(self, request, *args, **kwargs):
        wishlist_item = self.get_object()
        wishlist_item.delete()
        return Response({
            'message': 'Product removed from wishlist'
        }, status=status.HTTP_204_NO_CONTENT)


# ADMIN-SPECIFIC VIEWS
class AdminProductStatsView(APIView):
    """
    Admin dashboard for product statistics
    """
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Product statistics (Admin only)",
        description="Get comprehensive product statistics - Admin access required",
        responses={200: OpenApiResponse(description="Product statistics")}
    )
    def get(self, request):
        total_products = Product.objects.count()
        total_categories = Category.objects.count()
        low_stock_products = Product.objects.filter(
            total_qty__lte=F('total_sold') + 5
        ).count()
        out_of_stock = Product.objects.filter(
            total_qty__lte= F('total_sold')
        ).count()

        # Top selling products
        top_selling = Product.objects.order_by('-total_sold')[:5]

        # Recent products
        recent_products = Product.objects.order_by('-created_at')[:5]

        return Response({
            'total_products': total_products,
            'total_categories': total_categories,
            'low_stock_products': low_stock_products,
            'out_of_stock_products': out_of_stock,
            'top_selling_products': ProductListSerializer(top_selling, many=True).data,
            'recent_products': ProductListSerializer(recent_products, many=True).data,
        })


class AdminLowStockView(generics.ListAPIView):
    """
    Admin view for low stock products
    """
    serializer_class = ProductListSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        threshold = int(self.request.query_params.get('threshold', 5))
        return Product.objects.filter(
            total_qty__lte=F('total_sold') + threshold
        ).order_by('total_qty')

    @extend_schema(
        summary="Low stock products (Admin only)",
        description="Get products with low stock levels - Admin access required",
        parameters=[
            OpenApiParameter('threshold', OpenApiTypes.INT, description='Stock threshold (default: 5)'),
        ],
        responses={200: ProductListSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
