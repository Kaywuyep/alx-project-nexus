from rest_framework import serializers
from users.serializers import UserSerializer
from reviews.models import Review


class ReviewSerializer(serializers.ModelSerializer):
    """
    Product Review serializer
    """
    user = UserSerializer(read_only=True)
    user_name = serializers.CharField(source='user.fullname', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'user', 'user_name', 'rating', 'comment',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def create(self, validated_data):
        # User is set from the view
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)