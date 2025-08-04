import json
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework import generics, permissions, status
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from users.decorators import is_logged_in
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from reviews.serializers import ReviewSerializer
from products.models import Product
from reviews.models import Review


class ProductReviewView(generics.ListCreateAPIView):
    """
    List reviews for a product or create new review
    """
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        product_id = self.kwargs['product_id']
        return Review.objects.filter(product_id=product_id).select_related('user')

    @extend_schema(
        summary="List product reviews",
        description="Get all reviews for a specific product",
        responses={200: ReviewSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create product review",
        description="Create a review for a product - Authentication required",
        request=ReviewSerializer,
        responses={201: ReviewSerializer}
    )
    def post(self, request, *args, **kwargs):
        product_id = self.kwargs['product_id']

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if user already reviewed this product
        if Review.objects.filter(product=product, user=request.user).exists():
            return Response({
                'error': 'You have already reviewed this product'
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(product=product)
            return Response({
                'message': 'Review created successfully',
                'review': serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@require_http_methods(["POST"])
@is_logged_in
def add_product_review_function(request, product_id):
    """
    Function-based view to add product review (Node.js style)
    Equivalent to: POST /api/products/:id/reviews/
    """
    try:
        product = Product.objects.get(id=product_id)

        # Check if user already reviewed this product
        if Review.objects.filter(product=product, user=request.user).exists():
            return JsonResponse({
                'error': 'You have already reviewed this product'
            }, status=status.HTTP_400_BAD_REQUEST)

        data = json.loads(request.body)

        # Validate required fields
        if 'rating' not in data:
            return JsonResponse({
                'error': 'Rating is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate rating range
        rating = int(data['rating'])
        if rating < 1 or rating > 5:
            return JsonResponse({
                'error': 'Rating must be between 1 and 5'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create review
        review = Review.objects.create(
            product=product,
            user=request.user,  # Available from @is_logged_in decorator
            rating=rating,
            comment=data.get('comment', '')
        )

        return JsonResponse({
            'message': 'Review added successfully',
            'review': {
                'id': review.id,
                'rating': review.rating,
                'comment': review.comment,
                'user_name': review.user.fullname,
                'userAuthId': request.userAuthId
            }
        }, status=status.HTTP_201_CREATED)

    except Product.DoesNotExist:
        return JsonResponse({
            'error': 'Product not found'
        }, status=status.HTTP_404_NOT_FOUND)

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON data'
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return JsonResponse({
            'error': 'Failed to add review',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
