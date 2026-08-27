"""SQLAlchemy model for the users app.

Mirrors ``apps.users.models.User`` — same table, different ORM.
This model is read-only; user creation/modification goes through
Django's ``AbstractUser`` to keep password hashing and auth in sync.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from database.connection import Base


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    email = Column(String(254), nullable=False, unique=True, server_default="")
    first_name = Column(String(150), nullable=False, server_default="")
    last_name = Column(String(150), nullable=False, server_default="")
    is_active = Column(Boolean, nullable=False, server_default="1")
    is_staff = Column(Boolean, nullable=False, server_default="0")
    is_premium = Column(Boolean, nullable=False, default=False)
    tier = Column(String(20), nullable=False, default="free")
    date_joined = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"
