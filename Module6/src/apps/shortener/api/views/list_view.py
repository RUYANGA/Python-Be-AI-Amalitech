"""``GET /api/urls/mine/`` — list the caller's shortened URLs.

Supports keyset (cursor-based) pagination and dynamic filtering.

Keyset pagination advantages over OFFSET:
- O(1) page navigation — the database uses the primary key index
  directly instead of scanning ``OFFSET N`` rows.
- Consistent results even when rows are inserted/deleted between pages.
- Naturally stable ordering — no duplicate or missing rows.
"""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated

from apps.shortener.api.views.base_view import BaseURLView
from apps.shortener.api.views.list_mixin import URLListMixin


class URLListView(URLListMixin, BaseURLView):
    """``GET /api/urls/mine/`` — list the caller's shortened URLs."""

    permission_classes = [IsAuthenticated]
