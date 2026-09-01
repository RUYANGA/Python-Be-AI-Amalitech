"""Validates access tokens by calling the auth service over REST.

Neither this service nor analytics has a ``users`` table or the JWT
signing key, so verifying a token's signature — and reading the identity
claims embedded in it — means asking the auth service instead of
decoding it locally. Calls the auth service's internal
``POST /api/v1/auth/internal/token/validate/`` endpoint, authenticated
with the shared ``X-Internal-Token`` header (the same pattern as the
analytics→shortener ownership lookup).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class TokenValidationResult:
    """The auth service's verdict for a single access token."""

    valid: bool
    user_id: int = 0
    username: str = ""
    is_premium: bool = False
    tier: str = "free"
    error: str = ""


class AuthServiceClient:
    """Verifies an access token via the auth service's internal REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 3.0,
    ) -> None:
        self._base_url = (base_url or settings.AUTH_SERVICE_URL).rstrip("/")
        self._token = token or settings.INTERNAL_SERVICE_TOKEN
        self._timeout = timeout

    def validate(self, access_token: str) -> TokenValidationResult:
        """Return the auth service's verdict for ``access_token``.

        Raises ``requests.RequestException`` on a network/transport failure
        (including a rejected internal token) — callers decide how to
        translate that into an authentication outcome.
        """
        response = requests.post(
            f"{self._base_url}/api/v1/auth/internal/token/validate/",
            json={"token": access_token},
            headers={"X-Internal-Token": self._token},
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        return TokenValidationResult(
            valid=data.get("valid", False),
            user_id=data.get("user_id", 0),
            username=data.get("username", ""),
            is_premium=data.get("is_premium", False),
            tier=data.get("tier", "free"),
            error=data.get("error", ""),
        )
