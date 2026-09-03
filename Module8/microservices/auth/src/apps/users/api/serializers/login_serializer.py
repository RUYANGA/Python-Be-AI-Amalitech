from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """Validates login input shape (credential check lives in the service)."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
