"""Abstract repository contracts — no database-specific code lives here.

Following the Dependency Inversion Principle: services depend on these
interfaces, not on concrete Postgres or Mongo implementations. Concrete
repositories live in repositories/postgres_repos.py (PostgreSQL) and
repositories/mongo_repos.py (MongoDB).
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any


class IRepository(ABC):
    """Generic repository interface."""

    @abstractmethod
    def insert(self, document: dict) -> Any:
        """Insert a document and return its generated id."""
        ...

    @abstractmethod
    def find_by_id(self, _id: Any) -> dict | None:
        """Return the document for an id, or None."""
        ...

    @abstractmethod
    def find(self, query: dict, limit: int = 0) -> Iterable[dict]:
        """Return documents matching a query, optionally capped by limit."""
        ...

    @abstractmethod
    def update(self, _id: Any, changes: dict) -> int:
        """Apply changes to a document and return the rows affected."""
        ...

    @abstractmethod
    def delete(self, _id: Any) -> int:
        """Delete a document and return the rows affected."""
        ...


class IUserRepository(IRepository):
    """User repository contract — shared CRUD plus email lookup."""

    @abstractmethod
    def find_by_email(self, email: str) -> dict | None:
        """Return the user document for an email, or None."""
        ...


class IActivityLogRepository(IRepository):
    """Activity-log repository contract — shared CRUD plus audit log()."""

    @abstractmethod
    def log(
        self,
        user_id: Any,
        action: str,
        target_type: str,
        target_id: Any | None = None,
        metadata: dict | None = None,
    ) -> Any:
        """Persist an activity entry and return its generated id."""
        ...


class IPostRepository(IRepository):
    """Post repository contract — shared CRUD plus feed/trending/counters."""

    @abstractmethod
    def feed_for_user_ids(self, user_ids: list[Any], limit: int = 20, offset: int = 0) -> list:
        """Return posts by the given authors, newest first."""
        ...

    @abstractmethod
    def trending(self, limit: int = 20, since_hours: int = 168) -> list:
        """Return recent posts ordered by engagement score."""
        ...

    @abstractmethod
    def increment_like_count(self, post_id: Any, delta: int) -> None:
        """Adjust a post's like counter."""
        ...

    @abstractmethod
    def increment_comment_count(self, post_id: Any, delta: int) -> None:
        """Adjust a post's comment counter."""
        ...


class ICommentRepository(IRepository):
    """Comment repository contract — shared CRUD plus per-post listing."""

    @abstractmethod
    def for_post(self, post_id: Any) -> list:
        """Return comments for a post, oldest first."""
        ...


class IFollowerRepository(IRepository):
    """Follower repository contract — shared CRUD plus follow graph queries."""

    @abstractmethod
    def follow(self, follower_id: Any, followee_id: Any) -> bool:
        """Add a follow edge; return False if it already exists."""
        ...

    @abstractmethod
    def followees_of(self, user_id: Any) -> list[Any]:
        """Return the ids of users the given user follows."""
        ...

    @abstractmethod
    def followers_of(self, user_id: Any) -> list[Any]:
        """Return the ids of users following the given user."""
        ...

    @abstractmethod
    def unfollow(self, follower_id: Any, followee_id: Any) -> int:
        """Remove a follow edge and return the rows affected."""
        ...


class ILikeRepository(IRepository):
    """Like repository contract — shared CRUD plus existence checks."""

    @abstractmethod
    def exists(self, user_id: Any, post_id: Any) -> bool:
        """Return True if the user has already liked the post."""
        ...

    @abstractmethod
    def remove(self, user_id: Any, post_id: Any) -> int:
        """Remove a like edge and return the rows affected."""
        ...
