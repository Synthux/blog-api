import logging

from django.conf import settings
from django.db import models

logger = logging.getLogger('notifications')


class Notification(models.Model):
    """
    Created whenever someone comments on a user's post.
    Used by the HTTP polling endpoint to inform the post author.
    """
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    comment = models.ForeignKey(
        'blog.Comment',
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'notification'
        verbose_name_plural = 'notifications'

    def __str__(self) -> str:
        return f'Notification for {self.recipient.email}'
