from rest_framework import serializers
from .models import Order
from users.models import User


class OrderSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_fullname = serializers.CharField(source='user.fullname', read_only=True)
    is_paid = serializers.BooleanField(read_only=True)
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'user_email', 'user_fullname', 'order_items', 
            'shipping_address', 'order_number', 'payment_status', 
            'payment_method', 'total_price', 'currency', 'status', 
            'delivered_at', 'created_at', 'updated_at', 'is_paid', 'total_items'
        ]
        read_only_fields = ['id', 'order_number', 'created_at', 'updated_at', 'user']


class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            'order_items', 'shipping_address', 'payment_method', 
            'total_price', 'currency'
        ]

    def validate_order_items(self, value):
        if not value or len(value) == 0:
            raise serializers.ValidationError("Order must have at least one item.")
        return value

    def validate_total_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Total price must be greater than 0.")
        return value


class OrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['payment_status', 'status', 'delivered_at']
