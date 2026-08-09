from rest_framework import serializers

from apps.shortener.models import URL


class URLResponseSerializer(serializers.ModelSerializer):
    """Response shape for created / retrieved URLs."""

    short_url = serializers.SerializerMethodField()

    class Meta:
        model = URL
        fields = ["id", "original_url", "short_code", "short_url", "created_at"]
        read_only_fields = fields

    def get_short_url(self, obj: URL) -> str:
        request = self.context.get("request")
        path = f"/{obj.short_code}/"
        if request is None:
            return path
        return request.build_absolute_uri(path)
