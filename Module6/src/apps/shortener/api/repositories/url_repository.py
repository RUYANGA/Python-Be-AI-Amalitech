"""SQLAlchemy implementation of :class:`IURLRepository`.

This is the only module in the shortener app that performs database
writes — all queries go through SQLAlchemy sessions, keeping the ORM
dependency at a single boundary.

Demonstrates SQLAlchemy patterns:
- Aggregate functions (func.count, func.max, func.count.distinct())
- Keyset (cursor-based) pagination with ``filter()`` chains
- Dynamic filtering with ``or_()`` / ``and_()``
- Time-series bucketing with ``func.date_trunc()``
- Session-scoped transactions with explicit commit/rollback
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import selectinload

from apps.shortener.api.exceptions import RepositoryError
from apps.shortener.api.interfaces.repository import (
    IURLRepository,
    KeysetPage,
    URLAggregateStats,
    URLListFilters,
)
from database.connection import get_session
from database.shortener.models import ClickModel, TagModel, URLModel

logger = logging.getLogger(__name__)


class SQLAlchemyURLRepository(IURLRepository):
    # ── CRUD ──────────────────────────────────────────────────────────

    def create(
        self,
        original_url: str,
        short_code: str,
        owner=None,
    ) -> URLModel:
        session = get_session()
        try:
            sa_url = URLModel(
                original_url=original_url,
                short_code=short_code,
                owner_id=getattr(owner, "id", None),
            )
            session.add(sa_url)
            session.commit()
            session.refresh(sa_url)
            logger.info(
                "url.created id=%s short_code=%s owner_id=%s",
                sa_url.id,
                sa_url.short_code,
                sa_url.owner_id,
            )
            return sa_url
        except Exception as exc:
            logger.exception("url.create_failed short_code=%s", short_code)
            session.rollback()
            raise RepositoryError("create", short_code=short_code) from exc
        finally:
            session.close()

    def get_by_short_code(self, short_code: str) -> URLModel | None:
        session = get_session()
        try:
            return (
                session.query(URLModel)
                .options(selectinload(URLModel.tags), selectinload(URLModel.owner))
                .filter(URLModel.short_code == short_code)
                .first()
            )
        except Exception as exc:
            logger.exception("url.get_by_short_code_failed short_code=%s", short_code)
            raise RepositoryError("get_by_short_code", short_code=short_code) from exc
        finally:
            session.close()

    def exists_by_short_code(self, short_code: str) -> bool:
        session = get_session()
        try:
            return session.query(
                session.query(URLModel).filter(URLModel.short_code == short_code).exists()
            ).scalar()
        finally:
            session.close()

    def update(
        self,
        url: URLModel,
        original_url: str | None = None,
        title: str | None = None,
        tags: list[str] | None = None,
        expires_at=None,
    ) -> URLModel:
        """Apply optional partial fields to ``url``.

        Any of ``original_url``, ``title``, ``tags`` and ``expires_at`` that is
        provided is persisted; omitted fields are left unchanged.
        """
        session = get_session()
        try:
            sa_url = (
                session.query(URLModel)
                .options(selectinload(URLModel.tags), selectinload(URLModel.owner))
                .filter(URLModel.id == url.id)
                .one()
            )
            if original_url is not None:
                sa_url.original_url = original_url
            if title is not None:
                sa_url.title = title
            if expires_at is not None:
                sa_url.expires_at = expires_at
            if tags is not None:
                tag_objects = []
                for name in tags:
                    normalized = name.lower().strip()
                    tag = session.query(TagModel).filter(TagModel.name == normalized).first()
                    if tag is None:
                        tag = TagModel(name=normalized)
                        session.add(tag)
                        session.flush()
                    tag_objects.append(tag)
                sa_url.tags = tag_objects
            session.commit()
            session.refresh(sa_url)
            logger.info("url.updated id=%s short_code=%s", sa_url.id, sa_url.short_code)
            return sa_url
        except Exception as exc:
            logger.exception("url.update_failed id=%s", url.id)
            session.rollback()
            raise RepositoryError("update", id=url.id) from exc
        finally:
            session.close()

    def delete(self, url: URLModel) -> None:
        session = get_session()
        try:
            sa_url = session.query(URLModel).filter(URLModel.id == url.id).first()
            if sa_url:
                session.delete(sa_url)
                session.commit()
                logger.info("url.deleted id=%s short_code=%s", sa_url.id, sa_url.short_code)
            else:
                logger.warning("url.delete_missing id=%s", url.id)
        except Exception as exc:
            logger.exception("url.delete_failed id=%s", url.id)
            session.rollback()
            raise RepositoryError("delete", id=url.id) from exc
        finally:
            session.close()

    # ── Aggregations ──────────────────────────────────────────────────

    def get_aggregate_stats(self, url: URLModel) -> URLAggregateStats:
        session = get_session()
        try:
            total_clicks = (
                session.query(func.count(ClickModel.id))
                .filter(ClickModel.url_id == url.id)
                .scalar()
            )

            unique_countries = (
                session.query(func.count(ClickModel.country.distinct()))
                .filter(
                    ClickModel.url_id == url.id,
                    ClickModel.country != "",
                )
                .scalar()
            )

            last_clicked_at = (
                session.query(func.max(ClickModel.clicked_at))
                .filter(ClickModel.url_id == url.id)
                .scalar()
            )

            top_referer_row = (
                session.query(ClickModel.referer, func.count(ClickModel.id).label("cnt"))
                .filter(
                    ClickModel.url_id == url.id,
                    ClickModel.referer != "",
                )
                .group_by(ClickModel.referer)
                .order_by(func.count(ClickModel.id).desc())
                .first()
            )

            return URLAggregateStats(
                total_clicks=total_clicks or 0,
                unique_countries=unique_countries or 0,
                top_referer=top_referer_row[0] if top_referer_row else "",
                last_clicked_at=last_clicked_at,
            )
        finally:
            session.close()

    # ── Keyset pagination + dynamic filtering ─────────────────────────

    def list_with_filters(
        self, filters: URLListFilters, limit: int = 10, cursor: str | None = None
    ) -> KeysetPage:
        session = get_session()
        try:
            query = session.query(URLModel).options(
                selectinload(URLModel.tags), selectinload(URLModel.owner)
            )

            if filters.search:
                like_term = f"%{filters.search}%"
                query = query.filter(
                    or_(
                        URLModel.short_code.ilike(like_term),
                        URLModel.original_url.ilike(like_term),
                        URLModel.title.ilike(like_term),
                    )
                )

            if filters.is_active is not None:
                query = query.filter(URLModel.is_active == filters.is_active)

            if filters.tag:
                query = query.join(URLModel.tags).filter(TagModel.name == filters.tag)

            if filters.owner_id is not None:
                query = query.filter(URLModel.owner_id == filters.owner_id)

            if filters.created_after:
                query = query.filter(URLModel.created_at >= filters.created_after)

            if filters.created_before:
                query = query.filter(URLModel.created_at <= filters.created_before)

            if filters.min_clicks is not None:
                query = query.filter(URLModel.click_count >= filters.min_clicks)

            if filters.max_clicks is not None:
                query = query.filter(URLModel.click_count <= filters.max_clicks)

            if cursor:
                try:
                    decoded = json.loads(base64.b64decode(cursor).decode())
                    cursor_dt = datetime.fromisoformat(decoded["created_at"])
                    query = query.filter(
                        or_(
                            URLModel.created_at < cursor_dt,
                            and_(
                                URLModel.created_at == cursor_dt,
                                URLModel.id < decoded["pk"],
                            ),
                        )
                    )
                except (ValueError, KeyError):
                    pass

            order_map = {
                "created_at": URLModel.created_at.asc(),
                "-created_at": URLModel.created_at.desc(),
                "click_count": URLModel.click_count.asc(),
                "-click_count": URLModel.click_count.desc(),
                "title": URLModel.title.asc(),
                "-title": URLModel.title.desc(),
                "short_code": URLModel.short_code.asc(),
                "-short_code": URLModel.short_code.desc(),
            }
            order = order_map.get(filters.ordering, URLModel.created_at.desc())
            query = query.order_by(order, URLModel.id.desc())

            items_sa = query.limit(limit + 1).all()
            has_more = len(items_sa) > limit
            items_sa = items_sa[:limit]

            next_cursor = None
            if has_more and items_sa:
                last_sa = items_sa[-1]
                next_cursor = base64.b64encode(
                    json.dumps(
                        {
                            "pk": last_sa.id,
                            "created_at": last_sa.created_at.isoformat(),
                        }
                    ).encode()
                ).decode()

            return KeysetPage(items=items_sa, next_cursor=next_cursor, has_more=has_more)
        finally:
            session.close()

    # ── Time-series analytics ─────────────────────────────────────────

    def get_click_time_series(self, url: URLModel, days: int = 30) -> list[tuple[str, int]]:
        since = datetime.now(UTC) - timedelta(days=days)
        session = get_session()
        try:
            day_col = func.date_trunc("day", ClickModel.clicked_at).label("day")
            rows = (
                session.query(day_col, func.count(ClickModel.id).label("count"))
                .filter(
                    ClickModel.url_id == url.id,
                    ClickModel.clicked_at >= since,
                )
                .group_by(day_col)
                .order_by(day_col)
                .all()
            )
            return [(row.day.strftime("%Y-%m-%d"), row.count) for row in rows]
        finally:
            session.close()
