"""Custom DRF permission classes for the shortener API."""

from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsPremiumUser(BasePermission):
    """Grant access only to premium users (see ``User.is_premium_tier``).

    Gates the analytics endpoints per the Module 6 spec
    ("Analytics - Premium only").
    """

    message = "You need a premium account to access analytics."

    def has_permission(self, request, _view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "is_premium_tier", False))
