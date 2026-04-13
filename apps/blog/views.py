import asyncio
import json
import logging

import httpx
import redis
import redis.asyncio as aioredis
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.http import StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.utils.translation import get_language
from django.views import View
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .constants import (
    REDIS_COMMENTS_CHANNEL,
    REDIS_POSTS_CACHE_KEY,
    REDIS_POSTS_CACHE_TTL,
    PostStatus,
)
from .models import Comment, Post
from .serializers import CommentSerializer, PostSerializer
from .permissions import IsOwnerOrReadOnly
from apps.blog.tasks import invalidate_posts_cache
from apps.notifications.tasks import process_new_comment

logger = logging.getLogger('blog')
redis_client = redis.StrictRedis.from_url(settings.REDIS_URL)


def _get_cache_key(request=None) -> str:
    """Cache key includes language so each language gets its own cached response."""
    lang = get_language() or 'en'
    return f'{REDIS_POSTS_CACHE_KEY}_{lang}'


def _invalidate_all_caches() -> None:
    """Invalidate cache for all supported languages when any post is written."""
    from apps.core.middleware import SUPPORTED_LANGUAGES
    for lang in SUPPORTED_LANGUAGES:
        cache.delete(f'{REDIS_POSTS_CACHE_KEY}_{lang}')
    logger.info('All language caches invalidated')


def _publish_post_sse_event(post) -> None:
    """Publish a post-published event to Redis for all connected SSE clients."""
    client = redis.from_url(settings.BLOG_REDIS_URL)
    event = {
        'post_id': post.id,
        'title': post.title,
        'slug': post.slug,
        'author': {'id': post.author.id, 'email': post.author.email},
        'published_at': post.updated_at.isoformat(),
    }
    client.publish('post_published', json.dumps(event))
    logger.info('SSE event published for post: %s', post.slug)


async def post_stream(request):
    """SSE endpoint — streams newly published posts to all connected clients."""
    
    async def event_generator():
        client = aioredis.from_url(settings.BLOG_REDIS_URL, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe('post_published')
        yield 'data: {"type": "connected"}\n\n'
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    yield f'data: {message["data"]}\n\n'
        finally:
            await pubsub.close()
            await client.aclose()

    response = StreamingHttpResponse(event_generator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


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

    def perform_create(self, serializer) -> None:
        instance = serializer.save(author=self.request.user)
        # Dispatch cache invalidation as async Celery task
        invalidate_posts_cache.delay()
        # Fire SSE event if the post is immediately published
        if instance.status == PostStatus.PUBLISHED:
            _publish_post_sse_event(instance)

    def perform_update(self, serializer) -> None:
        old_status = serializer.instance.status
        instance = serializer.save()
        invalidate_posts_cache.delay()
        # Fire SSE event only when transitioning to published
        if old_status != PostStatus.PUBLISHED and instance.status == PostStatus.PUBLISHED:
            _publish_post_sse_event(instance)

    def perform_destroy(self, instance) -> None:
        instance.delete()
        invalidate_posts_cache.delay()
    
    @extend_schema(
        summary='Create a post',
        description='Creates a new post. Requires authentication. Rate-limited to 20/minute per user. Invalidates the Redis cache for all languages.',
        responses={
            201: PostSerializer,
            400: OpenApiResponse(description='Validation errors'),
            401: OpenApiResponse(description='Authentication required'),
            429: OpenApiResponse(description='Too many requests'),
        },
    )

    # Rate Limit: 20 requests per minute per user for creating posts
    @method_decorator(ratelimit(key='user', rate='20/m', method='POST', block=True))
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @extend_schema(
        summary='List published posts',
        description=(
            'Returns a paginated list of published posts. Responses are cached in Redis for 60 seconds, '
            'independently per language. Cache is invalidated when any post is created or updated. '
            'No authentication required.'
        ),
        parameters=[OpenApiParameter('lang', str, description='Override language: en, ru, kk')],
        responses={200: PostSerializer(many=True), 429: OpenApiResponse(description='Too many requests')},
    )

    def list(self, request, *args, **kwargs):
        cache_key = _get_cache_key(request)
        if not request.query_params:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.debug('Serving posts list from cache (lang=%s)', get_language())
                return Response(cached_data)

        response = super().list(request, *args, **kwargs)

        if not request.query_params:
            cache.set(cache_key, response.data, REDIS_POSTS_CACHE_TTL)
            logger.debug('Cached posts list for lang=%s', get_language())

        return response
    
    @extend_schema(summary='Get a single post', responses={200: PostSerializer, 404: OpenApiResponse(description='Not found')})
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(summary='Update own post', responses={200: PostSerializer, 403: OpenApiResponse(description='Not the author'), 404: OpenApiResponse(description='Not found')})
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(summary='Delete own post', responses={204: None, 403: OpenApiResponse(description='Not the author')})
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        methods=['get'],
        tags=['Comments'],
        summary='List comments on a post',
        responses={200: CommentSerializer(many=True)},
    )
    @extend_schema(
        methods=['post'],
        tags=['Comments'],
        summary='Add a comment to a post',
        description='Requires authentication. Publishes a JSON event to the Redis `comments` channel: {post_slug, author_id, body}.',
        responses={201: CommentSerializer, 401: OpenApiResponse(description='Authentication required')},
    )

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
                    'post_slug': post.slug,
                    'author_id': request.user.id,
                    'event': 'new_comment',
                    'post_title': post.title,
                    'author': request.user.email,
                    'body': serializer.data['body']
                }
                # Dispatch all comment side-effects (notification + WebSocket push) to Celery
                process_new_comment.delay(message.id)
                logger.info("Published new comment event to Redis channel: %s", REDIS_COMMENTS_CHANNEL)
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StatsView(View):
    """
    Async view: two external HTTP calls (exchange rates + current time) run
    concurrently via asyncio.gather. If written synchronously, the total response
    time would be the sum of both calls; async makes it the max of the two.
    """

    @extend_schema(
        tags=['Stats'],
        summary='Blog statistics with live exchange rates and Almaty time',
        description=(
            'Fetches blog counts from the database, then concurrently requests '
            'USD exchange rates from open.er-api.com and current Almaty time from '
            'timeapi.io using asyncio.gather. No authentication required.'
        ),
        responses={200: OpenApiResponse(description='Stats object')},
    )
    async def get(self, request) -> JsonResponse:
        from apps.users.models import User

        total_posts = await sync_to_async(
            Post.objects.filter(status=PostStatus.PUBLISHED).count
        )()
        total_comments = await sync_to_async(Comment.objects.count)()
        total_users = await sync_to_async(User.objects.count)()

        exchange_rates, current_time = await asyncio.gather(
            self._fetch_exchange_rates(),
            self._fetch_current_time(),
        )

        return JsonResponse({
            'blog': {
                'total_posts': total_posts,
                'total_comments': total_comments,
                'total_users': total_users,
            },
            'exchange_rates': exchange_rates,
            'current_time': current_time,
        })

    async def _fetch_exchange_rates(self) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get('https://open.er-api.com/v6/latest/USD')
            rates = resp.json().get('rates', {})
            return {key: rates.get(key) for key in ('KZT', 'RUB', 'EUR')}

    async def _fetch_current_time(self) -> str:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                'https://timeapi.io/api/time/current/zone',
                params={'timeZone': 'Asia/Almaty'},
            )
            return resp.json().get('dateTime', '')
