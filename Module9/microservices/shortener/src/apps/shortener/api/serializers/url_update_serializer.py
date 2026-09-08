from rest_framework import serializers

from apps.shortener.api.serializers.url_create_serializer import TagsField


class URLUpdateSerializer(serializers.Serializer):
    """Payload for ``PATCH /api/v1/urls/{short_code}/``.

    All fields are optional for partial updates — only the fields provided in
    the request body are modified on the target URL.
    """

    original_url = serializers.URLField(
        max_length=2048,
        required=False,
        help_text="The long URL to shorten. Must include a scheme, e.g. https://...",
    )
    title = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Optional human-readable title for the short URL.",
    )
    tags = TagsField(
        required=False,
        help_text='List of tag names OR a comma-separated string, e.g. "marketing, social".',
    )
    expires_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Optional expiry datetime. The URL becomes inactive after this time.",
    )
