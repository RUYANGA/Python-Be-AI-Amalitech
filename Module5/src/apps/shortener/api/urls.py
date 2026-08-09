"""URL routes for the shortener API endpoints.

Only the owner-scoped endpoints live under ``/api/``; the public resolve
route is registered at the project level so it maps to the naked
``/<short_code>/`` path (per the Module 5 spec).
"""

from django.urls import path

from apps.shortener.api.views import URLCreateView, URLDetailView, URLListView

urlpatterns = [
    path("urls/", URLCreateView.as_view(), name="url-create"),
    path("urls/mine/", URLListView.as_view(), name="url-list-mine"),
    path("urls/<int:pk>/", URLDetailView.as_view(), name="url-detail"),
]
