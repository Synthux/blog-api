from django.db import models
from django.utils.translation import gettext_lazy as _


class PostStatus(models.TextChoices):
    """Status choices for blog posts."""
    DRAFT = 'draft', _('Draft')
    PUBLISHED = 'published', _('Published')
    SCHEDULED = 'scheduled', _('Scheduled')


# Redis constants
REDIS_POSTS_CACHE_KEY = 'posts_list'
REDIS_POSTS_CACHE_TTL = 60  # seconds
REDIS_COMMENTS_CHANNEL = 'comments'
