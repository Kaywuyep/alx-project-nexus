import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework import status
from users.decorators import is_logged_in, is_admin_user
from .models import Product, Category, Wishlist


@csrf_exempt
@require_http_methods(["GET"])
def get_products_function(request):
    """
    Function-based view to get all products
    Equivalent to: GET /api/products/
    """
    try:
        # Get query parameters
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
        category = request.GET.get('category')
        brand = request.GET.get('brand')
        search = request.GET.get('search')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')

        # Build queryset
        queryset = Product.objects.select_related('category', 'user').prefetch_related('images', 'reviews')

        # Apply filters
        if category:
            queryset = queryset.filter(category_id=category)

        if brand:
            queryset = queryset.filter(brand__icontains=brand)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search) |
                Q(brand__icontains=search)
            )

        if min_price:
            queryset = queryset.filter(price__gte=min_price)

        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        # Paginate
        paginator = Paginator(queryset, limit)
        products_page = paginator.get_page(page)

        # Serialize data
        products_data = []
        for product in products_page:
            primary_image = product.images.filter(is_primary=True).first()
            products_data.append({
                'id': product.id,
                'name': product.name,
                'brand': product.brand,
                'category_name': product.category.name,
                'price': float(product.price),
                'primary_image': {
                    'url': primary_image.image.url if primary_image else None,
                    'alt_text': primary_image.alt_text if primary_image else ''
                },
                'qty_left': product.qty_left,
                'total_reviews': product.total_reviews,
                'average_rating': product.average_rating,
                'is_in_stock': product.is_in_stock,
                'created_at': product.created_at.isoformat()
            })

        return JsonResponse({
            'products': products_data,
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': products_page.has_next(),
                'has_previous': products_page.has_previous()
            }
        })

    except Exception as e:
        return JsonResponse({
            'error': 'Failed to fetch products',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@require_http_methods(["GET"])
def get_product_detail_function(request, product_id):
    """
    Function-based view to get product details (Node.js style)
    Equivalent to: GET /api/products/:id/
    """
    try:
        product = Product.objects.select_related('category', 'user').prefetch_related(
            'images', 'reviews__user'
        ).get(id=product_id)

        # Serialize product data
        images_data = []
        for image in product.images.all():
            images_data.append({
                'id': image.id,
                'url': image.image.url,
                'alt_text': image.alt_text,
                'is_primary': image.is_primary
            })

        reviews_data = []
        for review in product.reviews.all():
            reviews_data.append({
                'id': review.id,
                'user_name': review.user.fullname,
                'rating': review.rating,
                'comment': review.comment,
                'created_at': review.created_at.isoformat()
            })

        product_data = {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'brand': product.brand,
            'category': {
                'id': product.category.id,
                'name': product.category.name
            },
            'sizes': product.sizes,
            'colors': product.colors,
            'user': {
                'id': product.user.id,
                'fullname': product.user.fullname
            },
            'images': images_data,
            'reviews': reviews_data,
            'price': float(product.price),
            'total_qty': product.total_qty,
            'total_sold': product.total_sold,
            'qty_left': product.qty_left,
            'total_reviews': product.total_reviews,
            'average_rating': product.average_rating,
            'is_in_stock': product.is_in_stock,
            'is_low_stock': product.is_low_stock,
            'created_at': product.created_at.isoformat(),
            'updated_at': product.updated_at.isoformat()
        }

        return JsonResponse({
            'product': product_data
        })

    except Product.DoesNotExist:
        return JsonResponse({
            'error': 'Product not found'
        }, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return JsonResponse({
            'error': 'Failed to fetch product',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@require_http_methods(["POST"])
@is_admin_user
def create_product_function(request):
    """
    Function-based view to create product (Node.js style)
    Equivalent to: POST /api/products/
    """
    try:
        data = json.loads(request.body)

        # Validate required fields
        required_fields = ['name', 'description', 'brand', 'category_id', 'price', 'total_qty']
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'error': f'Missing required field: {field}'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Validate category exists
        try:
            category = Category.objects.get(id=data['category_id'])
        except Category.DoesNotExist:
            return JsonResponse({
                'error': 'Category not found'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create product
        product = Product.objects.create(
            name=data['name'],
            description=data['description'],
            brand=data['brand'],
            category=category,
            sizes=data.get('sizes', []),
            colors=data.get('colors', []),
            user=request.user,  # Available from @is_admin_user decorator
            price=data['price'],
            total_qty=data['total_qty'],
            total_sold=data.get('total_sold', 0)
        )

        return JsonResponse({
            'message': 'Product created successfully',
            'product': {
                'id': product.id,
                'name': product.name,
                'brand': product.brand,
                'price': float(product.price),
                'userAuthId': request.userAuthId  # Available from decorator
            }
        }, status=status.HTTP_201_CREATED)

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON data'
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return JsonResponse({
            'error': 'Failed to create product',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@require_http_methods(["GET", "POST"])
@is_logged_in
def user_wishlist_function(request):
    """
    Function-based view for user wishlist (Node.js style)
    GET: Get user wishlist
    POST: Add product to wishlist
    """
    if request.method == 'GET':
        try:
            wishlist_items = Wishlist.objects.filter(
                user=request.user
            ).select_related('product__category').prefetch_related('product__images')

            wishlist_data = []
            for item in wishlist_items:
                product = item.product
                primary_image = product.images.filter(is_primary=True).first()

                wishlist_data.append({
                    'id': item.id,
                    'product': {
                        'id': product.id,
                        'name': product.name,
                        'brand': product.brand,
                        'price': float(product.price),
                        'primary_image': {
                            'url': primary_image.image.url if primary_image else None
                        },
                        'is_in_stock': product.is_in_stock
                    },
                    'created_at': item.created_at.isoformat()
                })

            return JsonResponse({
                'wishlist': wishlist_data,
                'userAuthId': request.userAuthId
            })

        except Exception as e:
            return JsonResponse({
                'error': 'Failed to fetch wishlist',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')

            if not product_id:
                return JsonResponse({
                    'error': 'Product ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if product exists
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return JsonResponse({
                    'error': 'Product not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Check if already in wishlist
            if Wishlist.objects.filter(user=request.user, product=product).exists():
                return JsonResponse({
                    'error': 'Product already in wishlist'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Add to wishlist
            wishlist_item = Wishlist.objects.create(
                user=request.user,
                product=product
            )

            return JsonResponse({
                'message': 'Product added to wishlist',
                'wishlist_item': {
                    'id': wishlist_item.id,
                    'product_name': product.name
                },
                'userAuthId': request.userAuthId
            }, status=status.HTTP_201_CREATED)

        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return JsonResponse({
                'error': 'Failed to add to wishlist',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
