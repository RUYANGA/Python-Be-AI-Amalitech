"""Shared OpenAPI path parameters for the shortener views."""

from drf_spectacular.utils import OpenApiParameter

ID_PARAMETER = OpenApiParameter(
    # drf-spectacular renames the "pk" URL kwarg to "id" in the generated
    # schema (SCHEMA_COERCE_PATH_PK, on by default) — name this "id" too so
    # it merges with the auto-detected parameter instead of duplicating it.
    name="id",
    location=OpenApiParameter.PATH,
    type=int,
    description="The id returned by POST /api/urls/.",
)
