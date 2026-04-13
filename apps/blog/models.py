import logging

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .constants import PostStatus

logger = logging.getLogger('blog')


class Category(models.Model):
    """Category model for organizing blog posts."""
    
    slug = models.SlugField(unique=True, max_length=100, verbose_name=_('slug'))
    name_en = models.CharField(max_length=100, verbose_name=_('name (English)'))
    name_ru = models.CharField(max_length=100, blank=True, verbose_name=_('name (Russian)'))
    name_kk = models.CharField(max_length=100, blank=True, verbose_name=_('name (Kazakh)'))
    
    class Meta:
        verbose_name = _('category')
        verbose_name_plural = _('categories')
        ordering = ['name_en']

    def __str__(self) -> str:
        return self.get_translated_name()

    def get_translated_name(self) -> str:
        """Return category name in the currently active language."""
        from django.utils.translation import get_language
        lang = get_language() or 'en'
        name = getattr(self, f'name_{lang}', '') or ''
        return name if name else self.name_en
    
    def save(self, *args, **kwargs) -> None:
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            self.slug = slugify(self.name_en)
        super().save(*args, **kwargs)


class Tag(models.Model):
    """Tag model for labeling blog posts."""
    
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True, max_length=50)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self) -> str:
        return self.name
    
    def save(self, *args, **kwargs) -> None:
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Post(models.Model):
    """Blog post model."""
    
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    body = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    status = models.CharField(max_length=10, choices=PostStatus.choices, default=PostStatus.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    publish_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('publish at'),
        help_text=_('Set together with status=scheduled to auto-publish at this time.'),
        )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self) -> str:
        return self.title
    
    def save(self, *args, **kwargs) -> None:
        """Auto-generate slug from title if not provided."""
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class Comment(models.Model):
    """Comment model for blog posts."""
    
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self) -> str:
        return f'Comment by {self.author.email} on {self.post.title}'
