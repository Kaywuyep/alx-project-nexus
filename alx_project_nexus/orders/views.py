from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import Order
from .serializers import OrderSerializer, OrderCreateSerializer
from .serializers import OrderUpdateSerializer
from users.decorators import is_logged_in, is_admin_user
from users.permissions import IsOwnerOrAdmin, IsAdminUser


class OrderListCreateView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if getattr(self, 'swagger_fake_view', False) or not user.is_authenticated:
            return Order.objects.none()
        return Order.objects.filter(user=user)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        summary="List user orders",
        description="Get all orders for the authenticated user",
        responses={200: OrderSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create new order",
        description="Create a new order for the authenticated user",
        request=OrderCreateSerializer,
        responses={
            201: OrderSerializer,
            400: OpenApiResponse(description="Bad request")
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if getattr(self, 'swagger_fake_view', False) or not user.is_authenticated:
            return Order.objects.none()
        return Order.objects.filter(user=user)

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return OrderUpdateSerializer
        return OrderSerializer

    @extend_schema(
        summary="Get order details",
        description="Get details of a specific order",
        responses={
            200: OrderSerializer,
            404: OpenApiResponse(description="Order not found")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update order",
        description="Update order details (limited fields)",
        request=OrderUpdateSerializer,
        responses={
            200: OrderSerializer,
            400: OpenApiResponse(description="Bad request"),
            404: OpenApiResponse(description="Order not found")
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


# Admin-only views
class AdminOrderListView(generics.ListAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Admin - List all orders",
        description="Get all orders (admin only)",
        responses={200: OrderSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminOrderUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderUpdateSerializer
    permission_classes = [IsAdminUser]

    @extend_schema(
        summary="Admin - Update order status",
        description="Update order status and payment info (admin only)",
        request=OrderUpdateSerializer,
        responses={
            200: OrderSerializer,
            400: OpenApiResponse(description="Bad request"),
            404: OpenApiResponse(description="Order not found")
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


# Function-based views for specific actions
@api_view(['GET'])
@is_logged_in
@extend_schema(
    summary="Get user order statistics",
    description="Get order statistics for the authenticated user",
    responses={200: {
        'type': 'object',
        'properties': {
            'total_orders': {'type': 'integer'},
            'pending_orders': {'type': 'integer'},
            'completed_orders': {'type': 'integer'},
            'total_spent': {'type': 'number'}
        }
    }}
)
def user_order_stats(request):
    user_orders = Order.objects.filter(user=request.user)

    stats = {
        'total_orders': user_orders.count(),
        'pending_orders': user_orders.filter(status='pending').count(),
        'completed_orders': user_orders.filter(status='delivered').count(),
        'total_spent': float(sum(order.total_price for order in user_orders))
    }

    return Response(stats)


@api_view(['PATCH'])
@is_logged_in
@extend_schema(
    summary="Cancel order",
    description="Cancel a pending order",
    responses={
        200: {'type': 'object', 'properties': {'message': {'type': 'string'}}},
        400: OpenApiResponse(description="Cannot cancel order"),
        404: OpenApiResponse(description="Order not found")
    }
)
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status != 'pending':
        return Response(
            {'error': 'Can only cancel pending orders'},
            status=status.HTTP_400_BAD_REQUEST
        )

    order.status = 'cancelled'
    order.save()

    return Response({'message': 'Order cancelled successfully'})
