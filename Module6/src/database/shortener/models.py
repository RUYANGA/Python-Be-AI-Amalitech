"""SQLAlchemy models for the shortener app.

Mirrors ``apps.shortener.models`` — same tables, different ORM.
All data access goes through these models; the Django stubs exist
only for admin registration.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from database.connection import Base


class TagModel(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, index=True, nullable=False)

    tag_assocs = relationship("URLTagModel", back_populates="tag")

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name='{self.name}')>"


class URLTagModel(Base):
    __tablename__ = "urls_tags"

    url_id = Column(Integer, ForeignKey("urls.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    url = relationship("URLModel", back_populates="tag_assocs")
    tag = relationship("TagModel", back_populates="tag_assocs")


class URLModel(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_url = Column(String(2048), nullable=False)
    short_code = Column(String(10), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False, default="")
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    click_count = Column(Integer, nullable=False, default=0, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    tag_assocs = relationship("URLTagModel", back_populates="url")
    tags = relationship("TagModel", secondary="urls_tags")
    clicks = relationship("ClickModel", back_populates="url")

    __table_args__ = (
        Index("ix_urls_owner_created", "owner_id", created_at.desc()),
        Index("ix_urls_click_count_desc", click_count.desc()),
        Index("ix_urls_active_expires", "is_active", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<URL(id={self.id}, short_code='{self.short_code}')>"


class ClickModel(Base):
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url_id = Column(
        Integer,
        ForeignKey("urls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=False, server_default="")
    referer = Column(String(2048), nullable=False, server_default="")
    country = Column(String(2), nullable=False, server_default="", index=True)
    clicked_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    url = relationship("URLModel", back_populates="clicks")

    __table_args__ = (
        Index("ix_clicks_url_clicked", "url_id", clicked_at.desc()),
        Index("ix_clicks_country_clicked", "country", clicked_at.desc()),
    )

    def __repr__(self) -> str:
        return f"<Click(id={self.id}, url_id={self.url_id})>"
