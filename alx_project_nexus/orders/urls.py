from django.urls import path
from . import views

urlpatterns = [
    # User order endpoints
    path('orders/', views.OrderListCreateView.as_view(), name='order-list-create'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/stats/', views.user_order_stats, name='user-order-stats'),
    path('orders/<int:order_id>/cancel/', views.cancel_order, name='cancel-order'),

    # Admin order endpoints
    path('admin/orders/', views.AdminOrderListView.as_view(), name='admin-order-list'),
    path('admin/orders/<int:pk>/', views.AdminOrderUpdateView.as_view(), name='admin-order-update'),
]