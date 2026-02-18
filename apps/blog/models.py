import logging

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from .constants import PostStatus

logger = logging.getLogger('blog')


class Category(models.Model):
    """Category model for organizing blog posts."""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, max_length=100)
    
    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']
    
    def __str__(self) -> str:
        return self.name
    
    def save(self, *args, **kwargs) -> None:
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
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
