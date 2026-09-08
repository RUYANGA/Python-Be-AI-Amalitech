from rest_framework import serializers


class PreviewResponseSerializer(serializers.Serializer):
    """Response shape for a successful preview fetch."""

    url = serializers.URLField(max_length=2048)
    title = serializers.CharField(default="")
    description = serializers.CharField(default="")
    favicon_url = serializers.URLField(max_length=2048, default="")
