from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PostViewSet, StatsView, post_stream

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')

urlpatterns = [
    path('posts/stream/', post_stream, name='post-stream'),
    path('', include(router.urls)),
    path('stats/', StatsView.as_view(), name='stats'),
]

