import logging
from rest_framework import serializers
from .models import Category, Tag, Post, Comment

logger = logging.getLogger('blog')

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

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
    category = serializers.SlugRelatedField(
        slug_field='slug', 
        queryset=Category.objects.all(),
        required=False,
        allow_null=True
    )
    tags = serializers.SlugRelatedField(
        slug_field='slug', 
        queryset=Tag.objects.all(), 
        many=True,
        required=False
    )
    
    class Meta:
        model = Post
        fields = [
            'id', 'author', 'title', 'slug', 'body', 
            'category', 'tags', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at', 'author']

    def create(self, validated_data):
        # Extract tags to handle ManyToMany relationship
        tags = validated_data.pop('tags', [])
        post = Post.objects.create(**validated_data)
        post.tags.set(tags)
        logger.info('Post created: %s by %s', post.title, post.author.email)
        return post

