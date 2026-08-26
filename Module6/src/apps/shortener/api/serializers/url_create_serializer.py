from rest_framework import serializers


class URLCreateSerializer(serializers.Serializer):
    """Payload for ``POST /api/urls/``."""

    original_url = serializers.URLField(
        max_length=2048,
        help_text="The long URL to shorten. Must include a scheme, e.g. https://...",
    )
    title = serializers.CharField(
        max_length=255,
        required=False,
        default="",
        help_text="Optional human-readable title for the short URL.",
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=64),
        required=False,
        default=[],
        help_text="List of tag names to assign to this URL.",
    )
    expires_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Optional expiry datetime. The URL becomes inactive after this time.",
    )
