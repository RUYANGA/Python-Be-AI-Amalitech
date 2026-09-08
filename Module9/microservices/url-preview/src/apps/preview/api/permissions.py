"""Custom DRF permission classes for the url-preview API."""

from __future__ import annotations

import logging

from django.conf import settings
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


class HasInternalServiceToken(BasePermission):
    """Grants access only to callers presenting the shared internal-service token.

    Authenticates the shortener service's preview-fetch REST call —
    never a user's own JWT (this service has no notion of one).
    """

    message = "Not authorized."

    def has_permission(self, request, _view) -> bool:
        expected = settings.INTERNAL_SERVICE_TOKEN
        provided = request.META.get("HTTP_X_INTERNAL_TOKEN", "")
        return bool(expected) and provided == expected
