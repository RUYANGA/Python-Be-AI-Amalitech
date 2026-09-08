"""Authenticates requests using identity headers set by the API gateway.

This service never sees a raw JWT: the nginx gateway (``/gateway`` at the
repo root) verifies every access token itself — via an ``auth_request``
subrequest to the auth service — before a request ever reaches this
container, then forwards the claims it got back as trusted headers
(``X-User-Id``, ``X-Username``, ``X-User-Tier``, ``X-User-Is-Premium``).
This class only reads those headers; it makes no network call and does
no decoding of its own. Trusting them is safe because this service is
never reachable except through the gateway (no host port is published
for it), so a request that reaches this process already had its headers
set by nginx, not by the original caller.
"""

from __future__ import annotations

from dataclasses import dataclass

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

PREMIUM_TIERS = {"pro", "enterprise"}


@dataclass
class RemoteUser:
    """A stand-in for Django's ``User``, built entirely from gateway headers.

    Deliberately duck-types the surface every view/permission in this
    codebase actually touches (``id``, ``is_authenticated``) — nothing
    more, since that's all a claims-only identity can honestly provide.
    """

    id: int
    username: str
    is_premium: bool = False
    tier: str = "free"

    is_authenticated: bool = True

    @property
    def is_premium_tier(self) -> bool:
        return self.is_premium or self.tier in PREMIUM_TIERS

    def __str__(self) -> str:
        return self.username


class GatewayAuthentication(BaseAuthentication):
    """Authenticates a request using the identity headers the gateway set."""

    keyword = "Bearer"

    def authenticate(self, request) -> tuple[RemoteUser, None] | None:
        user_id = request.META.get("HTTP_X_USER_ID", "")
        if not user_id:
            return None

        try:
            uid = int(user_id)
        except ValueError as exc:
            raise exceptions.AuthenticationFailed("Invalid gateway identity header.") from exc

        user = RemoteUser(
            id=uid,
            username=request.META.get("HTTP_X_USERNAME", ""),
            is_premium=request.META.get("HTTP_X_USER_IS_PREMIUM", "") == "true",
            tier=request.META.get("HTTP_X_USER_TIER", "free"),
        )
        return (user, None)

    def authenticate_header(self, _request) -> str:
        return self.keyword


class GatewayAuthenticationScheme(OpenApiAuthenticationExtension):
    """Tells drf-spectacular how to represent ``GatewayAuthentication``.

    drf-spectacular has no idea what a custom authentication class does
    — without this, it silently omits the security scheme and Swagger UI
    never shows an "Authorize" button. Documented as a bearer token since
    that's still what a client sends, to the gateway, which turns it into
    these headers before proxying the request here.
    """

    target_class = GatewayAuthentication
    name = "jwtAuth"

    def get_security_definition(self, _auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
