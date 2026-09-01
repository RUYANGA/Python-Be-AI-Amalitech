"""REST view for verifying access tokens issued by this service.

Implements ``POST /api/v1/auth/internal/token/validate/`` — the
service-to-service endpoint that replaced the old
``authtoken.AuthTokenValidation`` gRPC contract. The shortener and
analytics services call this instead of decoding a token locally, since
neither holds the HS256 signing key or has a ``users`` table to look the
caller up in.

Like the gRPC servicer it replaces, it is authenticated with a shared
static secret in the ``X-Internal-Token`` header — never a user's own
access token.
"""

from __future__ import annotations

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.users.api.permissions import HasInternalServiceToken

logger = logging.getLogger(__name__)


class TokenValidationView(APIView):
    """Verifies an access token and returns the identity claims it carries."""

    permission_classes = [HasInternalServiceToken]

    @extend_schema(exclude=True)
    def post(self, request: Request) -> Response:
        token = request.data.get("token", "")
        try:
            access_token = AccessToken(token)
        except TokenError as exc:
            return Response({"valid": False, "error": str(exc)})

        return Response(
            {
                "valid": True,
                "user_id": int(access_token["user_id"]),
                "username": access_token.get("username", ""),
                "is_premium": bool(access_token.get("is_premium", False)),
                "tier": access_token.get("tier", "free"),
            }
        )
