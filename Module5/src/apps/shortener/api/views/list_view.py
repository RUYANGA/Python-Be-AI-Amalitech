from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.shortener.api.serializers import URLResponseSerializer
from apps.shortener.api.views.base_view import BaseURLView


class URLListView(BaseURLView):
    """``GET /api/urls/mine/`` — list the caller's shortened URLs."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="urls_list_mine",
        responses={200: URLResponseSerializer(many=True)},
        summary="List my URLs",
        tags=["URLs"],
    )
    def get(self, request: Request) -> Response:
        urls = self.service.list_owned(owner=request.user)
        response = URLResponseSerializer(urls, many=True, context={"request": request})
        return Response(response.data)
