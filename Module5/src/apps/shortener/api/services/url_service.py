"""URL shortener business logic.

The service depends only on abstract interfaces
(``IURLRepository``, ``IShortCodeGenerator``) — never on Django models,
DRF, or ``secrets`` directly. That is what makes the code testable in
isolation and safe to reuse from Celery tasks, management commands, or
the async layer in Module 8.
"""

from __future__ import annotations

import logging

from apps.shortener.api.exceptions import ShortCodeGenerationError, URLNotFoundError
from apps.shortener.api.interfaces.repository import IURLRepository
from apps.shortener.api.interfaces.shortener import IShortCodeGenerator
from apps.shortener.models import URL

logger = logging.getLogger(__name__)


class URLShortenerService:
    """Orchestrates URL creation and resolution.

    Retry semantics: on a rare short-code collision the service asks the
    generator for a fresh code and re-checks the repository. After
    :attr:`MAX_GENERATION_ATTEMPTS` failures it raises
    :class:`ShortCodeGenerationError` — the caller decides what to do
    with that (Module 5 views turn it into a ``500`` after logging).
    """

    MAX_GENERATION_ATTEMPTS: int = 5
    DEFAULT_CODE_LENGTH: int = 7

    def __init__(
        self,
        repository: IURLRepository,
        generator: IShortCodeGenerator,
    ) -> None:
        self._repository = repository
        self._generator = generator

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def shorten(self, original_url: str, owner=None) -> URL:
        """Create and return a new shortened URL."""
        short_code = self._generate_unique_code()
        url = self._repository.create(
            original_url=original_url,
            short_code=short_code,
            owner=owner,
        )
        logger.info(
            "url.created short_code=%s owner_id=%s",
            short_code,
            getattr(owner, "id", None),
        )
        return url

    def resolve(self, short_code: str) -> URL:
        """Return the URL for ``short_code`` or raise :class:`URLNotFoundError`."""
        url: URL | None = self._repository.get_by_short_code(short_code)
        if url is None:
            logger.warning("url.resolve_missing short_code=%s", short_code)
            raise URLNotFoundError(short_code)
        logger.debug("url.resolved short_code=%s", short_code)
        return url

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _generate_unique_code(self) -> str:
        for attempt in range(1, self.MAX_GENERATION_ATTEMPTS + 1):
            code = self._generator.generate(self.DEFAULT_CODE_LENGTH)
            if not self._repository.exists_by_short_code(code):
                return code
            logger.warning("url.short_code_collision attempt=%d code=%s", attempt, code)
        raise ShortCodeGenerationError()
