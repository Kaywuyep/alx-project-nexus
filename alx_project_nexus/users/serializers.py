from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, ShippingAddress


class ShippingAddressSerializer(serializers.ModelSerializer):
    """
    Serializer for shipping address
    """
    class Meta:
        model = ShippingAddress
        fields = [
            'first_name', 'last_name', 'address', 'city', 
            'postal_code', 'province', 'country', 'phone'
        ]


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user data
    """
    shipping_address = ShippingAddressSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'fullname', 'is_admin',
            'has_shipping_address', 'shipping_address',
            'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    """
    password = serializers.CharField(
        write_only=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ['email', 'fullname', 'password', 'password_confirm']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            email=validated_data['email'],
            fullname=validated_data['fullname'],
            password=validated_data['password']
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login
    """
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid email or password')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include email and password')
        
        return attrs


# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     """
#     Custom token serializer to include user data in response
#     """
#     @classmethod
#     def get_token(cls, user):
#         token = super().get_token(user)
        
#         # Add custom claims
#         token['email'] = user.email
#         token['fullname'] = user.fullname
#         token['is_admin'] = user.is_admin
        
#         return token

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'  # Tell JWT to use email instead of username

    def validate(self, attrs):
        # Rename "email" to "username" for internal use
        attrs['username'] = attrs.get('email')
        return super().validate(attrs)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['user'] = {
            'email': self.user.email,
            'fullname': self.user.fullname,
        }
        return data


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile
    """
    class Meta:
        model = User
        fields = ['fullname', 'email']
    
    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for admin updating user profile (includes admin status)
    """
    class Meta:
        model = User
        fields = ['fullname', 'email', 'is_admin', 'is_active']
    
    def validate_email(self, value):
        user_id = self.instance.id if self.instance else None
        if User.objects.exclude(pk=user_id).filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for changing password
    """
    old_password = serializers.CharField(style={'input_type': 'password'})
    new_password = serializers.CharField(
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(style={'input_type': 'password'})
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user