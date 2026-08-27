import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.shortener.api.exceptions import ShortCodeGenerationError
from apps.shortener.api.serializers import URLCreateSerializer, URLResponseSerializer
from apps.shortener.api.views.base_view import BaseURLView
from database.connection import get_session
from database.shortener.models import TagModel, URLModel

logger = logging.getLogger(__name__)


class URLCreateView(BaseURLView):
    """``POST /api/urls/`` — create a shortened URL, owned by the caller."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="urls_create",
        request=URLCreateSerializer,
        responses={
            201: URLResponseSerializer,
            400: OpenApiResponse(description="Invalid input."),
            401: OpenApiResponse(description="Authentication required."),
            500: OpenApiResponse(description="Could not generate a unique short code."),
        },
        summary="Create a short URL",
        tags=["URLs"],
    )
    def post(self, request: Request) -> Response:
        serializer = URLCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        try:
            url = self.service.shorten(
                original_url=validated["original_url"],
                owner=request.user,
            )
        except ShortCodeGenerationError:
            logger.exception("url.create_failed reason=short_code_exhausted")
            return Response(
                {"detail": "Could not allocate a short code. Please retry."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        title = validated.get("title", "")
        tag_names = validated.get("tags", [])
        expires_at = validated.get("expires_at")

        if title or tag_names or expires_at:
            session = get_session()
            try:
                sa_url = session.merge(url)
                if title:
                    sa_url.title = title
                if expires_at:
                    sa_url.expires_at = expires_at
                if tag_names:
                    tags = []
                    for name in tag_names:
                        tag = (
                            session.query(TagModel)
                            .filter(TagModel.name == name.lower().strip())
                            .first()
                        )
                        if tag is None:
                            tag = TagModel(name=name.lower().strip())
                            session.add(tag)
                            session.flush()
                        tags.append(tag)
                    sa_url.tags = tags
                session.commit()
                session.refresh(sa_url)
                from sqlalchemy.orm import selectinload

                url = (
                    session.query(URLModel)
                    .options(selectinload(URLModel.tags), selectinload(URLModel.owner))
                    .filter(URLModel.id == sa_url.id)
                    .one()
                )
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

            self.service._repository.invalidate(url)

        response = URLResponseSerializer(url, context={"request": request})
        return Response(response.data, status=status.HTTP_201_CREATED)
