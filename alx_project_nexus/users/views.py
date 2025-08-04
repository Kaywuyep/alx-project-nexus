from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.contrib.auth import logout

from .models import User, ShippingAddress
from .permissions import IsAdminUser, IsRegularUser, IsOwnerOrAdmin
from .serializers import (
    UserSerializer, UserRegistrationSerializer,
    CustomTokenObtainPairSerializer, UserUpdateSerializer,
    PasswordChangeSerializer, ShippingAddressSerializer
)


class RegisterView(generics.CreateAPIView):
    """
    User registration endpoint
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Register a new user",
        description="Create a new user account with email, fullname and password",
        responses={
            201: OpenApiResponse(description="User created successfully"),
            400: OpenApiResponse(description="Bad request")
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Generate tokens for the new user
            refresh = RefreshToken.for_user(user)

            return Response({
                'message': 'User registered successfully',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminRegisterView(generics.CreateAPIView):
    """
    Register an admin user (staff or superuser)
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]  # You can limit this later

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Make the user an admin
            user.is_admin = True
            user.is_staff = True
            user.is_superuser = True  # Optional
            user.save()

            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Admin user registered successfully',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom login view with user data in response
    """
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        summary="User login",
        description="Authenticate user and return JWT tokens with user data",
        responses={
            200: OpenApiResponse(description="Login successful"),
            401: OpenApiResponse(description="Invalid credentials")
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response(
                {'detail': 'Invalid email or password'},
                status=status.HTTP_401_UNAUTHORIZED)

        user = serializer.user  # Safely get the authenticated user
        tokens = serializer.validated_data  # Contains 'access' and 'refresh'

        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    User logout endpoint
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="User logout",
        description="Logout user and blacklist refresh token",
        responses={
            200: OpenApiResponse(description="Logout successful"),
            400: OpenApiResponse(description="Bad request")
        }
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            logout(request)
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': 'Something went wrong'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get and update user profile - Users can only access their own profile
    """
    serializer_class = UserSerializer
    permission_classes = [IsOwnerOrAdmin]
    
    def get_object(self):
        return self.request.user
    
    @extend_schema(
        summary="Get user profile",
        description="Retrieve current user's profile information",
        responses={200: UserSerializer}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Update user profile",
        description="Update current user's profile information",
        request=UserUpdateSerializer,
        responses={200: UserSerializer}
    )
    def patch(self, request, *args, **kwargs):
        serializer = UserUpdateSerializer(
            self.get_object(), 
            data=request.data, 
            partial=True, 
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully',
                'user': UserSerializer(self.get_object()).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """
    Change user password - Users can only change their own password
    """
    permission_classes = [IsOwnerOrAdmin]
    
    @extend_schema(
        summary="Change password",
        description="Change current user's password",
        request=PasswordChangeSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Bad request")
        }
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, 
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ShippingAddressView(generics.RetrieveUpdateAPIView):
    """
    Get, create or update user's shipping address - Users can only manage their own address
    """
    serializer_class = ShippingAddressSerializer
    permission_classes = [IsOwnerOrAdmin]
    
    def get_object(self):
        shipping_address, created = ShippingAddress.objects.get_or_create(
            user=self.request.user
        )
        return shipping_address
    
    @extend_schema(
        summary="Get shipping address",
        description="Retrieve current user's shipping address",
        responses={200: ShippingAddressSerializer}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Create/Update shipping address",
        description="Create or update current user's shipping address",
        request=ShippingAddressSerializer,
        responses={200: ShippingAddressSerializer}
    )
    def post(self, request, *args, **kwargs):
        return self.update_or_create_address(request)
    
    def patch(self, request, *args, **kwargs):
        return self.update_or_create_address(request)
    
    def update_or_create_address(self, request):
        shipping_address = self.get_object()
        serializer = self.get_serializer(
            shipping_address, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Shipping address updated successfully',
                'shipping_address': serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UsersListView(generics.ListAPIView):
    """
    Admin only - List all users
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return User.objects.all().order_by('-date_joined')
    
    @extend_schema(
        summary="List all users (Admin only)",
        description="Retrieve list of all users - Admin access required",
        responses={200: UserSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# ADMIN-SPECIFIC VIEWS
class AdminDashboardView(APIView):
    """
    Admin dashboard with system statistics
    """
    permission_classes = [IsAdminUser]
    
    @extend_schema(
        summary="Admin dashboard (Admin only)",
        description="Get system statistics and overview - Admin access required",
        responses={200: OpenApiResponse(description="Dashboard data")}
    )
    def get(self, request):
        total_users = User.objects.count()
        admin_users = User.objects.filter(is_admin=True).count()
        regular_users = User.objects.filter(is_admin=False).count()
        users_with_shipping = User.objects.filter(has_shipping_address=True).count()
        
        return Response({
            'total_users': total_users,
            'admin_users': admin_users,
            'regular_users': regular_users,
            'users_with_shipping_address': users_with_shipping,
            'recent_users': UserSerializer(
                User.objects.order_by('-date_joined')[:5], 
                many=True
            ).data
        })


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin only - Get, update or delete specific user
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'id'
    
    @extend_schema(
        summary="Get user details (Admin only)",
        description="Get detailed information about a specific user",
        responses={200: UserSerializer}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Update user (Admin only)",
        description="Update user information including admin status",
        request=UserUpdateSerializer,
        responses={200: UserSerializer}
    )
    def patch(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = UserUpdateSerializer(
            user, 
            data=request.data, 
            partial=True, 
            context={'request': request}
        )
        if serializer.is_valid():
            # Admin can update admin status
            if 'is_admin' in request.data:
                user.is_admin = request.data['is_admin']
                user.save()
            
            serializer.save()
            return Response({
                'message': 'User updated successfully',
                'user': UserSerializer(user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Delete user (Admin only)",
        description="Delete a user account",
        responses={204: OpenApiResponse(description="User deleted successfully")}
    )
    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        if user.is_superuser:
            return Response({
                'error': 'Cannot delete superuser'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.delete()
        return Response({
            'message': 'User deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


# REGULAR USER VIEWS
class RegularUserDashboardView(APIView):
    """
    Regular user dashboard with their personal information
    """
    permission_classes = [IsRegularUser]
    
    @extend_schema(
        summary="User dashboard (Regular users only)",
        description="Get user's personal dashboard information",
        responses={200: OpenApiResponse(description="User dashboard data")}
    )
    def get(self, request):
        user = request.user
        
        # This will be expanded when we add orders, wishlist, etc.
        return Response({
            'user': UserSerializer(user).data,
            'profile_completion': {
                'has_shipping_address': user.has_shipping_address,
                'profile_complete': bool(
                    user.fullname and 
                    user.email and 
                    user.has_shipping_address
                )
            },
            'stats': {
                'total_orders': 0,  # Will be updated when orders app is ready
                'wishlist_items': 0,  # Will be updated when products app is ready
            }
        })