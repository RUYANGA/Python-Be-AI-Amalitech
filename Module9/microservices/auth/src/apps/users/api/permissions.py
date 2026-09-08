"""Custom DRF permission classes for the users API."""

from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import BasePermission

INTERNAL_TOKEN_HEADER = "HTTP_X_INTERNAL_TOKEN"


class HasInternalServiceToken(BasePermission):
    """Grants access only to callers presenting the shared internal-service token.

    Authenticates service-to-service REST calls (e.g. the shortener and
    analytics services' token-validation lookups) — never a user's own JWT.
    """

    message = "Not authorized."

    def has_permission(self, request, _view) -> bool:
        expected = settings.INTERNAL_SERVICE_TOKEN
        provided = request.META.get(INTERNAL_TOKEN_HEADER, "")
        return bool(expected) and provided == expected
