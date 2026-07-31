"""Domain models for Mongo-backed collections — just activity logs. Uses
`_id` (Mongo's own convention), unlike the Postgres entities' `id`.
"""

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def _utcnow() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


@dataclass
class ActivityLog:
    """An audit-trail entry persisted to the activity_logs collection."""

    user_id: Any
    action: str
    target_type: str
    target_id: Any | None = None
    metadata: dict | None = None
    created_at: datetime = field(default_factory=_utcnow)
    _id: Any | None = None

    def to_doc(self) -> dict:
        """Return the entity as a dict, dropping _id when unsaved."""
        d = asdict(self)
        if d["_id"] is None:
            d.pop("_id")
        return d
