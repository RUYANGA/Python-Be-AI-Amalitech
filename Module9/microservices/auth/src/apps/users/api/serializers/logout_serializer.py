from rest_framework import serializers


class LogoutSerializer(serializers.Serializer):
    """Validates logout input; blacklisting is delegated to the service."""

    refresh = serializers.CharField()
