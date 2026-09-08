"""URL routes for the url-preview API endpoints."""

from django.urls import path

from apps.preview.api.views import PreviewFetchView

urlpatterns = [
    path(
        "api/v1/internal/preview/",
        PreviewFetchView.as_view(),
        name="internal-preview-fetch",
    ),
]
