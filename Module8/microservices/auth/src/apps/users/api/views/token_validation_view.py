"""REST view for verifying access tokens issued by this service.

Implements ``POST /api/v1/auth/internal/token/validate/`` — the
service-to-service endpoint that replaced the old
``authtoken.AuthTokenValidation`` gRPC contract — plus a ``GET`` variant
of the same check used exclusively by the nginx API gateway's
``auth_request`` directive (see ``/gateway``), which centralizes token
verification for shortener and analytics so neither has to call this
endpoint itself on every request. Both verify the same access token and
never decode it against anything but this service's own signing key.

Like the gRPC servicer it replaces, both are authenticated with a shared
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
        """Body-based contract: ``{"token": "..."}`` → the claims, as JSON."""
        token = request.data.get("token", "")
        return Response(self._claims(token))

    @extend_schema(exclude=True)
    def get(self, request: Request) -> Response:
        """Header-based contract for the gateway's ``auth_request`` check.

        ``auth_request`` forwards the original request's headers but
        never its body, so the token arrives as ``Authorization: Bearer
        <token>`` instead of a JSON payload — and since ``auth_request``
        only ever inspects the subrequest's status code and headers, the
        claims come back as response headers (for ``auth_request_set`` to
        pick up) rather than a JSON body: a 401 on anything invalid, a
        bare 200 with the claims on success.
        """
        header = request.META.get("HTTP_AUTHORIZATION", "")
        token = header[len("Bearer ") :] if header.startswith("Bearer ") else ""
        claims = self._claims(token)
        if not claims["valid"]:
            return Response(status=401)

        return Response(
            status=200,
            headers={
                "X-User-Id": str(claims["user_id"]),
                "X-Username": claims["username"],
                "X-User-Tier": claims["tier"],
                "X-User-Is-Premium": "true" if claims["is_premium"] else "false",
            },
        )

    @staticmethod
    def _claims(token: str) -> dict:
        try:
            # simplejwt's stub types the first positional arg as Token | None,
            # but AccessToken(str) — a raw encoded token — is its documented,
            # primary use; this is a stub gap, not a real type error.
            access_token = AccessToken(token)  # type: ignore[arg-type]
        except TokenError as exc:
            return {"valid": False, "error": str(exc)}

        return {
            "valid": True,
            "user_id": int(access_token["user_id"]),
            "username": access_token.get("username", ""),
            "is_premium": bool(access_token.get("is_premium", False)),
            "tier": access_token.get("tier", "free"),
        }
