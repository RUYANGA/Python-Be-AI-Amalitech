"""``POST/GET /api/v1/urls/`` — create and list URLs on one route."""

import logging

from rest_framework.permissions import IsAuthenticated

from apps.shortener.api.views.base_view import BaseURLView
from apps.shortener.api.views.create_mixin import URLCreateMixin
from apps.shortener.api.views.list_mixin import URLListMixin

logger = logging.getLogger(__name__)


class URLCollectionView(URLListMixin, URLCreateMixin, BaseURLView):
    """``POST`` creates a URL; ``GET`` lists the caller's URLs (Module 6 spec)."""

    permission_classes = [IsAuthenticated]
