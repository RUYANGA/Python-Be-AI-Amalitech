"""Abstraction for preview fetchers (Dependency Inversion).

Any strategy for turning a URL into a title/description/favicon — HTML
scraping today, an oEmbed/OpenGraph API tomorrow — is a valid
implementation as long as it fulfils this contract. Consumers
(``PreviewService``) depend on this interface, never on a concrete class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PreviewResult:
    """The extracted preview metadata for a single URL."""

    title: str
    description: str
    favicon_url: str


class IPreviewFetcher(ABC):
    """Fetches preview metadata for a single URL."""

    @abstractmethod
    def fetch(self, url: str) -> PreviewResult:
        """Return the :class:`PreviewResult` for ``url``.

        Implementations MUST NOT retry internally — that is
        ``PreviewService``'s responsibility (Single Responsibility
        Principle), via ``call_with_backoff``. A single failed attempt
        should raise ``PreviewFetchError``.
        """
        raise NotImplementedError
