from __future__ import annotations

from apps.shortener.api.exceptions.base import ShortenerError


class URLNotOwnedError(ShortenerError):
    """Raised when a URL id doesn't exist or isn't owned by the caller.

    Deliberately indistinguishable from "doesn't exist" — views translate
    this to a 404, not a 403, so callers can't use it to probe which ids
    belong to other users.
    """

    def __init__(self, pk: int) -> None:
        super().__init__(f"URL with id '{pk}' was not found.")
        self.pk = pk
