import json
import redis
from django.conf import settings
from django.core.management.base import BaseCommand
from apps.blog.constants import REDIS_COMMENTS_CHANNEL

class Command(BaseCommand):
    help = 'Listen for new comments via Redis Pub/Sub'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f'Subscribing to channel: {REDIS_COMMENTS_CHANNEL}'))
        
        r = redis.StrictRedis.from_url(settings.REDIS_URL)
        pubsub = r.pubsub()
        pubsub.subscribe(REDIS_COMMENTS_CHANNEL)

        self.stdout.write('Listening for messages...')

        for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'].decode('utf-8'))
                self.stdout.write(self.style.SUCCESS(f"New Comment Received:\n"
                                                     f"Post: {data['post_title']}\n"
                                                     f"User: {data['author']}\n"
                                                     f"Content: {data['body']}\n"
                                                     f"-------------------------"))

