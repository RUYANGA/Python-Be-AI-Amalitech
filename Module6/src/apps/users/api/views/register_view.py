import logging

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.users.api.serializers import RegisterSerializer, UserSerializer
from apps.users.api.views.base_view import BaseAuthView

logger = logging.getLogger(__name__)


class RegisterView(BaseAuthView):
    """Single responsibility: handle HTTP for the register use-case."""

    @extend_schema(
        request=RegisterSerializer,
        responses={201: None},
        summary="Register a new user",
        tags=["Auth API"],
        examples=[
            OpenApiExample(
                "Register",
                value={
                    "username": "johndoe",
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john@example.com",
                    "password": "StrongPass123",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.auth_service.register(serializer.validated_data)
        logger.info("auth.register_success user_id=%s username=%s", user.id, user.username)
        return Response(
            {
                "message": "User registered successfully.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )
