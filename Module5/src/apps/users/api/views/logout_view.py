from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.api.serializers import LogoutSerializer
from apps.users.api.views.base_view import BaseAuthView


class LogoutView(BaseAuthView):
    """Single responsibility: handle HTTP for the logout use-case."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        responses={205: None},
        summary="Logout and blacklist refresh token",
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.auth_service.logout(serializer.validated_data["refresh"])
        return Response(status=status.HTTP_205_RESET_CONTENT)
