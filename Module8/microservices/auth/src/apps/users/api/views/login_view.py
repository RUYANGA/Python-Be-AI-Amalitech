import logging

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework.response import Response

from apps.users.api.exceptions import (
    AuthenticationError,
    InactiveAccountError,
    TooManyLoginAttemptsError,
)
from apps.users.api.serializers import LoginSerializer, UserSerializer
from apps.users.api.views.base_view import BaseAuthView

logger = logging.getLogger(__name__)


class LoginView(BaseAuthView):
    """Single responsibility: handle HTTP for the login use-case."""

    @extend_schema(
        request=LoginSerializer,
        responses={200: None},
        summary="Login and receive JWT tokens",
        tags=["Auth API"],
        examples=[
            OpenApiExample(
                "Login",
                value={"username": "johndoe", "password": "StrongPass123"},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = self.auth_service.login(
                serializer.validated_data["username"],
                serializer.validated_data["password"],
            )
        except TooManyLoginAttemptsError as exc:
            logger.warning(
                "auth.login_rate_limited username=%s", serializer.validated_data["username"]
            )
            throttled = Throttled(detail=str(exc))
            throttled.wait = exc.retry_after_seconds
            raise throttled from exc
        except InactiveAccountError as exc:
            logger.warning("auth.login_inactive username=%s", serializer.validated_data["username"])
            raise AuthenticationFailed(str(exc), code=exc.code) from exc
        except AuthenticationError as exc:
            logger.warning("auth.login_failed username=%s", serializer.validated_data["username"])
            raise AuthenticationFailed(str(exc), code=exc.code) from exc
        logger.info(
            "auth.login_success user_id=%s username=%s",
            result["user"].id,
            result["user"].username,
        )
        return Response(
            {
                "message": "Login successful.",
                "user": UserSerializer(result["user"]).data,
                "refresh": result["tokens"]["refresh"],
                "access": result["tokens"]["access"],
            },
            status=status.HTTP_200_OK,
        )
