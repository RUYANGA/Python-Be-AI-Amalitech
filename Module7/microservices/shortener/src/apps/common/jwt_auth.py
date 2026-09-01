"""JWT verification for every service except auth.

This service never signs a token and has no ``users`` table to look the
caller up in — it verifies an access token by calling the auth
service's internal REST endpoint (see ``apps.common.auth_service_client``)
and builds a lightweight, in-memory "remote user" straight from the
claims it returns. There is no local decoding and no database lookup:
anything this service needs to know about the caller (id, username,
premium status) was embedded in the token by the auth service at login
time (see the auth service's ``JWTTokenService``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from apps.common.auth_service_client import AuthServiceClient

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
    """Authenticates a request using an access token verified by auth."""

    keyword = "Bearer"

    def authenticate(self, request) -> tuple[RemoteUser, str] | None:
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith(f"{self.keyword} "):
            return None
        token = header[len(self.keyword) + 1 :]

        response = self._validate(token)
        user = RemoteUser(
            id=response.user_id,
            username=response.username,
            is_premium=response.is_premium,
            tier=response.tier,
        )
        return (user, token)

    def authenticate_header(self, _request) -> str:
        return self.keyword

    @staticmethod
    def _validate(token: str):
        try:
            response = AuthServiceClient().validate(token)
        except requests.RequestException as exc:
            logger.warning("jwt.auth_service_failed error=%s", exc)
            raise exceptions.AuthenticationFailed("Could not verify access token.") from exc

        if not response.valid:
            raise exceptions.AuthenticationFailed(response.error or "Invalid access token.")
        return response


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
