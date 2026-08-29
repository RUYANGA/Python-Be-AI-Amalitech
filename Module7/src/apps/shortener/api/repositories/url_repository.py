"""Django ORM implementation of :class:`IURLRepository`.

This is the only module in the shortener app that performs database
writes for URL entities — all queries go through Django's built-in ORM,
keeping data access at a single boundary.

Demonstrates Django ORM patterns:
- Aggregate functions (``Count``, ``Max``, ``Sum``)
- Keyset (cursor-based) pagination with ``filter()`` chains
- Dynamic filtering with ``Q`` objects
- Atomic counter updates via ``F()`` expressions
- ``select_related`` / ``prefetch_related`` to avoid N+1 queries
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import UTC, datetime, timedelta

from django.db.models import Count, Max, Q
from django.db.models.functions import TruncDay

from apps.shortener.api.exceptions import RepositoryError
from apps.shortener.api.interfaces.repository import (
    IURLRepository,
    KeysetPage,
    URLAggregateStats,
    URLListFilters,
)
from apps.shortener.models import URL, Click

logger = logging.getLogger(__name__)


class DjangoURLRepository(IURLRepository):
    # ── CRUD ──────────────────────────────────────────────────────────

    def create(
        self,
        original_url: str,
        short_code: str,
        owner=None,
    ) -> URL:
        try:
            url = URL.objects.create(
                original_url=original_url,
                short_code=short_code,
                owner=owner,
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
            return (
                URL.objects.select_related("owner")
                .prefetch_related("tags")
                .filter(short_code=short_code)
                .first()
            )
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
    ) -> URL:
        """Apply optional partial fields to ``url``.

        Any of ``original_url``, ``title``, ``tags`` and ``expires_at`` that is
        provided is persisted; omitted fields are left unchanged.
        """
        try:
            if original_url is not None:
                url.original_url = original_url
            if title is not None:
                url.title = title
            if expires_at is not None:
                url.expires_at = expires_at
            if tags is not None:
                url.tags.set(self._get_or_create_tags(tags))
            url.save()
            url.refresh_from_db()
            url = URL.objects.select_related("owner").prefetch_related("tags").get(pk=url.pk)
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

    # ── Aggregations ──────────────────────────────────────────────────

    def get_aggregate_stats(self, url: URL) -> URLAggregateStats:
        try:
            clicks = Click.objects.filter(url=url)
            total_clicks = clicks.count()
            unique_countries = clicks.exclude(country="").values("country").distinct().count()
            last_clicked_at = clicks.aggregate(max=Max("clicked_at"))["max"]
            top_referer_row = (
                clicks.exclude(referer="")
                .values("referer")
                .annotate(cnt=Count("id"))
                .order_by("-cnt")
                .first()
            )
            return URLAggregateStats(
                total_clicks=total_clicks,
                unique_countries=unique_countries,
                top_referer=top_referer_row["referer"] if top_referer_row else "",
                last_clicked_at=last_clicked_at,
            )
        except Exception as exc:
            logger.exception("url.aggregate_stats_failed id=%s", url.id)
            raise RepositoryError("get_aggregate_stats", id=url.id) from exc

    # ── Keyset pagination + dynamic filtering ─────────────────────────

    def list_with_filters(
        self, filters: URLListFilters, limit: int = 10, cursor: str | None = None
    ) -> KeysetPage:
        try:
            qs = URL.objects.select_related("owner").prefetch_related("tags")

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

    # ── Time-series analytics ─────────────────────────────────────────

    def get_click_time_series(self, url: URL, days: int = 30) -> list[tuple[str, int]]:
        since = datetime.now(UTC) - timedelta(days=days)
        try:
            rows = (
                Click.objects.filter(url=url, clicked_at__gte=since)
                .annotate(day=TruncDay("clicked_at"))
                .values("day")
                .annotate(count=Count("id"))
            )
            return [
                (
                    row["day"].strftime("%Y-%m-%d") if row["day"] else "",
                    row["count"],
                )
                for row in rows
            ]
        except Exception as exc:
            logger.exception("url.click_time_series_failed id=%s", url.id)
            raise RepositoryError("get_click_time_series", id=url.id) from exc

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
