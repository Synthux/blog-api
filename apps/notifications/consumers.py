import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger('notifications')


class CommentConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time comment feed on a post.
    Authentication: JWT token passed as query param ?token=<access_token>
    Rejects with 4001 if unauthenticated, 4004 if post slug not found.
    """

    async def connect(self) -> None:
        self.post_slug = self.scope['url_route']['kwargs']['slug']

        # 1. Authenticate via JWT query param
        user = await self._authenticate()
        if user is None:
            await self.close(code=4001)
            return
        
        # 2. Verify the post exists
        if not await self._post_exists(self.post_slug):
            await self.close(code=4004)
            return
        
        self.group_name = f'post_comments_{self.post_slug}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info('WebSocket connected: post=%s user=%s', self.post_slug, user.email)

    async def disconnect(self, close_code: int) -> None:
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data: str = '', bytes_data: bytes = None) -> None:
        # Clients only receive - they do not send data on this channel
        pass

    async def new_comment(self, event: dict) -> None:
        """Called by Celery task via channel_layer.group_send().""" 
        await self.send(text_data=json.dumps(event['data']))

    async def _authenticate(self):
        query_string = self.scope.get('query_string', b'').decode()
        params = dict(p.split('=', 1) for p in query_string.split('&') if '=' in p)
        token_key = params.get('token')
        if not token_key:
            return None
        try:
            token = AccessToken(token_key)
            return await self._get_user(token['user_id'])
        except (InvalidToken, TokenError, Exception) as exc:
            logger.warning('WebSocket auth failed: %s', exc)
            return None
        
    @database_sync_to_async
    def _get_user(self, user_id: int):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return None
        
    @database_sync_to_async
    def _post_exists(self, slug: str) -> bool:
        from apps.blog.models import Post
        return Post.objects.filter(slug=slug).exists()
    