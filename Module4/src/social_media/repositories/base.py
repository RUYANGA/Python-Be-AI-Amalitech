"""Abstract repository contracts — no database-specific code lives here.

Following the Dependency Inversion Principle: services depend on these
interfaces, not on concrete Postgres or Mongo implementations. Concrete
repositories live in postgres_repos.py (PostgreSQL) and mongo_repos.py
(MongoDB) — each database's implementation detail stays in its own file.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any


class IRepository(ABC):
    """Generic repository interface."""

    @abstractmethod
    def insert(self, document: dict) -> Any: ...

    @abstractmethod
    def find_by_id(self, _id: Any) -> dict | None: ...

    @abstractmethod
    def find(self, query: dict, limit: int = 0) -> Iterable[dict]: ...

    @abstractmethod
    def update(self, _id: Any, changes: dict) -> int: ...

    @abstractmethod
    def delete(self, _id: Any) -> int: ...


class IUserRepository(IRepository):
    @abstractmethod
    def find_by_email(self, email: str) -> dict | None: ...


class IActivityLogRepository(IRepository):
    @abstractmethod
    def log(
        self,
        user_id: Any,
        action: str,
        target_type: str,
        target_id: Any | None = None,
        metadata: dict | None = None,
    ) -> Any: ...


class IPostRepository(IRepository):
    @abstractmethod
    def feed_for_user_ids(
        self, user_ids: list[Any], limit: int = 20, offset: int = 0
    ) -> list: ...

    @abstractmethod
    def trending(self, limit: int = 20, since_hours: int = 168) -> list: ...

    @abstractmethod
    def increment_like_count(self, post_id: Any, delta: int) -> None: ...

    @abstractmethod
    def increment_comment_count(self, post_id: Any, delta: int) -> None: ...


class ICommentRepository(IRepository):
    @abstractmethod
    def for_post(self, post_id: Any) -> list: ...


class IFollowerRepository(IRepository):
    @abstractmethod
    def follow(self, follower_id: Any, followee_id: Any) -> bool: ...

    @abstractmethod
    def followees_of(self, user_id: Any) -> list[Any]: ...

    @abstractmethod
    def followers_of(self, user_id: Any) -> list[Any]: ...

    @abstractmethod
    def unfollow(self, follower_id: Any, followee_id: Any) -> int: ...


class ILikeRepository(IRepository):
    @abstractmethod
    def exists(self, user_id: Any, post_id: Any) -> bool: ...

    @abstractmethod
    def remove(self, user_id: Any, post_id: Any) -> int: ...
