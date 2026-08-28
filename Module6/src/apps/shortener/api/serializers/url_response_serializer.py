import logging

from django.urls import reverse
from rest_framework import serializers

logger = logging.getLogger(__name__)


class URLResponseSerializer(serializers.Serializer):
    """Response shape for created / retrieved URLs."""

    id = serializers.IntegerField(read_only=True)
    original_url = serializers.URLField(max_length=2048)
    short_code = serializers.CharField(max_length=10, read_only=True)
    short_url = serializers.SerializerMethodField()
    title = serializers.CharField(max_length=255, default="")
    tags = serializers.SerializerMethodField()
    click_count = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    expires_at = serializers.DateTimeField(allow_null=True, read_only=True)
    last_accessed_at = serializers.DateTimeField(allow_null=True, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_short_url(self, obj) -> str:
        request = self.context.get("request")
        path = reverse("url-resolve", kwargs={"short_code": obj.short_code})
        if request is None:
            return path
        return request.build_absolute_uri(path)

    def get_tags(self, obj) -> list[str]:
        try:
            if hasattr(obj, "tags"):
                tags = obj.tags.all() if hasattr(obj.tags, "all") else obj.tags
                return [t.name for t in tags]
        except Exception:
            logger.warning(
                "serializer.tags_read_failed url_id=%s",
                getattr(obj, "id", None),
                exc_info=True,
            )
        return []
