import logging

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User

logger = logging.getLogger('users')


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model without password field."""
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'avatar', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    tokens = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'password', 'password_confirm', 'tokens']
        read_only_fields = ['id', 'tokens']
    
    def validate(self, attrs: dict) -> dict:
        """Validate that passwords match."""
        password = attrs.get('password')
        password_confirm = attrs.pop('password_confirm', None)
        
        if password != password_confirm:
            logger.warning('Registration failed: passwords do not match for email %s', attrs.get('email'))
            raise serializers.ValidationError({'password': 'Passwords do not match'})
        
        return attrs
    
    def create(self, validated_data: dict) -> User:
        """Create a new user."""
        email = validated_data['email']
        logger.info('Creating user: %s', email)
        
        user = User.objects.create_user(**validated_data)
        logger.info('User registered successfully: %s', email)
        return user
    
    def get_tokens(self, obj: User) -> dict:
        """Generate JWT tokens for the user."""
        refresh = RefreshToken.for_user(obj)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
