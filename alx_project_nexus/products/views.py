from rest_framework import generics, permissions, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from django.db.models import F, Q, Avg
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.core.paginator import Paginator
from django.db import transaction
import logging

from .models import Product, ProductImage, Category, Wishlist
from .serializers import (
    ProductListSerializer, ProductDetailSerializer, ProductCreateSerializer,
    ProductUpdateSerializer, CategorySerializer,
    WishlistSerializer, ProductImageSerializer
)
from .serializers import ProductSearchSerializer, ProductSearchMinimalSerializer
from users.permissions import IsAdminUser, IsOwnerOrAdmin, IsAdminOrReadOnly
# type: ignore

logger = logging.getLogger(__name__)


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


class ProductListCreateView(generics.ListCreateAPIView):
    """
    List products or create new product with image
    """
    queryset = Product.objects.select_related('category', 'user').prefetch_related('images', 'reviews')
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # Essential for file uploads

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateSerializer
        return ProductListSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [permissions.AllowAny()]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        logger.info(f"📥 Product creation request data: {request.data}")
        logger.info(f"📁 Files in request: {list(request.FILES.keys())}")
        
        serializer = self.get_serializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                product = serializer.save()
                logger.info(f"✅ Product {product.id} created successfully")
                
                # Check if images were created
                images_count = product.images.count()
                logger.info(f"📸 Product has {images_count} images")
                
                response_data = {
                    'message': 'Product created successfully',
                    'id': product.id,
                    'product': ProductDetailSerializer(product, context={'request': request}).data
                }
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"❌ Product creation failed: {str(e)}")
                return Response({
                    'error': 'Product creation failed',
                    'detail': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        logger.error(f"❌ Serializer errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductImageUploadView(APIView):
    """
    Upload additional images to existing product with better error handling
    """
    permission_classes = [IsOwnerOrAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, product_id):
        try:
            logger.info(f"📥 Image upload request for product {product_id}")
            logger.info(f"📁 Files in request: {list(request.FILES.keys())}")
            logger.info(f"📊 Request data: {dict(request.data)}")
            
            product = Product.objects.get(id=product_id)

            # Check permissions
            if not (request.user.is_admin or product.user == request.user):
                return Response({
                    'error': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)

            # Handle both single image and multiple images
            uploaded_files = []

            # Check for single image upload (from frontend)
            if 'image' in request.FILES:
                uploaded_files.append(request.FILES['image'])
                logger.info(f"📷 Single image found: {request.FILES['image'].name}")

            # Check for multiple images upload
            if 'images' in request.FILES:
                uploaded_files.extend(request.FILES.getlist('images'))
                logger.info(f"📷 Multiple images found: {len(request.FILES.getlist('images'))}")

            if not uploaded_files:
                logger.warning("⚠️ No images provided in request")
                return Response({
                    'error': 'No images provided',
                    'available_files': list(request.FILES.keys())
                }, status=status.HTTP_400_BAD_REQUEST)

            is_primary = request.data.get('is_primary', 'false').lower() == 'true'
            logger.info(f"🏷️ Is primary: {is_primary}")

            created_images = []
            errors = []

            with transaction.atomic():
                for i, image_file in enumerate(uploaded_files):
                    try:
                        logger.info(f"📤 Uploading image {i+1}: {image_file.name}")
                        
                        image = ProductImage.objects.create(
                            product=product,
                            image=image_file,
                            is_primary=(is_primary and i == 0),
                            alt_text=f"{product.name} image"
                        )
                        created_images.append(image)
                        logger.info(f"✅ Image {i+1} uploaded successfully. Cloudinary URL: {image.image.url}")
                        
                    except Exception as img_error:
                        error_msg = f"Failed to upload image {i+1}: {str(img_error)}"
                        logger.error(f"❌ {error_msg}")
                        errors.append(error_msg)

            if created_images:
                return Response({
                    'message': f'{len(created_images)} images uploaded successfully',
                    'images': ProductImageSerializer(created_images, many=True, context={'request': request}).data,
                    'errors': errors if errors else None
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'error': 'No images were uploaded successfully',
                    'errors': errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Product.DoesNotExist:
            logger.error(f"❌ Product {product_id} not found")
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"❌ Unexpected error in image upload: {str(e)}")
            return Response({
                'error': 'Unexpected error occurred',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductSearchView(generics.ListAPIView):
    """
    Advanced product search with multiple filters and sorting options

    Query Parameters:
    - q: Search query (searches name, description, brand)
    - category: Category ID or name
    - brand: Brand name
    - min_price: Minimum price
    - max_price: Maximum price
    - sizes: Comma-separated sizes (e.g., "S,M,L")
    - in_stock: Filter by stock availability (true/false)
    - sort: Sorting option (price_asc, price_desc, newest, oldest, rating, popular)
    - page: Page number for pagination
    - page_size: Items per page (default: 20, max: 100)
    - minimal: Return minimal data for faster loading (true/false)
    """

    def get_serializer_class(self):
        if self.request.query_params.get('minimal', '').lower() == 'true':
            return ProductSearchMinimalSerializer
        return ProductSearchSerializer

    def get_queryset(self):
        queryset = Product.objects.select_related('category', 'user').prefetch_related(
            'images', 'reviews'
        )

        # Search query
        query = self.request.query_params.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(brand__icontains=query) |
                Q(category__name__icontains=query)
            )

        # Category filter
        category = self.request.query_params.get('category', '')
        if category:
            if category.isdigit():
                queryset = queryset.filter(category_id=category)
            else:
                queryset = queryset.filter(category__name__icontains=category)

        # Brand filter
        brand = self.request.query_params.get('brand', '')
        if brand:
            queryset = queryset.filter(brand__icontains=brand)

        # Price filters
        min_price = self.request.query_params.get('min_price', '')
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except ValueError:
                pass

        max_price = self.request.query_params.get('max_price', '')
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except ValueError:
                pass

        # Size filter
        sizes = self.request.query_params.get('sizes', '')
        if sizes:
            size_list = [size.strip().upper() for size in sizes.split(',')]
            # Filter products that have any of the requested sizes
            for size in size_list:
                queryset = queryset.filter(sizes__contains=[size])

        # Stock filter
        in_stock = self.request.query_params.get('in_stock', '')
        if in_stock.lower() == 'true':
            # Filter products where total_qty > total_sold
            queryset = queryset.filter(total_qty__gt=F('total_sold'))
        elif in_stock.lower() == 'false':
            # Filter products where total_qty <= total_sold
            queryset = queryset.filter(total_qty__lte=F('total_sold'))

        return queryset

    def get_sorted_queryset(self, queryset):
        """Apply sorting to queryset"""
        sort_param = self.request.query_params.get('sort', 'newest')

        if sort_param == 'price_asc':
            return queryset.order_by('price')
        elif sort_param == 'price_desc':
            return queryset.order_by('-price')
        elif sort_param == 'oldest':
            return queryset.order_by('created_at')
        elif sort_param == 'newest':
            return queryset.order_by('-created_at')
        elif sort_param == 'rating':
            # Sort by average rating (requires annotation)
            return queryset.annotate(
                avg_rating=Avg('reviews__rating')
            ).order_by('-avg_rating', '-created_at')
        elif sort_param == 'popular':
            # Sort by total sold
            return queryset.order_by('-total_sold', '-created_at')
        elif sort_param == 'name_asc':
            return queryset.order_by('name')
        elif sort_param == 'name_desc':
            return queryset.order_by('-name')
        else:
            return queryset.order_by('-created_at')

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            queryset = self.get_sorted_queryset(queryset)

            # Get page size (default 20, max 100)
            page_size = min(int(request.query_params.get('page_size', 20)), 100)
            page_number = int(request.query_params.get('page', 1))

            # Paginate results
            paginator = Paginator(queryset, page_size)
            page = paginator.get_page(page_number)

            # Serialize data
            serializer = self.get_serializer(page.object_list, many=True)

            # Prepare response with metadata
            response_data = {
                'results': serializer.data,
                'pagination': {
                    'current_page': page.number,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'page_size': page_size,
                    'has_next': page.has_next(),
                    'has_previous': page.has_previous(),
                    'next_page': page.next_page_number() if page.has_next() else None,
                    'previous_page': page.previous_page_number() if page.has_previous() else None,
                },
                'filters_applied': {
                    'query': request.query_params.get('q', ''),
                    'category': request.query_params.get('category', ''),
                    'brand': request.query_params.get('brand', ''),
                    'min_price': request.query_params.get('min_price', ''),
                    'max_price': request.query_params.get('max_price', ''),
                    'sizes': request.query_params.get('sizes', ''),
                    'in_stock': request.query_params.get('in_stock', ''),
                    'sort': request.query_params.get('sort', 'newest'),
                }
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {'error': 'Invalid parameter value', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Search failed', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductSearchSuggestionsView(generics.ListAPIView):
    """
    Get search suggestions based on partial query
    """

    def get(self, request, *args, **kwargs):
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response({'suggestions': []})

        # Get product name suggestions
        name_suggestions = Product.objects.filter(
            name__icontains=query
        ).values_list('name', flat=True).distinct()[:5]

        # Get brand suggestions
        brand_suggestions = Product.objects.filter(
            brand__icontains=query
        ).values_list('brand', flat=True).distinct()[:5]

        # Get category suggestions
        category_suggestions = Category.objects.filter(
            name__icontains=query
        ).values_list('name', flat=True).distinct()[:5]

        suggestions = {
            'products': list(name_suggestions),
            'brands': list(brand_suggestions),
            'categories': list(category_suggestions),
        }

        return Response({'suggestions': suggestions})


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
