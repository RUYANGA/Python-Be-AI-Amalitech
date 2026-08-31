"""URL routes for the analytics API endpoints."""

from django.urls import path

from apps.analytics.api.views import URLAnalyticsByCodeView

urlpatterns = [
    path(
        "analytics/<str:short_code>/",
        URLAnalyticsByCodeView.as_view(),
        name="url-analytics-by-code",
    ),
]
