"""URL routes for the shortener API endpoints.

Concrete, unambiguous paths (``mine``) must be declared before the
``<str:short_code>`` catch-all so they are matched first. The public
resolve route is registered at the project level to map to the naked
``/<short_code>/`` path.

Analytics moved to their own service — see ``analytics/src/apps/analytics``.
"""

from django.urls import path

from apps.shortener.api.views import (
    InternalURLOwnerView,
    URLCreateView,
    URLListView,
    URLShortCodeDetailView,
)

urlpatterns = [
    path("urls/", URLCreateView.as_view(), name="url-create"),
    path("urls/mine/", URLListView.as_view(), name="url-list-mine"),
    path("urls/<str:short_code>/", URLShortCodeDetailView.as_view(), name="url-by-code"),
    path(
        "internal/urls/<str:short_code>/",
        InternalURLOwnerView.as_view(),
        name="internal-url-owner",
    ),
]
