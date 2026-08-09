from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = User.objects.filter(username=attrs["username"]).first()
        if user is None or not user.check_password(attrs["password"]):
            raise serializers.ValidationError("Invalid username or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")
        refresh = RefreshToken.for_user(user)
        return {
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate_refresh(self, value):
        try:
            token = RefreshToken(value)
        except Exception:
            raise serializers.ValidationError("Invalid refresh token.") from None
        token.blacklist()
        return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]
