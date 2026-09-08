from __future__ import annotations

from apps.preview.api.exceptions.base import PreviewError


class CircuitOpenError(PreviewError):
    """Raised when ``DomainCircuitBreaker.allow`` blocks a domain.

    Means this domain has failed enough recent fetch attempts that we're
    deliberately not making another network call for it right now —
    the caller should treat this the same as ``URLNotAccessibleError``.
    """

    def __init__(self, domain: str) -> None:
        super().__init__(f"Circuit open for domain '{domain}'.")
        self.domain = domain
