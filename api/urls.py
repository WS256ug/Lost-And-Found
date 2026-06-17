from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    ClaimViewSet,
    ConversationViewSet,
    CurrentUserAPIView,
    ItemViewSet,
    NotificationViewSet,
    RegisterAPIView,
)

router = DefaultRouter()
router.register("items", ItemViewSet, basename="api-item")
router.register("conversations", ConversationViewSet, basename="api-conversation")
router.register("claims", ClaimViewSet, basename="api-claim")
router.register("notifications", NotificationViewSet, basename="api-notification")

urlpatterns = [
    path("auth/register/", RegisterAPIView.as_view(), name="api-register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="api-login"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", CurrentUserAPIView.as_view(), name="api-me"),
    path("", include(router.urls)),
]
