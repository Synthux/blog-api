import logging

import pytz
from django.utils import formats
from django.utils import timezone as tz_utils
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import Category, Comment, Post, Tag

logger = logging.getLogger('blog')

class CategorySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']
    
    def get_name(self, obj: Category) -> str:
        return obj.get_translated_name()

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']

class CommentSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'author', 'body', 'created_at']
        read_only_fields = ['id', 'created_at', 'author']

class PostSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    category = CategorySerializer(read_only=True)
    category_slug = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True,
    )
    tags = TagSerializer(many=True, read_only=True)
    tag_slugs = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Tag.objects.all(),
        source='tags',
        many=True,
        write_only=True,
        required=False,
    )
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'title', 'slug', 'body',
            'category', 'category_slug', 'tags', 'tag_slugs',
            'status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'author', 'created_at', 'updated_at']

    def _format_datetime(self, dt) -> str:
        """Convert dt to user's timezone (or UTC) and format it per active locale."""
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and getattr(user, 'timezone', ''):
            try:
                user_tz = pytz.timezone(user.timezone)
                dt = dt.astimezone(user_tz)
            except pytz.exceptions.UnknownTimeZoneError:
                pass
        return formats.date_format(dt, format='DATETIME_FORMAT')

    def get_created_at(self, obj: Post) -> str:
        return self._format_datetime(obj.created_at)

    def get_updated_at(self, obj: Post) -> str:
        return self._format_datetime(obj.updated_at)
