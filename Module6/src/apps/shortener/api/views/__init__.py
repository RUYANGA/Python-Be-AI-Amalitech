"""HTTP views for the shortener API endpoints."""

from apps.shortener.api.views.analytics_view import (
    TopURLsView,
    URLAnalyticsView,
    URLTimeSeriesView,
)
from apps.shortener.api.views.create_view import URLCreateView
from apps.shortener.api.views.detail_view import URLDetailView
from apps.shortener.api.views.list_view import URLListView
from apps.shortener.api.views.resolve_view import URLResolveView

__all__ = [
    "TopURLsView",
    "URLAnalyticsView",
    "URLCreateView",
    "URLDetailView",
    "URLListView",
    "URLResolveView",
    "URLTimeSeriesView",
]
