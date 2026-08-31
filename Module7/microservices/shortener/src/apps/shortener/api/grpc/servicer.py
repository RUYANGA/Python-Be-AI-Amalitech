"""gRPC servicer for the internal ownership lookup.

This implements ``urlownership.ShortenerOwnership`` — the service-to-service
contract that replaced the previous synchronous HTTP endpoint
(``GET /api/v1/internal/urls/{short_code}/``). It runs in its own process
(see the ``serve_grpc`` management command) so the HTTP/Django server is not
affected by gRPC traffic.

Like the HTTPS endpoint it replaces, it is authenticated with a shared static
secret passed as gRPC metadata (``x-internal-token``), never a user's JWT.
"""

from __future__ import annotations

import logging

import grpc

from urlownership import ownership_pb2, ownership_pb2_grpc

logger = logging.getLogger(__name__)

TOKEN_METADATA_KEY = "x-internal-token"


class OwnershipServicer(ownership_pb2_grpc.ShortenerOwnershipServicer):
    """Answers existence/ownership questions about short codes."""

    def __init__(self, url_service, internal_token: str) -> None:
        self._url_service = url_service
        self._internal_token = internal_token

    def GetOwner(  # noqa: N802 - matches generated gRPC base class
        self, request, context
    ) -> ownership_pb2.GetOwnerResponse:  # type: ignore[name-defined]  # generated protobuf
        provided = ""
        for key, value in context.invocation_metadata():
            if key.lower() == TOKEN_METADATA_KEY:
                provided = value
                break

        if not self._internal_token or provided != self._internal_token:
            logger.warning("ownership.grpc_rejected short_code=%s", request.short_code)
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Not authorized.")
            return ownership_pb2.GetOwnerResponse()  # type: ignore[attr-defined]  # generated protobuf

        # Import lazily so the gRPC process only needs the URL service wired
        # (never the full URL resolution import chain at module load time).
        from apps.shortener.api.exceptions import URLNotFoundError

        try:
            url = self._url_service.resolve(request.short_code)
        except URLNotFoundError:
            return ownership_pb2.GetOwnerResponse(  # type: ignore[attr-defined]  # generated protobuf
                exists=False, url_id=0, owner_id=0
            )

        return ownership_pb2.GetOwnerResponse(  # type: ignore[attr-defined]  # generated protobuf
            exists=True,
            url_id=url.id,
            owner_id=url.owner_id or 0,
        )
