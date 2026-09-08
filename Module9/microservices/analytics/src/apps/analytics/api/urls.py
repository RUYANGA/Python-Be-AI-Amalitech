"""URL routes for the analytics API endpoints."""

from django.urls import path

from apps.analytics.api.views import ClickIngestView, URLAnalyticsByCodeView

urlpatterns = [
    path(
        "api/v1/analytics/<str:short_code>/",
        URLAnalyticsByCodeView.as_view(),
        name="url-analytics-by-code",
    ),
    path("api/v1/internal/clicks/", ClickIngestView.as_view(), name="internal-click-ingest"),
]
