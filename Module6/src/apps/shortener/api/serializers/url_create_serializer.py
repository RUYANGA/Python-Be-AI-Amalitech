from rest_framework import serializers


class TagsField(serializers.Field):
    """Accepts tags as a JSON list OR a comma-separated string.

    ``["marketing", "social"]`` and ``"marketing, social"`` both produce
    the list ``["marketing", "social"]``.
    """

    def to_internal_value(self, data):
        if isinstance(data, str):
            return [tag.strip() for tag in data.split(",") if tag.strip()]
        if isinstance(data, (list | tuple)):
            return [str(tag).strip() for tag in data if str(tag).strip()]
        raise serializers.ValidationError("Tags must be a list or a comma-separated string.")

    def to_representation(self, value):
        return value


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
    tags = TagsField(
        required=False,
        default=[],
        help_text='List of tag names OR a comma-separated string, e.g. "marketing, social".',
    )
    expires_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Optional expiry datetime. The URL becomes inactive after this time.",
    )
