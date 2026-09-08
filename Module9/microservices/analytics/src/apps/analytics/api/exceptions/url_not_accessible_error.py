from __future__ import annotations

from apps.analytics.api.exceptions.base import AnalyticsError


class URLNotAccessibleError(AnalyticsError):
    """Raised when a short code doesn't exist or isn't owned by the caller.

    Deliberately indistinguishable from "doesn't exist" (same rationale
    as the shortener service's ``URLNotOwnedError``) — the view
    translates this to a 404, not a 403, so a caller can't use it to
    probe which short codes belong to other users.
    """

    def __init__(self, short_code: str) -> None:
        super().__init__(f"URL with short code '{short_code}' was not found.")
        self.short_code = short_code
