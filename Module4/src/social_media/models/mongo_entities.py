"""Domain models for Mongo-backed collections — just activity logs. Uses
`_id` (Mongo's own convention), unlike the Postgres entities' `id`.
"""

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class ActivityLog:
    user_id: Any
    action: str
    target_type: str
    target_id: Any | None = None
    metadata: dict | None = None
    created_at: datetime = field(default_factory=_utcnow)
    _id: Any | None = None

    def to_doc(self) -> dict:
        d = asdict(self)
        if d["_id"] is None:
            d.pop("_id")
        return d
