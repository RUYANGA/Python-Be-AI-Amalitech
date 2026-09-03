"""URL routes for the users API endpoints."""

from django.urls import path

from apps.users.api.views import (
    LoginView,
    LogoutView,
    RefreshTokenView,
    RegisterView,
    TokenValidationView,
)

urlpatterns = [
    path("api/v1/auth/register/", RegisterView.as_view(), name="register"),
    path("api/v1/auth/login/", LoginView.as_view(), name="login"),
    path("api/v1/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/v1/auth/token/refresh/", RefreshTokenView.as_view(), name="token_refresh"),
    path(
        "api/v1/auth/internal/token/validate/",
        TokenValidationView.as_view(),
        name="internal-token-validate",
    ),
]
