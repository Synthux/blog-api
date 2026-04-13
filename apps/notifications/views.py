import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer

logger = logging.getLogger('notifications')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_count(request) -> Response:
    """Return unread notification count for the authenticated user."""
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return Response({'unread_count': count})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request) -> Response:
    """Return paginated list of notifications for the authenticated user."""
    queryset = Notification.objects.filter(recipient=request.user).select_related(
        'comment', 'comment__post', 'comment__author'
    )
    paginator = PageNumberPagination()
    paginator.page_size = 10
    page = paginator.paginate_queryset(queryset, request)
    serializer = NotificationSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_mark_read(request) -> Response:
    """Mark all unread notifications as read for the authenticated user."""
    updated = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    logger.info('User %s marked %d notifications as read', request.user.email, updated)
    return Response({'marked_read': updated})
