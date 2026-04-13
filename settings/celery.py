import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.env.local')

app = Celery('settings')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

# Periodic (Beat) tasks
app.conf.beat_schedule = {
    # Every 1 minute: auto-publish scheduled posts
    'publish_scheduled_posts': {
        'task': 'apps.blog.tasks.publish_scheduled_posts',
        'schedule': 60.0,
    },
    # Daily at 03:00 UTC: delete old notifications
    'clear_expired_notifications': {
        'task': 'apps.notifications.tasks.clear_expired_notifications',
        'schedule': crontab(hour=3, minute=0),
    },
    # Daily at 00:00 UTC: log content statistics
    'generate_daily_stats': {
        'task': 'apps.blog.tasks.generate_daily_stats',
        'schedule': crontab(hour=0, minute=0),
    },
}
