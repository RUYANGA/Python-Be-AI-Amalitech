"""Tests for the BcryptPasswordHasher implementation."""

import pytest

from app.security.bcrypt_hasher import BcryptPasswordHasher


@pytest.fixture
def hasher() -> BcryptPasswordHasher:
    """Create a BcryptPasswordHasher with default rounds."""
    return BcryptPasswordHasher()


@pytest.fixture
def fast_hasher() -> BcryptPasswordHasher:
    """Create a hasher with low rounds for faster tests."""
    return BcryptPasswordHasher(rounds=4)


class TestBcryptPasswordHasher:
    """Tests for bcrypt hashing."""

    def test_hash_returns_string(self, fast_hasher: BcryptPasswordHasher) -> None:
        """hash() should return a string."""
        result = fast_hasher.hash("password")

        assert isinstance(result, str)

    def test_hash_starts_with_bcrypt_prefix(
        self, fast_hasher: BcryptPasswordHasher
    ) -> None:
        """Hash should start with the bcrypt identifier."""
        result = fast_hasher.hash("password")

        assert result.startswith("$2b$")

    def test_verify_correct_password(self, fast_hasher: BcryptPasswordHasher) -> None:
        """verify() should return True for matching password."""
        hashed = fast_hasher.hash("mypassword")

        assert fast_hasher.verify("mypassword", hashed) is True

    def test_verify_wrong_password(self, fast_hasher: BcryptPasswordHasher) -> None:
        """verify() should return False for wrong password."""
        hashed = fast_hasher.hash("mypassword")

        assert fast_hasher.verify("wrongpassword", hashed) is False

    def test_hash_is_deterministic_different_each_time(
        self, fast_hasher: BcryptPasswordHasher
    ) -> None:
        """Each hash should produce a different salt."""
        hash1 = fast_hasher.hash("password")
        hash2 = fast_hasher.hash("password")

        # Same password, different salts → different hashes
        assert hash1 != hash2

    def test_verify_with_invalid_hash(self, fast_hasher: BcryptPasswordHasher) -> None:
        """verify() should return False for malformed hash."""
        assert fast_hasher.verify("password", "not-a-hash") is False

    def test_verify_with_empty_hash(self, fast_hasher: BcryptPasswordHasher) -> None:
        """verify() should return False for empty string."""
        assert fast_hasher.verify("password", "") is False

    def test_hash_empty_password(self, fast_hasher: BcryptPasswordHasher) -> None:
        """Should be able to hash an empty string (bcrypt allows it)."""
        result = fast_hasher.hash("")

        assert isinstance(result, str)
        assert fast_hasher.verify("", result) is True

    def test_default_rounds(self) -> None:
        """Default rounds should be 12."""
        hasher = BcryptPasswordHasher()

        assert hasher._rounds == 12

    def test_custom_rounds(self) -> None:
        """Custom rounds should be stored."""
        hasher = BcryptPasswordHasher(rounds=8)

        assert hasher._rounds == 8
