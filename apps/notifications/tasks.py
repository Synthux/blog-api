import logging

from celery import shared_task

from apps.notifications.models import Notification

logger = logging.getLogger('notifications')


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def process_new_comment(comment_id: int) -> None:
    """
    Handle all side-effects of a new comment in one atomic Celery task:
      1. Create a Notification record for the post author.
      2. Push the comment to the WebSocket channel group.
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    from apps.blog.models import Comment

    try:
        comment = Comment.objects.select_related(
            'post', 'post__author', 'author'
        ).get(id=comment_id)
    except Comment.DoesNotExist:
        logger.error('process_new_comment: Comment %d not found', comment_id)
        return
    
    post = comment.post

    # 1. Create notification only if the commenter is not the post author
    if comment.author_id != post.author_id:
        Notification.objects.create(recipient=post.author, comment=comment)
        logger.info(
            'Notification created for %s (comment on post %s)',
            post.author.email, post.slug,
        )

    # 2. Publish to WebSocket group
    channel_layer = get_channel_layer()
    group_name = f'post_comments_{post.slug}'
    message = {
        'comment_id': comment.id,
        'author': {'id': comment.author.id, 'email': comment.author.email},
        'body': comment.body,
        'created_at': comment.created_at.isoformat(),
    }
    async_to_sync(channel_layer.group_send)(
        group_name,
        {'type': 'new_comment', 'data': message},
    )
    logger.info('WebSocket push sent for post %s comment %d', post.slug, comment_id)


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def clear_expired_notifications() -> None:
    """Delete notifications older than 30 days"""
    from datetime import timedelta

    from django.utils import timezone

    cutoff = timezone.now() - timedelta(days=30)
    deleted, _ = Notification.objects.filter(created_at__lt=cutoff).delete()
    logger.info('Cleared %d expired notifications older than 30 days', deleted)
