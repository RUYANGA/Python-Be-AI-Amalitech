from __future__ import annotations

from apps.preview.api.exceptions.base import PreviewError


class PreviewFetchError(PreviewError):
    """Raised by a single :class:`IPreviewFetcher` attempt on failure.

    Wraps a ``requests.RequestException``, a non-2xx response, or a
    non-HTML ``Content-Type`` — used only internally, between
    ``HTMLPreviewFetcher``/``call_with_backoff`` and ``PreviewService``.
    Never raised out of a view directly.
    """
