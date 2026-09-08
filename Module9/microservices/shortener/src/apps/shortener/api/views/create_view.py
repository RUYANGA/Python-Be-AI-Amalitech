"""``POST /api/v1/urls/`` — create a shortened URL, owned by the caller."""

from rest_framework.permissions import IsAuthenticated

from apps.shortener.api.views.base_view import BaseURLView
from apps.shortener.api.views.create_mixin import URLCreateMixin


class URLCreateView(URLCreateMixin, BaseURLView):
    """``POST /api/urls/`` — create a shortened URL, owned by the caller."""

    permission_classes = [IsAuthenticated]
