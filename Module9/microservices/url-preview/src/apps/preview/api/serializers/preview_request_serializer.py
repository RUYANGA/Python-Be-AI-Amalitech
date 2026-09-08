from rest_framework import serializers


class PreviewRequestSerializer(serializers.Serializer):
    """Request shape for ``POST /api/v1/internal/preview/``."""

    url = serializers.URLField(max_length=2048)
