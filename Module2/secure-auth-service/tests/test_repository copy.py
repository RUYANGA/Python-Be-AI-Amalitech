"""Tests for the InMemoryRepository implementation."""

import pytest

from app.models import User
from app.repositories.in_memory_repository import InMemoryRepository


@pytest.fixture
def repo() -> InMemoryRepository:
    """Create a fresh InMemoryRepository."""
    return InMemoryRepository()


class TestInMemoryRepository:
    """Tests for user persistence in memory."""

    def test_save_and_find(self, repo: InMemoryRepository) -> None:
        """Saved user should be findable by username."""
        user = User(username="alice", password_hash="hashed")
        repo.save(user)

        result = repo.find("alice")

        assert result == user

    def test_find_nonexistent_returns_none(self, repo: InMemoryRepository) -> None:
        """Finding a non-existent user should return None."""
        result = repo.find("nobody")

        assert result is None

    def test_overwrite_existing_user(self, repo: InMemoryRepository) -> None:
        """Saving a user with the same name should overwrite."""
        user1 = User(username="alice", password_hash="old_hash")
        user2 = User(username="alice", password_hash="new_hash")

        repo.save(user1)
        repo.save(user2)

        result = repo.find("alice")
        assert result == user2

    def test_multiple_users(self, repo: InMemoryRepository) -> None:
        """Repository should handle multiple users independently."""
        alice = User(username="alice", password_hash="hash_a")
        bob = User(username="bob", password_hash="hash_b")

        repo.save(alice)
        repo.save(bob)

        assert repo.find("alice") == alice
        assert repo.find("bob") == bob

    def test_find_after_no_saves(self, repo: InMemoryRepository) -> None:
        """Empty repository should return None for any find."""
        assert repo.find("anyone") is None
