from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.shortener.api.interfaces.repository import URLListFilters
from apps.shortener.api.serializers import URLListFilterSerializer, URLResponseSerializer
from apps.shortener.api.views.base_view import BaseURLView


class URLListView(BaseURLView):
    """``GET /api/urls/mine/`` — list the caller's shortened URLs.

    Supports keyset (cursor-based) pagination and dynamic filtering.

    Keyset pagination advantages over OFFSET:
    - O(1) page navigation — the database uses the primary key index
      directly instead of scanning ``OFFSET N`` rows.
    - Consistent results even when rows are inserted/deleted between pages.
    - Naturally stable ordering — no duplicate or missing rows.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="urls_list_mine",
        parameters=[URLListFilterSerializer],
        responses={200: URLResponseSerializer(many=True)},
        summary="List my URLs with filtering and pagination",
        tags=["URLs"],
    )
    def get(self, request: Request) -> Response:
        filter_serializer = URLListFilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        data = filter_serializer.validated_data

        filters = URLListFilters(
            search=data.get("search"),
            is_active=data.get("is_active"),
            tag=data.get("tag"),
            created_after=data.get("created_after"),
            created_before=data.get("created_before"),
            min_clicks=data.get("min_clicks"),
            max_clicks=data.get("max_clicks"),
            ordering=data.get("ordering", "-created_at"),
            owner_id=request.user.id,
        )

        cursor = data.get("cursor")
        limit = data.get("limit", 20)

        page = self.service.list_with_filters(filters, limit=limit, cursor=cursor)

        serializer = URLResponseSerializer(page.items, many=True, context={"request": request})
        return Response(
            {
                "results": serializer.data,
                "next_cursor": page.next_cursor,
                "has_more": page.has_more,
            }
        )
