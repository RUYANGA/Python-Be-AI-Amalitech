"""URL configuration for the shortener service."""

from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.shortener.api.views import URLRedirectView, URLResolveView
from config.health import health_check

urlpatterns = [
    # Must precede the ``<str:short_code>/`` catch-all below so a real
    # short code can never collide with this path.
    path("health/", health_check, name="health-check"),
    path("", include("apps.shortener.api.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/v1/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("api/v1/<str:short_code>/", URLResolveView.as_view(), name="url-resolve"),
    path("<str:short_code>/", URLRedirectView.as_view(), name="url-redirect"),
]
