from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    comment_body = serializers.CharField(source='comment.body', read_only=True)
    post_slug = serializers.CharField(source='comment.post.slug', read_only=True)
    commenter_email = serializers.EmailField(source='comment.author.email', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'comment_body', 'post_slug', 'commenter_email', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']
