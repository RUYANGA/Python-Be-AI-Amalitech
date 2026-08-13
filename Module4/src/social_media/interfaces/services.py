"""Service-layer contracts — what the application and composition root rely on.

Each concrete service in services/ implements one of these interfaces so
callers (e.g. the CLI or tests) depend on the abstraction, not the
implementation.
"""

from abc import ABC, abstractmethod
from typing import Any


class IActivityLogService(ABC):
    """Audit-logging contract — records user actions."""

    @abstractmethod
    def log(
        self,
        user_id: Any,
        action: str,
        target_type: str,
        target_id: Any | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Record an activity entry if a backing repository is configured."""
        ...


class IUserService(ABC):
    """Registration and authentication for users."""

    @abstractmethod
    def register(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
        bio: str | None = None,
    ) -> dict:
        """Create a new user after validating email, password, name, and bio."""
        ...

    @abstractmethod
    def update_profile(
        self,
        user_id: Any,
        *,
        full_name: str | None = None,
        bio: str | None = None,
        email: str | None = None,
    ) -> dict:
        """Update profile details; None means keep the current value."""
        ...

    @abstractmethod
    def authenticate(self, email: str, password: str) -> dict:
        """Return the user doc if the email/password pair is valid."""
        ...


class IPostService(ABC):
    """Post CRUD plus cached timeline and trending feeds."""

    @abstractmethod
    def create(
        self,
        user_id: Any,
        content: str,
        tags: list[str] | None = None,
        location: str | None = None,
    ) -> dict:
        """Create a post for the given user and return its stored doc."""
        ...

    @abstractmethod
    def update(
        self,
        post_id: Any,
        content: str,
        tags: list[str] | None = None,
        location: str | None = None,
    ) -> dict | None:
        """Replace a post's content and metadata; returns the updated post."""
        ...

    @abstractmethod
    def soft_delete(self, post_id: Any) -> None:
        """Mark a post deleted and drop its metadata."""
        ...

    @abstractmethod
    def timeline_for(self, user_id: Any, limit: int = 20, offset: int = 0) -> list[dict]:
        """Return posts by the user's followees (plus self), cached in Redis."""
        ...

    @abstractmethod
    def trending(self, limit: int = 20, since_hours: int = 168) -> list[dict]:
        """Return the most engaging posts from the last N hours."""
        ...


class ILikeService(ABC):
    """Like/unlike a post, maintaining the post's like counter."""

    @abstractmethod
    def like(self, user_id: Any, post_id: Any) -> bool:
        """Record a like; returns False if the user already liked the post."""
        ...

    @abstractmethod
    def unlike(self, user_id: Any, post_id: Any) -> bool:
        """Remove a like; returns False if the user had not liked the post."""
        ...


class ICommentService(ABC):
    """Add and list comments on posts."""

    @abstractmethod
    def add(
        self,
        post_id: Any,
        user_id: Any,
        content: str,
        parent_comment_id: Any | None = None,
    ) -> dict:
        """Add a comment to a post (optionally as a reply) and return it."""
        ...

    @abstractmethod
    def for_post(self, post_id: Any) -> list:
        """Return the non-deleted comments on a post, oldest first."""
        ...


class IFollowService(ABC):
    """Follow and unfollow users."""

    @abstractmethod
    def follow(self, follower_id: Any, followee_id: Any) -> bool:
        """Follow a user; returns False if the edge already exists."""
        ...

    @abstractmethod
    def unfollow(self, follower_id: Any, followee_id: Any) -> bool:
        """Unfollow a user; returns False if the edge did not exist."""
        ...
