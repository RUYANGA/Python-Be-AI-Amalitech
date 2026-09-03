"""URL shortener business logic.

The service depends only on abstract interfaces
(``IURLRepository``, ``IShortCodeGenerator``) — never on Django models,
DRF, or ``secrets`` directly. ``owner`` is never a Django ``User``
instance here (this service has no ``users`` table): it is whatever the
view's authentication layer hands it — a ``RemoteUser`` built from JWT
claims — duck-typed to just ``.id`` and ``.is_premium_tier``.
"""

from __future__ import annotations

import logging

from apps.shortener.api.exceptions import (
    CustomAliasNotAllowedError,
    CustomAliasTakenError,
    ShortCodeGenerationError,
    URLLimitExceededError,
    URLNotFoundError,
    URLNotOwnedError,
)
from apps.shortener.api.interfaces.repository import (
    IURLRepository,
    KeysetPage,
    URLListFilters,
)
from apps.shortener.api.interfaces.shortener import IShortCodeGenerator
from apps.shortener.models import URL

logger = logging.getLogger(__name__)


class URLShortenerService:
    """Orchestrates URL creation, resolution, and lifecycle management.

    Retry semantics: on a rare short-code collision the service asks the
    generator for a fresh code and re-checks the repository. After
    :attr:`MAX_GENERATION_ATTEMPTS` failures it raises
    :class:`ShortCodeGenerationError`.
    """

    MAX_GENERATION_ATTEMPTS: int = 5
    DEFAULT_CODE_LENGTH: int = 7
    FREE_TIER_MAX_ACTIVE_URLS: int = 10

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
    def create(
        self,
        original_url: str,
        owner=None,
        *,
        title: str | None = None,
        tags: list[str] | None = None,
        expires_at=None,
        custom_alias: str | None = None,
    ) -> URL:
        """Create a new shortened URL, applying optional title/tags/expiry.

        Generates a unique short code and persists the URL atomically,
        then enriches it with any of ``title``, ``tags`` or ``expires_at``
        that are provided — all in a single service call so callers never
        need to follow up with a separate ``update``.

        Free-tier owners (see ``RemoteUser.is_premium_tier``) are capped
        at :attr:`FREE_TIER_MAX_ACTIVE_URLS` active URLs; premium owners
        are unlimited. Raises :class:`URLLimitExceededError` once a free
        owner is at the cap.

        ``custom_alias``, if given, is used as the short code instead of
        an auto-generated one — a premium-only feature. Raises
        :class:`CustomAliasNotAllowedError` for a free/anonymous owner, or
        :class:`CustomAliasTakenError` if the alias is already in use.
        """
        if owner is not None and not getattr(owner, "is_premium_tier", False):
            active_count = self._repository.count_active_by_owner(owner.id)
            if active_count >= self.FREE_TIER_MAX_ACTIVE_URLS:
                logger.warning(
                    "url.create_blocked_limit owner_id=%s active_count=%s",
                    owner.id,
                    active_count,
                )
                raise URLLimitExceededError(self.FREE_TIER_MAX_ACTIVE_URLS)

        if custom_alias:
            if owner is None or not getattr(owner, "is_premium_tier", False):
                logger.warning("url.custom_alias_blocked owner_id=%s", getattr(owner, "id", None))
                raise CustomAliasNotAllowedError()
            if self._repository.exists_by_short_code(custom_alias):
                raise CustomAliasTakenError(custom_alias)
            short_code = custom_alias
        else:
            short_code = self._generate_unique_code()

        owner_id = owner.id if owner is not None else None
        url = self._repository.create(
            original_url=original_url,
            short_code=short_code,
            owner_id=owner_id,
        )
        if title or tags or expires_at:
            url = self.update(
                url,
                title=title or None,
                tags=tags or None,
                expires_at=expires_at,
            )
        logger.info("url.created short_code=%s owner_id=%s", short_code, owner_id)
        return url

    def shorten(self, original_url: str, owner=None) -> URL:
        """Create and return a new shortened URL without optional fields."""
        return self.create(original_url, owner)

    def resolve(self, short_code: str) -> URL:
        """Return the URL for ``short_code`` or raise :class:`URLNotFoundError`."""
        url: URL | None = self._repository.get_by_short_code(short_code)
        if url is None:
            logger.warning("url.resolve_missing short_code=%s", short_code)
            raise URLNotFoundError(short_code)
        logger.debug("url.resolved short_code=%s", short_code)
        return url

    def list_with_filters(
        self, filters: URLListFilters, limit: int = 10, cursor: str | None = None
    ) -> KeysetPage:
        """Return a keyset-paginated, filtered list of URLs."""
        return self._repository.list_with_filters(filters, limit=limit, cursor=cursor)

    def get_owned_by_code(self, short_code: str, owner) -> URL:
        """Return the URL for ``short_code``, if owned by ``owner``.

        Raises :class:`URLNotOwnedError` if it doesn't exist or belongs to
        someone else.
        """
        return self._get_owned_by_code_or_raise(short_code, owner)

    def partial_update_by_code(
        self,
        short_code: str,
        owner,
        *,
        original_url: str | None = None,
        title: str | None = None,
        tags: list[str] | None = None,
        expires_at=None,
    ) -> URL:
        """Update only the provided fields on the URL ``short_code``, if owned by ``owner``.

        Any of ``original_url``, ``title``, ``tags`` and ``expires_at`` that is
        provided is persisted; omitted fields are left unchanged.
        """
        url = self._get_owned_by_code_or_raise(short_code, owner)
        return self.update(
            url,
            original_url=original_url,
            title=title,
            tags=tags,
            expires_at=expires_at,
        )

    def update(
        self,
        url: URL,
        *,
        original_url: str | None = None,
        title: str | None = None,
        tags: list[str] | None = None,
        expires_at=None,
        is_active: bool | None = None,
    ) -> URL:
        """Update only the provided fields on ``url``.

        Any of ``original_url``, ``title``, ``tags``, ``expires_at`` and
        ``is_active`` that is provided is persisted; omitted fields are
        left unchanged.
        """
        updated = self._repository.update(
            url,
            original_url=original_url,
            title=title,
            tags=tags,
            expires_at=expires_at,
            is_active=is_active,
        )
        self._repository.invalidate(updated)
        logger.info(
            "url.updated id=%s short_code=%s owner_id=%s",
            updated.id,
            updated.short_code,
            updated.owner_id,
        )
        return updated

    def delete_owned_by_code(self, short_code: str, owner) -> None:
        """Delete the URL ``short_code``, if owned by ``owner``."""
        url = self._get_owned_by_code_or_raise(short_code, owner)
        self.delete(url)

    def delete(self, url: URL) -> None:
        """Delete ``url``. Callers are responsible for any ownership check."""
        self._repository.delete(url)
        logger.info(
            "url.deleted id=%s short_code=%s owner_id=%s", url.id, url.short_code, url.owner_id
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _get_owned_by_code_or_raise(self, short_code: str, owner) -> URL:
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
