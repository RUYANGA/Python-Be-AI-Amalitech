from rest_framework import serializers


class URLCreateSerializer(serializers.Serializer):
    """Payload for ``POST /api/urls/``."""

    original_url = serializers.URLField(
        max_length=2048,
        help_text="The long URL to shorten. Must include a scheme, e.g. https://…",
    )
