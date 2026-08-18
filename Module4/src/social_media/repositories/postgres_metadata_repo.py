"""Backward-compatibility shim — PostMetadataRepository now lives in postgres_repos.py."""

from social_media.repositories.postgres_repos import PostMetadataRepository

__all__ = ["PostMetadataRepository"]
