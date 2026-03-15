from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PostViewSet, StatsView

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', StatsView.as_view(), name='stats'),
]

