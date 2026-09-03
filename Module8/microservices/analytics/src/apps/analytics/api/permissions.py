"""Custom DRF permission classes for the analytics API."""

from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import BasePermission


class HasInternalServiceToken(BasePermission):
    """Grants access only to callers presenting the shared internal-service token.

    Authenticates the shortener service's click-ingestion REST call —
    never a user's own JWT.
    """

    message = "Not authorized."

    def has_permission(self, request, _view) -> bool:
        expected = settings.INTERNAL_SERVICE_TOKEN
        provided = request.META.get("HTTP_X_INTERNAL_TOKEN", "")
        return bool(expected) and provided == expected


class IsPremiumUser(BasePermission):
    """Grant access only to premium users (see ``RemoteUser.is_premium_tier``).

    "Detailed analytics" is a premium-only feature per the tier spec.
    """

    message = "You need a premium account to access analytics."

    def has_permission(self, request, _view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "is_premium_tier", False))
