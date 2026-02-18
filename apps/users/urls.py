from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from .views import AuthViewSet

router = DefaultRouter()
router.register(r'register', AuthViewSet, basename='register')

# Rate-limited token views
token_view = method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True), name='dispatch')(TokenObtainPairView)
refresh_view = TokenRefreshView

urlpatterns = [
    path('token/', token_view.as_view(), name='token_obtain_pair'),
    path('token/refresh/', refresh_view.as_view(), name='token_refresh'),
] + router.urls
