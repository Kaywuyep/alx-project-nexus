from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentication endpoints (accessible to all)
    path('register/', views.RegisterView.as_view(), name='user-register'),
    path("admin/register/", views.AdminRegisterView.as_view(), name="admin-register"),
    path('login/', views.CustomTokenObtainPairView.as_view(), name='user-login'),
    path('logout/', views.LogoutView.as_view(), name='user-logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # User profile endpoints (role-based access)
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('shipping-address/', views.ShippingAddressView.as_view(), name='shipping-address'),

    # Regular user dashboard
    path('dashboard/', views.RegularUserDashboardView.as_view(), name='user-dashboard'),

    # Admin-only endpoints
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin/users/', views.UsersListView.as_view(), name='admin-users-list'),
    path('admin/users/<int:id>/', views.AdminUserDetailView.as_view(), name='admin-user-detail'),
]