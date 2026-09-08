"""Custom DRF permission classes for the shortener API."""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import Http404
from rest_framework.permissions import SAFE_METHODS, BasePermission

logger = logging.getLogger(__name__)


class HasInternalServiceToken(BasePermission):
    """Grants access only to callers presenting the shared internal-service token.

    Authenticates the analytics service's ownership-lookup REST call —
    never a user's own JWT.
    """

    message = "Not authorized."

    def has_permission(self, request, _view) -> bool:
        expected = settings.INTERNAL_SERVICE_TOKEN
        provided = request.META.get("HTTP_X_INTERNAL_TOKEN", "")
        return bool(expected) and provided == expected


class IsOwnerOrReadOnly(BasePermission):
    """Object-level RBAC: only a URL's owner may edit or delete it.

    Safe methods (``GET``/``HEAD``/``OPTIONS``) are left to the view —
    this only gates the unsafe ones (``PATCH``/``DELETE``). A non-owner
    write attempt raises ``Http404`` rather than returning a plain
    permission denial, so the response can't be used to distinguish "not
    yours" from "doesn't exist" (mirrors ``URLNotOwnedError``).
    """

    def has_object_permission(self, request, _view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        if getattr(obj, "owner_id", None) != request.user.id:
            logger.warning(
                "shortener.object_not_owned method=%s owner_id=%s requester_id=%s",
                request.method,
                getattr(obj, "owner_id", None),
                request.user.id,
            )
            raise Http404("URL not found.")
        return True
