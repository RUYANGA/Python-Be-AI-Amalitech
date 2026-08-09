from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenRefreshView


class RefreshTokenView(TokenRefreshView):
    """Token refresh endpoint that also returns a confirmation message."""

    @extend_schema(
        request=TokenRefreshSerializer,
        responses={200: None},
        summary="Refresh access token",
        examples=[
            OpenApiExample(
                "Refresh",
                value={"refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {"message": "Token refreshed successfully.", **serializer.validated_data},
            status=status.HTTP_200_OK,
        )
