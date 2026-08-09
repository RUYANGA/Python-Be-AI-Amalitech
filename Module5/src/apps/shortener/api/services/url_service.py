"""URL shortener business logic.

The service depends only on abstract interfaces
(``IURLRepository``, ``IShortCodeGenerator``) — never on Django models,
DRF, or ``secrets`` directly. That is what makes the code testable in
isolation and safe to reuse from Celery tasks, management commands, or
the async layer in Module 8.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from apps.shortener.api.exceptions import (
    ShortCodeGenerationError,
    URLNotFoundError,
    URLNotOwnedError,
)
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

    def list_owned(self, owner) -> Iterable[URL]:
        """Return every URL owned by ``owner``."""
        return self._repository.list_by_owner(owner)

    def update_owned(self, pk: int, owner, original_url: str) -> URL:
        """Update ``original_url`` on the URL ``pk``, if owned by ``owner``.

        Raises :class:`URLNotOwnedError` if it doesn't exist or belongs to
        someone else.
        """
        url = self._get_owned_or_raise(pk, owner)
        updated = self._repository.update(url, original_url=original_url)
        logger.info("url.updated id=%s owner_id=%s", pk, owner.id)
        return updated

    def delete_owned(self, pk: int, owner) -> None:
        """Delete the URL ``pk``, if owned by ``owner``.

        Raises :class:`URLNotOwnedError` if it doesn't exist or belongs to
        someone else.
        """
        url = self._get_owned_or_raise(pk, owner)
        self._repository.delete(url)
        logger.info("url.deleted id=%s owner_id=%s", pk, owner.id)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _get_owned_or_raise(self, pk: int, owner) -> URL:
        url = self._repository.get_by_id(pk)
        if url is None or url.owner_id != owner.id:
            logger.warning("url.not_owned id=%s owner_id=%s", pk, owner.id)
            raise URLNotOwnedError(pk)
        return url

    def _generate_unique_code(self) -> str:
        for attempt in range(1, self.MAX_GENERATION_ATTEMPTS + 1):
            code = self._generator.generate(self.DEFAULT_CODE_LENGTH)
            if not self._repository.exists_by_short_code(code):
                return code
            logger.warning("url.short_code_collision attempt=%d code=%s", attempt, code)
        raise ShortCodeGenerationError()
