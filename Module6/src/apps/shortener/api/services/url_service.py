"""URL shortener business logic.

The service depends only on abstract interfaces
(``IURLRepository``, ``IShortCodeGenerator``) — never on Django models,
DRF, or ``secrets`` directly. That is what makes the code testable in
isolation and safe to reuse from Celery tasks, management commands, or
the async layer in Module 8.
"""

from __future__ import annotations

import logging

from apps.shortener.api.exceptions import (
    ShortCodeGenerationError,
    URLNotFoundError,
    URLNotOwnedError,
)
from apps.shortener.api.interfaces.analytics import IClickAnalyticsRepository
from apps.shortener.api.interfaces.repository import (
    IURLRepository,
    KeysetPage,
    URLAggregateStats,
    URLListFilters,
)
from apps.shortener.api.interfaces.shortener import IShortCodeGenerator
from database.shortener.models import URLModel

logger = logging.getLogger(__name__)


class URLShortenerService:
    """Orchestrates URL creation, resolution, and analytics.

    Retry semantics: on a rare short-code collision the service asks the
    generator for a fresh code and re-checks the repository. After
    :attr:`MAX_GENERATION_ATTEMPTS` failures it raises
    :class:`ShortCodeGenerationError`.
    """

    MAX_GENERATION_ATTEMPTS: int = 5
    DEFAULT_CODE_LENGTH: int = 7

    def __init__(
        self,
        repository: IURLRepository,
        generator: IShortCodeGenerator,
        analytics_repository: IClickAnalyticsRepository | None = None,
    ) -> None:
        self._repository = repository
        self._generator = generator
        self._analytics = analytics_repository

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def shorten(self, original_url: str, owner=None) -> URLModel:
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

    def resolve(self, short_code: str) -> URLModel:
        """Return the URL for ``short_code`` or raise :class:`URLNotFoundError`."""
        url: URLModel | None = self._repository.get_by_short_code(short_code)
        if url is None:
            logger.warning("url.resolve_missing short_code=%s", short_code)
            raise URLNotFoundError(short_code)
        logger.debug("url.resolved short_code=%s", short_code)
        return url

    def record_click(
        self,
        url: URLModel,
        ip_address: str | None = None,
        user_agent: str = "",
        referer: str = "",
        country: str = "",
    ) -> None:
        """Record a click event and invalidate cached URL data."""
        if self._analytics is not None:
            self._analytics.record_click(
                url,
                ip_address=ip_address,
                user_agent=user_agent,
                referer=referer,
                country=country,
            )
            self._repository.invalidate(url)

    def list_with_filters(
        self, filters: URLListFilters, limit: int = 10, cursor: str | None = None
    ) -> KeysetPage:
        """Return a keyset-paginated, filtered list of URLs."""
        return self._repository.list_with_filters(filters, limit=limit, cursor=cursor)

    def get_aggregate_stats(self, url: URLModel) -> URLAggregateStats:
        """Return click analytics for a URL."""
        return self._repository.get_aggregate_stats(url)

    def get_click_time_series(self, url: URLModel, days: int = 30) -> list[tuple[str, int]]:
        """Return daily click counts for a URL."""
        return self._repository.get_click_time_series(url, days=days)

    def get_owned_by_code(self, short_code: str, owner) -> URLModel:
        """Return the URL for ``short_code``, if owned by ``owner``.

        Raises :class:`URLNotOwnedError` if it doesn't exist or belongs to
        someone else.
        """
        return self._get_owned_by_code_or_raise(short_code, owner)

    def update_owned_by_code(
        self,
        short_code: str,
        owner,
        original_url: str | None = None,
        title: str | None = None,
        tags: list[str] | None = None,
        expires_at=None,
    ) -> URLModel:
        """Apply optional partial fields to the URL ``short_code``, if owned by ``owner``."""
        url = self._get_owned_by_code_or_raise(short_code, owner)
        updated = self._repository.update(
            url,
            original_url=original_url,
            title=title,
            tags=tags,
            expires_at=expires_at,
        )
        logger.info("url.updated_by_code short_code=%s owner_id=%s", short_code, owner.id)
        return updated

    def partial_update_by_code(
        self,
        short_code: str,
        owner,
        *,
        original_url: str | None = None,
        title: str | None = None,
        tags: list[str] | None = None,
        expires_at=None,
    ) -> URLModel:
        """Update only the provided fields on the URL ``short_code``, if owned by ``owner``."""
        return self.update_owned_by_code(
            short_code,
            owner,
            original_url=original_url,
            title=title,
            tags=tags,
            expires_at=expires_at,
        )

    def delete_owned_by_code(self, short_code: str, owner) -> None:
        """Delete the URL ``short_code``, if owned by ``owner``."""
        url = self._get_owned_by_code_or_raise(short_code, owner)
        self._repository.delete(url)
        logger.info("url.deleted_by_code short_code=%s owner_id=%s", short_code, owner.id)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _get_owned_by_code_or_raise(self, short_code: str, owner) -> URLModel:
        url = self._repository.get_by_short_code(short_code)
        if url is None or url.owner_id != owner.id:
            logger.warning("url.not_owned short_code=%s owner_id=%s", short_code, owner.id)
            raise URLNotOwnedError(short_code)
        return url

    def _generate_unique_code(self) -> str:
        for attempt in range(1, self.MAX_GENERATION_ATTEMPTS + 1):
            code = self._generator.generate(self.DEFAULT_CODE_LENGTH)
            if not self._repository.exists_by_short_code(code):
                return code
            logger.warning("url.short_code_collision attempt=%d code=%s", attempt, code)
        raise ShortCodeGenerationError()
