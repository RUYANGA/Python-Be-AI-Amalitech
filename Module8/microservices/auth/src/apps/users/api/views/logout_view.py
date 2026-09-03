import logging

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.api.serializers import LogoutSerializer
from apps.users.api.views.base_view import BaseAuthView

logger = logging.getLogger(__name__)


class LogoutView(BaseAuthView):
    """Single responsibility: handle HTTP for the logout use-case."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        responses={200: None},
        summary="Logout and blacklist refresh token",
        tags=["Auth API"],
        examples=[
            OpenApiExample(
                "Logout",
                value={"refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.auth_service.logout(serializer.validated_data["refresh"])
        logger.info("User '%s' logged out.", request.user)
        return Response(
            {"message": "Logged out successfully."},
            status=status.HTTP_200_OK,
        )
