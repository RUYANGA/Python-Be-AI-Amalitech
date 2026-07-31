"""Post-related business logic."""

import json
from typing import Any

from social_media.exceptions import EmptyPostContentError
from social_media.models.postgres_entities import Post
from social_media.repositories.base import IFollowerRepository, IPostRepository
from social_media.repositories.postgres_metadata_repo import PostMetadataRepository
from social_media.services.activity_log_service import ActivityLogService
from social_media.utils.logger import get_logger

log = get_logger(__name__)

CACHE_TIMELINE_TTL = 60


class PostService:
    def __init__(
        self,
        post_repo: IPostRepository,
        follower_repo: IFollowerRepository,
        metadata_repo: PostMetadataRepository | None = None,
        cache_client: Any | None = None,
        activity_log: ActivityLogService | None = None,
    ):
        self._posts = post_repo
        self._followers = follower_repo
        self._metadata = metadata_repo
        self._cache = cache_client
        self._activity = activity_log or ActivityLogService()

    def _invalidate_timeline_cache(self, user_id: Any) -> None:
        if self._cache is None:
            return
        pattern = f"timeline:{user_id}:*"
        for key in self._cache.scan_iter(match=pattern):
            self._cache.delete(key)

    def update(
        self,
        post_id: Any,
        content: str,
        tags: list[str] | None = None,
        location: str | None = None,
    ) -> dict | None:
        if not content.strip():
            raise EmptyPostContentError("Post content cannot be empty")
        self._posts.update(post_id, {"content": content})
        if self._metadata:
            self._metadata.upsert(post_id, tags=tags, location=location)
        log.debug("Post updated: %s", post_id)
        return self._posts.find_by_id(post_id)

    def create(
        self,
        user_id: Any,
        content: str,
        tags: list[str] | None = None,
        location: str | None = None,
    ) -> dict:
        if not content.strip():
            raise EmptyPostContentError("Post content cannot be empty")
        post_id = self._posts.insert(Post(user_id=user_id, content=content).to_doc())
        if self._metadata:
            self._metadata.upsert(post_id, tags=tags, location=location)
        self._invalidate_timeline_cache(user_id)
        self._activity.log(
            user_id, "post_create", "post", post_id, {"content": content[:80]}
        )
        log.debug("Post created: %s by user %s", post_id, user_id)
        doc = self._posts.find_by_id(post_id)
        assert doc is not None
        return doc

    def soft_delete(self, post_id: Any) -> None:
        self._posts.update(post_id, {"is_deleted": True})
        if self._metadata:
            self._metadata.delete(post_id)
        log.debug("Post soft-deleted: %s", post_id)

    def timeline_for(
        self, user_id: Any, limit: int = 20, offset: int = 0
    ) -> list[dict]:
        cache_key = f"timeline:{user_id}:{limit}:{offset}"
        if self._cache is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                log.debug("Timeline cache hit for user %s", user_id)
                return json.loads(cached)
            log.debug("Timeline cache miss for user %s", user_id)

        followees = self._followers.followees_of(user_id)
        followees.append(user_id)
        result = self._posts.feed_for_user_ids(followees, limit=limit, offset=offset)

        if self._cache is not None:
            self._cache.setex(
                cache_key, CACHE_TIMELINE_TTL, json.dumps(result, default=str)
            )

        return result

    def trending(self, limit: int = 20, since_hours: int = 168) -> list[dict]:
        return self._posts.trending(limit=limit, since_hours=since_hours)
