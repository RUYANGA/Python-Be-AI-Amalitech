import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.users.api.exceptions import EmailTakenError, UsernameTakenError

User = get_user_model()

logger = logging.getLogger(__name__)


class RegisterSerializer(serializers.ModelSerializer):
    """Validates and shapes registration input (no creation logic — SRP)."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "password"]
        # Disable the auto-generated UniqueValidator so our friendlier
        # message in validate_username below is what actually surfaces.
        extra_kwargs: dict = {"username": {"validators": []}}

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            logger.warning("serializer.register.username_taken username=%s", value)
            raise serializers.ValidationError(str(UsernameTakenError(value)), code="username_taken")
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            logger.warning("serializer.register.email_taken email=%s", value)
            raise serializers.ValidationError(str(EmailTakenError(value)), code="email_taken")
        return value
