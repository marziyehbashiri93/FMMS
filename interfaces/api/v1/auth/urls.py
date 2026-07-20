"""Authentication URL routes."""

from django.urls import path

from interfaces.api.v1.auth.views import (
    CurrentUserView,
    FMMSJWTTokenObtainPairView,
    FMMSJWTTokenRefreshView,
)

urlpatterns = [
    path("token/", FMMSJWTTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", FMMSJWTTokenRefreshView.as_view(), name="token_refresh"),
    path("me/", CurrentUserView.as_view(), name="current_user"),
]
