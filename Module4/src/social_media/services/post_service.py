"""Post-related business logic."""

import json
from typing import Any

from social_media.exceptions import EmptyPostContentError
from social_media.models.postgres_entities import Post
from social_media.repositories.base import IFollowerRepository, IPostRepository
from social_media.repositories.postgres_repos import PostMetadataRepository
from social_media.services.activity_log_service import ActivityLogService
from social_media.utils.logger import get_logger

log = get_logger(__name__)

CACHE_TIMELINE_TTL = 60


class PostService:
    """Post CRUD plus cached timeline and trending feeds."""

    def __init__(
        self,
        post_repo: IPostRepository,
        follower_repo: IFollowerRepository,
        metadata_repo: PostMetadataRepository | None = None,
        cache_client: Any | None = None,
        activity_log: ActivityLogService | None = None,
    ):
        self._post_repo = post_repo
        self._follower_repo = follower_repo
        self._metadata_repo = metadata_repo
        self._cache_client = cache_client
        self._activity = activity_log or ActivityLogService()

    def _invalidate_timeline_cache(self, user_id: Any) -> None:
        """Delete every cached timeline entry belonging to the given user."""
        if self._cache_client is None:
            return
        pattern = f"timeline:{user_id}:*"
        for key in self._cache_client.scan_iter(match=pattern):
            self._cache_client.delete(key)

    def update(
        self,
        post_id: Any,
        content: str,
        tags: list[str] | None = None,
        location: str | None = None,
    ) -> dict | None:
        """Replace a post's content and metadata; returns the updated post."""
        if not content.strip():
            raise EmptyPostContentError("Post content cannot be empty")
        self._post_repo.update(post_id, {"content": content})
        if self._metadata_repo:
            self._metadata_repo.upsert(post_id, tags=tags, location=location)
        log.debug("Post updated: %s", post_id)
        return self._post_repo.find_by_id(post_id)

    def create(
        self,
        user_id: Any,
        content: str,
        tags: list[str] | None = None,
        location: str | None = None,
    ) -> dict:
        """Create a post for the given user and return its stored doc."""
        if not content.strip():
            raise EmptyPostContentError("Post content cannot be empty")
        post_id = self._post_repo.insert(Post(user_id=user_id, content=content).to_doc())
        if self._metadata_repo:
            self._metadata_repo.upsert(post_id, tags=tags, location=location)
        self._invalidate_timeline_cache(user_id)
        self._activity.log(user_id, "post_create", "post", post_id, {"content": content[:80]})
        log.debug("Post created: %s by user %s", post_id, user_id)
        post = self._post_repo.find_by_id(post_id)
        assert post is not None
        return post

    def soft_delete(self, post_id: Any) -> None:
        """Mark a post deleted and drop its metadata."""
        self._post_repo.update(post_id, {"is_deleted": True})
        if self._metadata_repo:
            self._metadata_repo.delete(post_id)
        log.debug("Post soft-deleted: %s", post_id)

    def timeline_for(self, user_id: Any, limit: int = 20, offset: int = 0) -> list[dict]:
        """Return posts by the user's followees (plus self), cached in Redis."""
        cache_key = f"timeline:{user_id}:{limit}:{offset}"
        if self._cache_client is not None:
            cached = self._cache_client.get(cache_key)
            if cached is not None:
                log.debug("Timeline cache hit for user %s", user_id)
                return json.loads(cached)
            log.debug("Timeline cache miss for user %s", user_id)

        followees = self._follower_repo.followees_of(user_id)
        followees.append(user_id)
        result = self._post_repo.feed_for_user_ids(followees, limit=limit, offset=offset)

        if self._cache_client is not None:
            self._cache_client.setex(cache_key, CACHE_TIMELINE_TTL, json.dumps(result, default=str))

        return result

    def trending(self, limit: int = 20, since_hours: int = 168) -> list[dict]:
        """Return the most engaging posts from the last N hours."""
        return self._post_repo.trending(limit=limit, since_hours=since_hours)
