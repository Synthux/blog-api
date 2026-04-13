import logging

from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .tasks import send_welcome_email_task
from .serializers import (
    LanguageSerializer,
    RegisterSerializer,
    TimezoneSerializer,
)

logger = logging.getLogger('users')


class AuthViewSet(viewsets.GenericViewSet):
    """ViewSet for authentication operations."""
    
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth'],
        summary='Register a new user',
        description=(
            'Creates a new user account and returns the user data along with '
            'a JWT token pair. Sends a welcome email in the user\'s chosen language. '
            'Rate-limited to 5 requests/minute per IP. Returns 429 when exceeded.'
        ),
        request=RegisterSerializer,
        responses={
            201: RegisterSerializer,
            400: OpenApiResponse(description='Validation errors (e.g. passwords do not match)'),
            429: OpenApiResponse(description='Too many requests'),
        },
        examples=[
            OpenApiExample(
                'Register request',
                value={
                    'email': 'alice@example.com',
                    'first_name': 'Alice',
                    'last_name': 'Smith',
                    'password': 'securepass123',
                    'password_confirm': 'securepass123',
                },
                request_only=True,
            ),
            OpenApiExample(
                'Register response',
                value={
                    'id': 1,
                    'email': 'alice@example.com',
                    'tokens': {'access': '...', 'refresh': '...'},
                },
                response_only=True,
            ),
        ],
    )
    
    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True))
    def create(self, request) -> Response:
        """Register a new user."""
        email = request.data.get('email')
        logger.info('Registration attempt for email: %s', email)
        
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            # Fire welcome email asynchronously — does not block the response
            send_welcome_email_task.delay(user.id)
            logger.info('User registered: %s', user.email)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error('Registration failed for email %s: %s', email, str(e))
            raise


class PreferencesViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Auth'],
        summary='Update preferred language',
        description='Updates the authenticated user\'s preferred language. Supported values: en, ru, kk.',
        request=LanguageSerializer,
        responses={
            200: OpenApiResponse(description='Language updated'),
            400: OpenApiResponse(description='Unsupported language value'),
            401: OpenApiResponse(description='Authentication required'),
        },
        examples=[
            OpenApiExample('Request', value={'language': 'ru'}, request_only=True),
            OpenApiExample('Response', value={'detail': 'Language updated successfully.'}, response_only=True),
        ],
    )

    @action(detail=False, methods=['patch'], url_path='language', serializer_class=LanguageSerializer)
    def set_language(self, request) -> Response:
        """Update the authenticated user's preferred language."""
        serializer = LanguageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.preferred_language = serializer.validated_data['language']
        request.user.save(update_fields=['preferred_language'])
        logger.info('User %s changed language to %s', request.user.email, request.user.preferred_language)
        return Response({'detail': _('Language updated successfully.')})

    @extend_schema(
        tags=['Auth'],
        summary='Update user timezone',
        description='Validates and saves an IANA timezone identifier for the authenticated user. Returns 400 for invalid timezones.',
        request=TimezoneSerializer,
        responses={
            200: OpenApiResponse(description='Timezone updated'),
            400: OpenApiResponse(description='Invalid IANA timezone'),
            401: OpenApiResponse(description='Authentication required'),
        },
        examples=[
            OpenApiExample('Request', value={'timezone': 'Asia/Almaty'}, request_only=True),
            OpenApiExample('Response', value={'detail': 'Timezone updated successfully.'}, response_only=True),
        ],
    )

    @action(detail=False, methods=['patch'], url_path='timezone', serializer_class=TimezoneSerializer)
    def set_timezone(self, request) -> Response:
        """Update the authenticated user's preferred timezone."""
        serializer = TimezoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.timezone = serializer.validated_data['timezone']
        request.user.save(update_fields=['timezone'])
        logger.info('User %s changed timezone to %s', request.user.email, request.user.timezone)
        return Response({'detail': _('Timezone updated successfully.')})
