"""The one cross-service call in this service — now over gRPC.

Analytics has no ``urls`` table, so "does this short code exist, and is
it owned by the caller?" has to be answered by the shortener service,
which does own that data. This is deliberately the only place this
service makes a network call to another one — everything else (click
ingestion) flows one-way through Kafka so neither service can stall the
other on the hot paths. The call itself uses gRPC (HTTP/2 + protobuf —
faster and more compact than the REST endpoint it replaced) for the
strongly-typed ``urlownership`` contract.
"""

from __future__ import annotations

import logging

import grpc
from django.conf import settings

from urlownership import ownership_pb2, ownership_pb2_grpc

logger = logging.getLogger(__name__)


class URLOwnershipClient:
    """Looks up a short code's owner via the shortener service's gRPC API."""

    def __init__(
        self,
        grpc_url: str | None = None,
        token: str | None = None,
        timeout: float = 3.0,
    ) -> None:
        self._grpc_url = (grpc_url or settings.SHORTENER_GRPC_URL).rstrip("/")
        self._token = token or settings.INTERNAL_SERVICE_TOKEN
        self._timeout = timeout

    def get_owner_id(self, short_code: str) -> tuple[bool, int | None, int | None]:
        """Return ``(exists, url_id, owner_id)`` for ``short_code``.

        On a network failure this fails *closed* — ``(False, None, None)``
        — so a down shortener service can never leak someone else's
        analytics; it just makes analytics temporarily unavailable too.
        """
        try:
            with grpc.insecure_channel(self._grpc_url) as channel:
                stub = ownership_pb2_grpc.ShortenerOwnershipStub(channel)
                response = stub.GetOwner(
                    ownership_pb2.GetOwnerRequest(short_code=short_code),  # type: ignore[attr-defined]  # generated protobuf
                    metadata=(("x-internal-token", self._token),),
                    timeout=self._timeout,
                )
            if not response.exists:
                return False, None, None
            return True, response.url_id, response.owner_id
        except grpc.RpcError as exc:
            logger.warning(
                "url_ownership.grpc_failed short_code=%s code=%s error=%s",
                short_code,
                getattr(exc, "code", lambda: None)(),
                exc,
            )
            return False, None, None
