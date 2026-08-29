"""URL routes for the shortener API endpoints.

Concrete, unambiguous paths (``mine``) must be declared before the
``<str:short_code>`` catch-all so they are matched first. The public
resolve route is registered at the project level to map to the naked
``/<short_code>/`` path (per the Module 5 spec).

Analytics are exposed via the single Premium-only endpoint
``GET /api/v1/analytics/{short_code}/`` (time-series + geo).
"""

from django.urls import path

from apps.shortener.api.views import (
    URLAnalyticsByCodeView,
    URLCreateView,
    URLListView,
    URLShortCodeDetailView,
)

urlpatterns = [
    path("urls/", URLCreateView.as_view(), name="url-create"),
    path("urls/mine/", URLListView.as_view(), name="url-list-mine"),
    path("urls/<str:short_code>/", URLShortCodeDetailView.as_view(), name="url-by-code"),
    path(
        "analytics/<str:short_code>/",
        URLAnalyticsByCodeView.as_view(),
        name="url-analytics-by-code",
    ),
]
