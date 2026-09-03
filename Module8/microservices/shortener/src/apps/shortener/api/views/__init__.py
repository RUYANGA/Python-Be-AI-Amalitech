"""HTTP views for the shortener API endpoints."""

from apps.shortener.api.views.create_view import URLCreateView
from apps.shortener.api.views.list_view import URLListView
from apps.shortener.api.views.ownership_view import URLOwnershipView
from apps.shortener.api.views.redirect_view import URLRedirectView
from apps.shortener.api.views.resolve_view import URLResolveView
from apps.shortener.api.views.short_code_view import URLShortCodeDetailView

__all__ = [
    "URLCreateView",
    "URLListView",
    "URLOwnershipView",
    "URLRedirectView",
    "URLResolveView",
    "URLShortCodeDetailView",
]
