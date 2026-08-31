"""JWT verification for every service except auth.

This service never signs a token and has no ``users`` table to look
the caller up in — it only verifies a token's RS256 signature against
the auth service's public key and builds a lightweight, in-memory
"remote user" straight from the claims. There is no database lookup:
anything this service needs to know about the caller (id, username,
premium status) was embedded in the token by the auth service at
login time (see the auth service's ``JWTTokenService``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import jwt
from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

logger = logging.getLogger(__name__)

PREMIUM_TIERS = {"pro", "enterprise"}


@dataclass
class RemoteUser:
    """A stand-in for Django's ``User``, built entirely from JWT claims.

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


class RemoteJWTAuthentication(BaseAuthentication):
    """Authenticates a request using an RS256 access token from auth."""

    keyword = "Bearer"

    def authenticate(self, request) -> tuple[RemoteUser, str] | None:
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith(f"{self.keyword} "):
            return None
        token = header[len(self.keyword) + 1 :]

        claims = self._decode(token)
        if claims.get("token_type") != "access":
            raise exceptions.AuthenticationFailed("Expected an access token.")

        user = RemoteUser(
            # simplejwt always encodes user_id as a string claim; every
            # comparison against a stored owner_id needs it as an int.
            id=int(claims["user_id"]),
            username=claims.get("username", ""),
            is_premium=claims.get("is_premium", False),
            tier=claims.get("tier", "free"),
        )
        return (user, token)

    def authenticate_header(self, _request) -> str:
        return self.keyword

    @staticmethod
    def _decode(token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=["RS256"])
        except jwt.ExpiredSignatureError as exc:
            raise exceptions.AuthenticationFailed("Access token expired.") from exc
        except jwt.InvalidTokenError as exc:
            logger.warning("jwt.invalid_token error=%s", exc)
            raise exceptions.AuthenticationFailed("Invalid access token.") from exc


class RemoteJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """Tells drf-spectacular how to represent ``RemoteJWTAuthentication``.

    drf-spectacular ships a built-in extension for
    ``rest_framework_simplejwt.authentication.JWTAuthentication`` (that's
    why the auth service's Swagger UI already has an "Authorize" button)
    but has no idea what a custom authentication class does — without
    this, it silently omits the security scheme and Swagger UI never
    shows an "Authorize" button at all.
    """

    target_class = RemoteJWTAuthentication
    name = "jwtAuth"

    def get_security_definition(self, _auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
