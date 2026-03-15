import asyncio
import json
import logging

import redis.asyncio as aioredis
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.blog.constants import REDIS_COMMENTS_CHANNEL

logger = logging.getLogger('blog')


class Command(BaseCommand):
    """
    Async is used here because Redis subscribe/listen is a long-running I/O operation.
    If written synchronously, it blocks the entire thread waiting for each message.
    With asyncio, the coroutine yields control while waiting, keeping the event loop free.
    """

    help = 'Listen for new comment events from the Redis comments channel (async)'

    def handle(self, *args, **options) -> None:
        asyncio.run(self._listen())

    async def _listen(self) -> None:
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(REDIS_COMMENTS_CHANNEL)
        self.stdout.write(
            self.style.SUCCESS(f'Subscribed to Redis channel: {REDIS_COMMENTS_CHANNEL}')
        )

        async for message in pubsub.listen():
            if message['type'] != 'message':
                continue
            try:
                data = json.loads(message['data'])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n[New Comment Event]\n"
                        f"  Post slug : {data.get('post_slug')}\n"
                        f"  Author ID : {data.get('author_id')}\n"
                        f"  Body      : {data.get('body')}\n"
                    )
                )
                logger.info('Received comment event on post %s', data.get('post_slug'))
            except (json.JSONDecodeError, KeyError) as exc:
                logger.error('Malformed comment event: %s', exc)
