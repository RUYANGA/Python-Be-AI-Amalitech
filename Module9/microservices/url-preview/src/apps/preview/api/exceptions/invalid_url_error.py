from __future__ import annotations

from apps.preview.api.exceptions.base import PreviewError


class InvalidURLError(PreviewError):
    """Raised when a submitted URL fails validation.

    Covers a disallowed scheme (only ``http``/``https`` are accepted) and
    the SSRF guard in ``PreviewService.fetch`` — a hostname that resolves
    to a private/loopback/link-local/reserved/multicast address, or that
    fails to resolve at all.
    """
