"""Django ORM implementation of :class:`IURLRepository`.

This is the only module in the shortener app that performs database
writes for URL entities — all queries go through Django's built-in ORM,
keeping data access at a single boundary.

``owner_id`` is a bare integer here (see ``models.py``), so there is no
``select_related("owner")`` to do — the owning ``User`` row lives in the
auth service's own database.
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime

from django.db.models import Q

from apps.shortener.api.exceptions import RepositoryError
from apps.shortener.api.interfaces.repository import (
    IURLRepository,
    KeysetPage,
    URLListFilters,
)
from apps.shortener.models import URL

logger = logging.getLogger(__name__)


class DjangoURLRepository(IURLRepository):
    # ── CRUD ──────────────────────────────────────────────────────────

    def create(
        self,
        original_url: str,
        short_code: str,
        owner_id: int | None = None,
    ) -> URL:
        try:
            url = URL.objects.create(
                original_url=original_url,
                short_code=short_code,
                owner_id=owner_id,
            )
            logger.info(
                "url.created id=%s short_code=%s owner_id=%s",
                url.id,
                url.short_code,
                url.owner_id,
            )
            return url
        except Exception as exc:
            logger.exception("url.create_failed short_code=%s", short_code)
            raise RepositoryError("create", short_code=short_code) from exc

    def get_by_short_code(self, short_code: str) -> URL | None:
        try:
            return URL.objects.prefetch_related("tags").filter(short_code=short_code).first()
        except Exception as exc:
            logger.exception("url.get_by_short_code_failed short_code=%s", short_code)
            raise RepositoryError("get_by_short_code", short_code=short_code) from exc

    def exists_by_short_code(self, short_code: str) -> bool:
        try:
            return URL.objects.filter(short_code=short_code).exists()
        except Exception as exc:
            logger.exception("url.exists_by_short_code_failed short_code=%s", short_code)
            raise RepositoryError("exists_by_short_code", short_code=short_code) from exc

    def update(
        self,
        url: URL,
        original_url: str | None = None,
        title: str | None = None,
        tags: list[str] | None = None,
        expires_at=None,
        is_active: bool | None = None,
    ) -> URL:
        """Apply optional partial fields to ``url``.

        Any of ``original_url``, ``title``, ``tags``, ``expires_at`` and
        ``is_active`` that is provided is persisted; omitted fields are
        left unchanged.
        """
        try:
            if original_url is not None:
                url.original_url = original_url
            if title is not None:
                url.title = title
            if expires_at is not None:
                url.expires_at = expires_at
            if is_active is not None:
                url.is_active = is_active
            if tags is not None:
                url.tags.set(self._get_or_create_tags(tags))
            url.save()
            url.refresh_from_db()
            url = URL.objects.prefetch_related("tags").get(pk=url.pk)
            logger.info("url.updated id=%s short_code=%s", url.id, url.short_code)
            return url
        except Exception as exc:
            logger.exception("url.update_failed id=%s", url.id)
            raise RepositoryError("update", id=url.id) from exc

    def delete(self, url: URL) -> None:
        try:
            url.delete()
            logger.info("url.deleted id=%s short_code=%s", url.id, url.short_code)
        except Exception as exc:
            logger.exception("url.delete_failed id=%s", url.id)
            raise RepositoryError("delete", id=url.id) from exc

    # ── Keyset pagination + dynamic filtering ─────────────────────────

    def list_with_filters(
        self, filters: URLListFilters, limit: int = 10, cursor: str | None = None
    ) -> KeysetPage:
        try:
            qs = URL.objects.prefetch_related("tags")

            if filters.search:
                qs = qs.filter(
                    Q(short_code__icontains=filters.search)
                    | Q(original_url__icontains=filters.search)
                    | Q(title__icontains=filters.search)
                )

            if filters.is_active is not None:
                qs = qs.filter(is_active=filters.is_active)

            if filters.tag:
                qs = qs.filter(tags__name=filters.tag.strip().lower())

            if filters.owner_id is not None:
                qs = qs.filter(owner_id=filters.owner_id)

            if filters.created_after:
                qs = qs.filter(created_at__gte=filters.created_after)

            if filters.created_before:
                qs = qs.filter(created_at__lte=filters.created_before)

            if filters.min_clicks is not None:
                qs = qs.filter(click_count__gte=filters.min_clicks)

            if filters.max_clicks is not None:
                qs = qs.filter(click_count__lte=filters.max_clicks)

            if cursor:
                try:
                    decoded = json.loads(base64.b64decode(cursor).decode())
                    cursor_dt = datetime.fromisoformat(decoded["created_at"])
                    qs = qs.filter(
                        Q(created_at__lt=cursor_dt)
                        | (Q(created_at=cursor_dt) & Q(id__lt=decoded["pk"]))
                    )
                except (ValueError, KeyError, TypeError):
                    pass

            order_map = {
                "created_at": "created_at",
                "-created_at": "-created_at",
                "click_count": "click_count",
                "-click_count": "-click_count",
                "title": "title",
                "-title": "-title",
                "short_code": "short_code",
                "-short_code": "-short_code",
            }
            order = order_map.get(filters.ordering, "-created_at")
            qs = qs.order_by(order, "-id")

            item_list = list(qs[: (limit + 1)])
            has_more = len(item_list) > limit
            item_list = item_list[:limit]

            next_cursor = None
            if has_more and item_list:
                last = item_list[-1]
                next_cursor = base64.b64encode(
                    json.dumps(
                        {
                            "pk": last.id,
                            "created_at": last.created_at.isoformat(),
                        }
                    ).encode()
                ).decode()

            return KeysetPage(items=item_list, next_cursor=next_cursor, has_more=has_more)
        except Exception as exc:
            logger.exception("url.list_with_filters_failed owner_id=%s", filters.owner_id)
            raise RepositoryError("list_with_filters", owner_id=filters.owner_id) from exc

    def count_active_by_owner(self, owner_id: int) -> int:
        try:
            return URL.objects.filter(owner_id=owner_id, is_active=True).count()
        except Exception as exc:
            logger.exception("url.count_active_by_owner_failed owner_id=%s", owner_id)
            raise RepositoryError("count_active_by_owner", owner_id=owner_id) from exc

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _get_or_create_tags(tags: list[str]):
        from apps.shortener.models import Tag

        tag_objects = []
        for name in tags:
            normalized = name.lower().strip()
            if not normalized:
                continue
            tag, _ = Tag.objects.get_or_create(name=normalized)
            tag_objects.append(tag)
        return tag_objects
