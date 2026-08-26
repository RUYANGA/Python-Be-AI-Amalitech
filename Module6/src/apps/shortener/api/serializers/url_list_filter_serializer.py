"""Serializer for keyset-paginated URL listing with dynamic filters."""

from rest_framework import serializers


class URLListFilterSerializer(serializers.Serializer):
    """Query parameters for ``GET /api/urls/`` with keyset pagination."""

    search = serializers.CharField(
        required=False,
        help_text="Search in short_code, title, or original_url.",
    )
    is_active = serializers.BooleanField(
        required=False,
        default=None,
        allow_null=True,
        help_text="Filter by active status.",
    )
    tag = serializers.CharField(
        required=False,
        help_text="Filter by tag name.",
    )
    created_after = serializers.DateTimeField(
        required=False,
        help_text="Only URLs created after this datetime.",
    )
    created_before = serializers.DateTimeField(
        required=False,
        help_text="Only URLs created before this datetime.",
    )
    min_clicks = serializers.IntegerField(
        required=False,
        min_value=0,
        help_text="Minimum click count.",
    )
    max_clicks = serializers.IntegerField(
        required=False,
        min_value=0,
        help_text="Maximum click count.",
    )
    ordering = serializers.ChoiceField(
        choices=[
            "created_at",
            "-created_at",
            "click_count",
            "-click_count",
            "title",
            "-title",
        ],
        required=False,
        default="-created_at",
        help_text="Field to sort by (prefix with - for descending).",
    )
    cursor = serializers.CharField(
        required=False,
        help_text="Keyset pagination cursor from a previous response.",
    )
    limit = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
        default=20,
        help_text="Number of results per page (1-100).",
    )
