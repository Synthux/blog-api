import logging

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import User
from .serializers import RegisterSerializer, UserSerializer

logger = logging.getLogger('users')


class AuthViewSet(viewsets.GenericViewSet):
    """ViewSet for authentication operations."""
    
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def create(self, request) -> Response:
        """Register a new user."""
        email = request.data.get('email')
        logger.info('Registration attempt for email: %s', email)
        
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            logger.info('User registered: %s', user.email)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error('Registration failed for email %s: %s', email, str(e))
            raise
