from rest_framework.permissions import IsAuthenticated

from apps.shortener.api.views.base_view import BaseURLView
from apps.shortener.api.views.delete_view import URLDeleteMixin
from apps.shortener.api.views.update_view import URLUpdateMixin


class URLDetailView(URLUpdateMixin, URLDeleteMixin, BaseURLView):
    """``PATCH``/``DELETE`` ``/api/urls/<id>/`` — update or delete a URL you own.

    One Django route handles both verbs, so the two behaviors are split
    into their own mixins (update_view.py, delete_view.py) and combined
    here rather than duplicated across two routes.
    """

    permission_classes = [IsAuthenticated]
