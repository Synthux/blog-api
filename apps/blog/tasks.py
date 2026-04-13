import logging

from celery import shared_task

logger = logging.getLogger('blog')


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def invalidate_posts_cache() -> None:
    """
    Invalidate the posts list cache for all supported languages.
    Retries are important because a failed cache invalidation during a
    high-write period leaves stale data visible to readers until TTL expires.
    Retrying ensures the cache eventually reflects the latest state even if
    Redis is momentarily unavailable.
    """
    from django.core.cache import cache

    from apps.core.middleware import SUPPORTED_LANGUAGES

    CACHE_KEY_PREFIX = 'posts_list'  # must match the key used in PostViewSet.list()
    for lang in SUPPORTED_LANGUAGES:
        cache.delete(f'{CACHE_KEY_PREFIX}_{lang}')
    logger.info('Posts cache invalidated (all languages)')


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def publish_scheduled_posts() -> None:
    """
    Find posts with status=scheduled and publish_at <= now().
    Publishes each one and fires its SSE event.
    Runs every minute via Celery Beat.
    """
    import json

    import redis
    from django.conf import settings
    from django.utils import timezone

    from apps.blog.constants import PostStatus
    from apps.blog.models import Post

    now = timezone.now()
    due_posts = Post.objects.filter(
        status=PostStatus.SCHEDULED, publish_at__lte=now
    ).select_related('author')

    if not due_posts.exists():
        return

    redis_client = redis.from_url(settings.BLOG_REDIS_URL)

    for post in due_posts:
        post.status = PostStatus.PUBLISHED
        post.save(update_fields=['status'])

        # Fire SSE event for each newly published post
        event = {
            'post_id': post.id,
            'title': post.title,
            'slug': post.slug,
            'author': {'id': post.author.id, 'email': post.author.email},
            'published_at': post.updated_at.isoformat(),
        }
        redis_client.publish('post_published', json.dumps(event))
        logger.info('Scheduled post published: %s', post.slug)

    logger.info('publish_scheduled_posts: published %d post(s)', due_posts.count())


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def generate_daily_stats() -> None:
    """
    Log counts of new posts, comments, and users from the last 24 hours.
    Runs daily at 00:00 via Celery Beat. Retries matter because a DB
    timeout would silently skip the stats log for that day with no record.
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.blog.models import Comment, Post
    from apps.users.models import User

    since = timezone.now() - timedelta(hours=24)
    new_posts = Post.objects.filter(created_at__gte=since).count()
    new_comments = Comment.objects.filter(created_at__gte=since).count()
    new_users = User.objects.filter(date_joined__gte=since).count()

    logger.info(
        'Daily stats — new posts: %d | new comments: %d | new users: %d',
        new_posts,
        new_comments,
        new_users,
    )
