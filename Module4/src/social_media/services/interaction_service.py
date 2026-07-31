"""Likes, comments, follows — user-to-content and user-to-user interactions."""

from typing import Any

from social_media.exceptions import EmptyCommentError, SelfFollowError
from social_media.models.postgres_entities import Comment, Like
from social_media.repositories.base import (
    ICommentRepository,
    IFollowerRepository,
    ILikeRepository,
    IPostRepository,
)
from social_media.services.activity_log_service import ActivityLogService
from social_media.utils.logger import get_logger

log = get_logger(__name__)


class LikeService:
    def __init__(
        self,
        like_repo: ILikeRepository,
        post_repo: IPostRepository,
        activity_log: ActivityLogService | None = None,
    ):
        self._like_repo = like_repo
        self._post_repo = post_repo
        self._activity = activity_log or ActivityLogService()

    def _post_snippet(self, post_id: Any) -> str:
        post = self._post_repo.find_by_id(post_id)
        if post:
            text = post.get("content", "")
            return f'"{text[:40]}{"..." if len(text) > 40 else ""}"'
        return str(post_id)

    def _log(self, user_id: Any, action: str, target_id: Any, metadata: dict | None = None) -> None:
        self._activity.log(user_id, action, "post", target_id, metadata)

    def like(self, user_id: Any, post_id: Any) -> bool:
        if self._like_repo.exists(user_id, post_id):
            log.debug("Like skipped (already liked): user %s on post %s", user_id, post_id)
            return False
        self._like_repo.insert(Like(user_id=user_id, post_id=post_id).to_doc())
        self._post_repo.increment_like_count(post_id, +1)
        self._log(user_id, "like", post_id)
        log.debug("Post liked: %s by user %s", post_id, user_id)
        return True

    def unlike(self, user_id: Any, post_id: Any) -> bool:
        if self._like_repo.remove(user_id, post_id):
            self._post_repo.increment_like_count(post_id, -1)
            self._log(user_id, "unlike", post_id)
            log.debug("Post unliked: %s by user %s", post_id, user_id)
            return True
        log.debug("Unlike skipped (not liked): user %s on post %s", user_id, post_id)
        return False


class CommentService:
    def __init__(
        self,
        comment_repo: ICommentRepository,
        post_repo: IPostRepository,
        activity_log: ActivityLogService | None = None,
    ):
        self._comment_repo = comment_repo
        self._post_repo = post_repo
        self._activity = activity_log or ActivityLogService()

    def add(
        self,
        post_id: Any,
        user_id: Any,
        content: str,
        parent_comment_id: Any | None = None,
    ) -> dict:
        if not content.strip():
            raise EmptyCommentError("Comment content cannot be empty")
        comment_id = self._comment_repo.insert(
            Comment(
                post_id=post_id,
                user_id=user_id,
                content=content,
                parent_comment_id=parent_comment_id,
            ).to_doc()
        )
        self._post_repo.increment_comment_count(post_id, +1)
        self._activity.log(user_id, "comment", "post", post_id, {"comment_id": str(comment_id)})
        log.debug("Comment added: %s on post %s by user %s", comment_id, post_id, user_id)
        comment = self._comment_repo.find_by_id(comment_id)
        assert comment is not None
        return comment

    def for_post(self, post_id: Any) -> list:
        return self._comment_repo.for_post(post_id)


class FollowService:
    def __init__(
        self,
        follower_repo: IFollowerRepository,
        activity_log: ActivityLogService | None = None,
    ):
        self._follower_repo = follower_repo
        self._activity = activity_log or ActivityLogService()

    def follow(self, follower_id: Any, followee_id: Any) -> bool:
        if follower_id == followee_id:
            raise SelfFollowError("Cannot follow yourself")
        result = self._follower_repo.follow(follower_id, followee_id)
        if result:
            self._activity.log(follower_id, "follow", "user", followee_id)
            log.info("User %s followed user %s", follower_id, followee_id)
        else:
            log.info("Follow skipped (already following): %s -> %s", follower_id, followee_id)
        return result

    def unfollow(self, follower_id: Any, followee_id: Any) -> bool:
        result = self._follower_repo.unfollow(follower_id, followee_id) > 0
        if result:
            self._activity.log(follower_id, "unfollow", "user", followee_id)
            log.info("User %s unfollowed user %s", follower_id, followee_id)
        else:
            log.info("Unfollow skipped (not following): %s -> %s", follower_id, followee_id)
        return result
