"""Serializers for the shortener API endpoints."""

from apps.shortener.api.serializers.url_create_serializer import URLCreateSerializer
from apps.shortener.api.serializers.url_response_serializer import URLResponseSerializer

__all__ = ["URLCreateSerializer", "URLResponseSerializer"]
