"""Django ORM implementation of :class:`IURLRepository`.

This is the only module in the shortener app that touches
``URL.objects`` — that keeps the ORM dependency at a single boundary
and makes it easy to swap for a cached repository in Module 8.
"""

from __future__ import annotations

from collections.abc import Iterable

from apps.shortener.api.interfaces.repository import IURLRepository
from apps.shortener.models import URL


class DjangoURLRepository(IURLRepository):
    def create(
        self,
        original_url: str,
        short_code: str,
        owner=None,
    ) -> URL:
        return URL.objects.create(
            original_url=original_url,
            short_code=short_code,
            owner=owner,
        )

    def get_by_short_code(self, short_code: str) -> URL | None:
        return URL.objects.filter(short_code=short_code).first()

    def exists_by_short_code(self, short_code: str) -> bool:
        return URL.objects.filter(short_code=short_code).exists()

    def get_by_id(self, pk: int) -> URL | None:
        return URL.objects.filter(pk=pk).first()

    def list_by_owner(self, owner) -> Iterable[URL]:
        return URL.objects.filter(owner=owner)

    def update(self, url: URL, original_url: str) -> URL:
        url.original_url = original_url
        url.save(update_fields=["original_url"])
        return url

    def delete(self, url: URL) -> None:
        url.delete()
