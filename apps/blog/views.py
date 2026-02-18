import json
import logging
import redis
from django.conf import settings
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import Post, Comment, Category, Tag
from .serializers import PostSerializer, CommentSerializer
from .permissions import IsOwnerOrReadOnly
from .constants import REDIS_POSTS_CACHE_KEY, REDIS_POSTS_CACHE_TTL, REDIS_COMMENTS_CHANNEL, PostStatus

logger = logging.getLogger('blog')
redis_client = redis.StrictRedis.from_url(settings.REDIS_URL)

class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing blog posts.
    """
    queryset = Post.objects.filter(status=PostStatus.PUBLISHED)
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    lookup_field = 'slug'
    pagination_class = PageNumberPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'body']

    def get_queryset(self):
        # Allow authors to see their own draft posts
        user = self.request.user
        if user.is_authenticated:
            return Post.objects.filter(status=PostStatus.PUBLISHED) | Post.objects.filter(author=user)
        return Post.objects.filter(status=PostStatus.PUBLISHED)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
        # Invalidate cache on create
        cache.delete(REDIS_POSTS_CACHE_KEY)
        logger.info("Cache invalidated due to new post creation")

    def perform_update(self, serializer):
        serializer.save()
        # Invalidate cache on update
        cache.delete(REDIS_POSTS_CACHE_KEY)
        logger.info("Cache invalidated due to post update")

    def perform_destroy(self, instance):
        instance.delete()
        # Invalidate cache on delete
        cache.delete(REDIS_POSTS_CACHE_KEY)
        logger.info("Cache invalidated due to post deletion")

    # Rate Limit: 20 requests per minute per user for creating posts
    @method_decorator(ratelimit(key='user', rate='20/m', method='POST', block=True))
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """
        List posts with Redis caching (60 seconds).
        """
        # We only cache the default list view (no search params) for simplicity
        if not request.query_params:
            cached_data = cache.get(REDIS_POSTS_CACHE_KEY)
            if cached_data:
                logger.debug("Serving posts list from Redis cache")
                return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        
        if not request.query_params:
            cache.set(REDIS_POSTS_CACHE_KEY, response.data, REDIS_POSTS_CACHE_TTL)
            logger.debug("Cached posts list to Redis")
            
        return response

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def comments(self, request, slug=None):
        """
        Action to list or create comments for a specific post.
        """
        post = self.get_object()

        if request.method == 'GET':
            comments = post.comments.all()
            page = self.paginate_queryset(comments)
            if page is not None:
                serializer = CommentSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            serializer = CommentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(author=request.user, post=post)
                
                # Pub/Sub: Publish event to Redis
                message = {
                    'event': 'new_comment',
                    'post_title': post.title,
                    'author': request.user.email,
                    'body': serializer.data['body']
                }
                redis_client.publish(REDIS_COMMENTS_CHANNEL, json.dumps(message))
                logger.info("Published new comment event to Redis channel: %s", REDIS_COMMENTS_CHANNEL)
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

