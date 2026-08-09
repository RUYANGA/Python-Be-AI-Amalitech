"""URL routes for the shortener API endpoints.

Only the create endpoint lives under ``/api/``; the public redirect
route is registered at the project level so it maps to the naked
``/<short_code>/`` path (per the Module 5 spec).
"""

from django.urls import path

from apps.shortener.api.views import URLCreateView

urlpatterns = [
    path("urls/", URLCreateView.as_view(), name="url-create"),
]
