"""MongoDB connection manager.

Encapsulates client creation, authentication, and database access.
Handles the 'db already exists with different case' issue by resolving
existing DB names case-insensitively before use.
"""

from typing import Optional

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure

from social_media.config.settings import Settings
from social_media.utils.logger import get_logger

log = get_logger(__name__)


class MongoConnection:
    """MongoDB connection wrapper — inject Settings rather than importing globally."""

    _instance: Optional["MongoConnection"] = None

    def __new__(cls, settings: Settings) -> "MongoConnection":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_client(settings)
        return cls._instance

    def _init_client(self, settings: Settings) -> None:
        kwargs = {"host": settings.mongo_uri, "serverSelectionTimeoutMS": 5000}
        if settings.mongo_username and settings.mongo_password:
            kwargs.update(
                {
                    "username": settings.mongo_username,
                    "password": settings.mongo_password,
                    "authSource": settings.mongo_auth_source,
                }
            )

        self._client: MongoClient = MongoClient(**kwargs)  # type: ignore[arg-type]
        try:
            self._client.admin.command("ping")
            log.info("Connected to MongoDB at %s", settings.mongo_uri)
        except ConnectionFailure as exc:
            log.error("MongoDB connection failed: %s", exc)
            raise

        self._db: Database = self._client[self._resolve_db_name(settings.mongo_db_name)]

    def _resolve_db_name(self, desired: str) -> str:
        """Reuse an existing DB whose name matches case-insensitively.

        MongoDB stores DB names case-sensitively but forbids two names that
        differ only in case. If 'School' already exists, requesting 'school'
        would raise error code 13297. This resolver picks the existing name.
        """
        existing = self._client.list_database_names()
        for name in existing:
            if name.lower() == desired.lower() and name != desired:
                log.warning(
                    "DB '%s' already exists as '%s'; using existing name to avoid conflict",
                    desired,
                    name,
                )
                return name
        return desired

    @property
    def db(self) -> Database:
        return self._db

    def close(self) -> None:
        self._client.close()
        log.info("MongoDB connection closed")
