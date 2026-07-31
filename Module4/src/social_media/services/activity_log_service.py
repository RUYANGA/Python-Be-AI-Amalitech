"""Activity-log service — the one place that knows Mongo audit logging is
optional. PostService/LikeService/CommentService/FollowService each depend
on this instead of IActivityLogRepository directly, so they can call
log(...) unconditionally instead of null-checking the dependency themselves.
"""

from typing import Any

from social_media.repositories.base import IActivityLogRepository


class ActivityLogService:
    def __init__(self, repo: IActivityLogRepository | None = None):
        self._repo = repo

    def log(
        self,
        user_id: Any,
        action: str,
        target_type: str,
        target_id: Any | None = None,
        metadata: dict | None = None,
    ) -> None:
        if self._repo is None:
            return
        self._repo.log(user_id, action, target_type, target_id, metadata)
