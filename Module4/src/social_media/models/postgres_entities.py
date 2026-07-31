"""Domain models mirroring the normalized PostgreSQL schema — users, posts,
comments, followers, likes. Each uses `id` (a Postgres surrogate key), except
Follower/Like whose composite (follower_id, followee_id) / (user_id, post_id)
pair *is* the key.
"""

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def _utcnow() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


@dataclass
class User:
    """A registered user account."""

    email: str
    password_hash: str
    full_name: str | None = None
    bio: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    id: Any | None = None

    def to_doc(self) -> dict:
        """Return the entity as a dict, dropping the id when unsaved."""
        d = asdict(self)
        if d["id"] is None:
            d.pop("id")
        return d


@dataclass
class Post:
    """A single post authored by a user."""

    user_id: Any
    content: str
    like_count: int = 0
    comment_count: int = 0
    is_deleted: bool = False
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    id: Any | None = None

    def to_doc(self) -> dict:
        """Return the entity as a dict, dropping the id when unsaved."""
        d = asdict(self)
        if d["id"] is None:
            d.pop("id")
        return d


@dataclass
class Comment:
    """A comment on a post, optionally replying to another comment."""

    post_id: Any
    user_id: Any
    content: str
    parent_comment_id: Any | None = None
    is_deleted: bool = False
    created_at: datetime = field(default_factory=_utcnow)
    id: Any | None = None

    def to_doc(self) -> dict:
        """Return the entity as a dict, dropping the id when unsaved."""
        d = asdict(self)
        if d["id"] is None:
            d.pop("id")
        return d


@dataclass
class Follower:
    """A directed follow edge from follower_id to followee_id."""

    follower_id: Any
    followee_id: Any
    created_at: datetime = field(default_factory=_utcnow)

    def to_doc(self) -> dict:
        """Return the entity as a dict."""
        return asdict(self)


@dataclass
class Like:
    """A like edge from user_id to post_id."""

    user_id: Any
    post_id: Any
    created_at: datetime = field(default_factory=_utcnow)

    def to_doc(self) -> dict:
        """Return the entity as a dict."""
        return asdict(self)
