from django.urls import path

from .views import notification_count, notification_list, notification_mark_read

urlpatterns = [
    path('notifications/', notification_list, name='notification-list'),
    path('notifications/count/', notification_count, name='notification-count'),
    path('notifications/read/', notification_mark_read, name='notification-read'),
]
