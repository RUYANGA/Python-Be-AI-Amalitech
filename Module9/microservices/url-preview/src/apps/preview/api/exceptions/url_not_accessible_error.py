from __future__ import annotations

from apps.preview.api.exceptions.base import PreviewError


class URLNotAccessibleError(PreviewError):
    """Raised when every retry attempt against ``url`` has failed."""

    def __init__(self, url: str) -> None:
        super().__init__(f"URL '{url}' was not accessible after retrying.")
        self.url = url
