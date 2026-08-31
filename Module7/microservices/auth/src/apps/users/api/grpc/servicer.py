"""gRPC servicer for verifying access tokens issued by this service.

This implements ``authtoken.AuthTokenValidation`` — the service-to-service
contract that replaced local RS256 verification in the shortener and
analytics services. It runs in its own process (see the ``serve_grpc``
management command) so the HTTP/Django server is not affected by gRPC
traffic.

Like the shortener's ownership lookup, it is authenticated with a shared
static secret passed as gRPC metadata (``x-internal-token``), separate
from the user access token being validated.
"""

from __future__ import annotations

import logging

import grpc
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from authtoken import authtoken_pb2, authtoken_pb2_grpc

logger = logging.getLogger(__name__)

TOKEN_METADATA_KEY = "x-internal-token"


class AuthTokenValidationServicer(authtoken_pb2_grpc.AuthTokenValidationServicer):
    """Verifies an access token and returns the identity claims it carries."""

    def __init__(self, internal_token: str) -> None:
        self._internal_token = internal_token

    def ValidateAccessToken(  # noqa: N802 - matches generated gRPC base class
        self, request, context
    ) -> authtoken_pb2.ValidateAccessTokenResponse:  # type: ignore[name-defined]  # generated protobuf
        provided = ""
        for key, value in context.invocation_metadata():
            if key.lower() == TOKEN_METADATA_KEY:
                provided = value
                break

        if not self._internal_token or provided != self._internal_token:
            logger.warning("token_validation.grpc_rejected")
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Not authorized.")
            return authtoken_pb2.ValidateAccessTokenResponse()  # type: ignore[attr-defined]  # generated protobuf

        try:
            token = AccessToken(request.token)
        except TokenError as exc:
            return authtoken_pb2.ValidateAccessTokenResponse(  # type: ignore[attr-defined]  # generated protobuf
                valid=False, error=str(exc)
            )

        return authtoken_pb2.ValidateAccessTokenResponse(  # type: ignore[attr-defined]  # generated protobuf
            valid=True,
            user_id=int(token["user_id"]),
            username=token.get("username", ""),
            is_premium=bool(token.get("is_premium", False)),
            tier=token.get("tier", "free"),
        )
