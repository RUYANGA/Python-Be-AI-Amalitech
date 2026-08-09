"""HTTP views for the shortener API endpoints."""

from apps.shortener.api.views.create_view import URLCreateView
from apps.shortener.api.views.redirect_view import URLRedirectView

__all__ = ["URLCreateView", "URLRedirectView"]
