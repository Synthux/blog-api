from django.db import models


class PostStatus(models.TextChoices):
    """Status choices for blog posts."""
    DRAFT = 'draft', 'Draft'
    PUBLISHED = 'published', 'Published'


# Redis constants
REDIS_POSTS_CACHE_KEY = 'posts_list'
REDIS_POSTS_CACHE_TTL = 60  # seconds
REDIS_COMMENTS_CHANNEL = 'comments'
