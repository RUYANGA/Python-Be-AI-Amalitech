"""URL routes for the shortener API endpoints.

Concrete, unambiguous paths (``top``, ``mine``) must be declared before
the ``<str:short_code>`` catch-all so they are matched first. The public
resolve route is registered at the project level to map to the naked
``/<short_code>/`` path (per the Module 5 spec).
"""

from django.urls import path

from apps.shortener.api.views import (
    TopURLsView,
    URLAnalyticsByCodeView,
    URLAnalyticsView,
    URLCollectionView,
    URLListView,
    URLShortCodeDetailView,
    URLTimeSeriesView,
)

urlpatterns = [
    path("urls/", URLCollectionView.as_view(), name="url-collection"),
    path("urls/top/", TopURLsView.as_view(), name="url-top"),
    path("urls/mine/", URLListView.as_view(), name="url-list-mine"),
    path(
        "urls/<int:pk>/analytics/timeseries/",
        URLTimeSeriesView.as_view(),
        name="url-analytics-timeseries",
    ),
    path(
        "urls/<int:pk>/analytics/",
        URLAnalyticsView.as_view(),
        name="url-analytics",
    ),
    path("urls/<str:short_code>/", URLShortCodeDetailView.as_view(), name="url-by-code"),
    path(
        "analytics/<str:short_code>/",
        URLAnalyticsByCodeView.as_view(),
        name="url-analytics-by-code",
    ),
]
