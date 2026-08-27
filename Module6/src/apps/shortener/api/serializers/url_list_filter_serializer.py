"""Serializer for keyset-paginated URL listing with dynamic filters."""

from rest_framework import serializers


class URLListFilterSerializer(serializers.Serializer):
    """Query parameters for ``GET /api/v1/urls/mine/`` with keyset pagination.

    Filters combine with AND semantics. Ranges (``created_after``/``created_before``,
    ``min_clicks``/``max_clicks``) are validated so the lower bound never exceeds
    the upper bound.
    """

    search = serializers.CharField(
        required=False,
        allow_blank=False,
        trim_whitespace=True,
        help_text="Case-insensitive search across short_code, title, and original_url.",
    )
    is_active = serializers.BooleanField(
        required=False,
        default=None,
        allow_null=True,
        help_text="Filter by active status (true, false, or omit for both).",
    )
    tag = serializers.CharField(
        required=False,
        allow_blank=False,
        trim_whitespace=True,
        help_text="Filter by tag name (case-insensitive).",
    )
    created_after = serializers.DateTimeField(
        required=False,
        help_text="Only URLs created at or after this datetime (ISO 8601 / RFC 3339).",
    )
    created_before = serializers.DateTimeField(
        required=False,
        help_text="Only URLs created at or before this datetime (ISO 8601 / RFC 3339).",
    )
    min_clicks = serializers.IntegerField(
        required=False,
        min_value=0,
        help_text="Minimum click count (inclusive).",
    )
    max_clicks = serializers.IntegerField(
        required=False,
        min_value=0,
        help_text="Maximum click count (inclusive).",
    )
    ordering = serializers.ChoiceField(
        choices=[
            "created_at",
            "-created_at",
            "click_count",
            "-click_count",
            "title",
            "-title",
            "short_code",
            "-short_code",
        ],
        required=False,
        default="-created_at",
        help_text="Field to sort by; prefix with '-' for descending order.",
    )
    cursor = serializers.CharField(
        required=False,
        help_text="Opaque keyset pagination cursor returned in the previous response's "
        "next_cursor. Do not construct it manually.",
    )
    limit = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
        default=20,
        help_text="Maximum number of results to return per page (1-100).",
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        min_clicks = attrs.get("min_clicks")
        max_clicks = attrs.get("max_clicks")
        if min_clicks is not None and max_clicks is not None and min_clicks > max_clicks:
            raise serializers.ValidationError(
                {"min_clicks": "min_clicks cannot be greater than max_clicks."}
            )

        created_after = attrs.get("created_after")
        created_before = attrs.get("created_before")
        if (
            created_after is not None
            and created_before is not None
            and created_after > created_before
        ):
            raise serializers.ValidationError(
                {"created_after": "created_after cannot be later than created_before."}
            )
        return attrs
