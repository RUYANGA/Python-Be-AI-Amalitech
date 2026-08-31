"""Validates access tokens by calling the auth service over gRPC.

Neither this service nor analytics has a ``users`` table or the JWT
signing key, so verifying a token's signature — and reading the identity
claims embedded in it — means asking the auth service instead of
decoding it locally. Uses the strongly-typed ``authtoken`` contract (the
same pattern as the shortener→analytics ownership lookup).
"""

from __future__ import annotations

import logging

import grpc
from django.conf import settings

from authtoken import authtoken_pb2, authtoken_pb2_grpc

logger = logging.getLogger(__name__)


class AuthTokenClient:
    """Verifies an access token via the auth service's gRPC API."""

    def __init__(
        self,
        grpc_url: str | None = None,
        token: str | None = None,
        timeout: float = 3.0,
    ) -> None:
        self._grpc_url = (grpc_url or settings.AUTH_GRPC_URL).rstrip("/")
        self._token = token or settings.INTERNAL_SERVICE_TOKEN
        self._timeout = timeout

    def validate(self, access_token: str) -> authtoken_pb2.ValidateAccessTokenResponse:  # type: ignore[name-defined]  # generated protobuf
        """Return the auth service's verdict for ``access_token``.

        Raises ``grpc.RpcError`` on a network/transport failure — callers
        decide how to translate that into an authentication outcome.
        """
        with grpc.insecure_channel(self._grpc_url) as channel:
            stub = authtoken_pb2_grpc.AuthTokenValidationStub(channel)
            return stub.ValidateAccessToken(
                authtoken_pb2.ValidateAccessTokenRequest(token=access_token),  # type: ignore[attr-defined]  # generated protobuf
                metadata=(("x-internal-token", self._token),),
                timeout=self._timeout,
            )
