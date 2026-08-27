"""HTTP views for the shortener API endpoints."""

from apps.shortener.api.views.analytics_by_code_view import URLAnalyticsByCodeView
from apps.shortener.api.views.create_view import URLCreateView
from apps.shortener.api.views.list_view import URLListView
from apps.shortener.api.views.resolve_view import URLResolveView
from apps.shortener.api.views.short_code_view import URLShortCodeDetailView

__all__ = [
    "URLAnalyticsByCodeView",
    "URLCreateView",
    "URLListView",
    "URLResolveView",
    "URLShortCodeDetailView",
]
