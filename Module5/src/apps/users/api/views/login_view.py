from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.users.api.serializers import LoginSerializer, UserSerializer
from apps.users.api.views.base_view import BaseAuthView


class LoginView(BaseAuthView):
    """Single responsibility: handle HTTP for the login use-case."""

    @extend_schema(
        request=LoginSerializer,
        responses={200: None},
        summary="Login and receive JWT tokens",
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
        result = self.auth_service.login(
            serializer.validated_data["username"],
            serializer.validated_data["password"],
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
