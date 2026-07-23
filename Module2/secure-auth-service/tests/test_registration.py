"""Tests for user registration functionality."""

from unittest.mock import MagicMock

import pytest

from app.exceptions import (
    InvalidPasswordError,
    UserAlreadyExistsError,
)
from app.models import User
from app.services.user_service import UserService


@pytest.fixture
def mock_repository() -> MagicMock:
    """Create a mock UserRepository."""
    repo = MagicMock()
    repo.find.return_value = None
    return repo


@pytest.fixture
def mock_hasher() -> MagicMock:
    """Create a mock PasswordHasher."""
    hasher = MagicMock()
    hasher.hash_password.return_value = "$2b$12$hashedpassword"
    hasher.verify.return_value = True
    return hasher


@pytest.fixture
def service(mock_repository: MagicMock, mock_hasher: MagicMock) -> UserService:
    """Create a UserService with mocked dependencies."""
    return UserService(repository=mock_repository, hasher=mock_hasher)


class TestRegistration:
    """Tests for user registration."""

    def test_register_new_user(
        self,
        service: UserService,
        mock_repository: MagicMock,
        mock_hasher: MagicMock,
    ) -> None:
        """Test successful registration of a new user."""
        service.register("alice", "Password1!")

        mock_hasher.hash_password.assert_called_once_with("Password1!")
        mock_repository.save.assert_called_once_with(
            User(username="alice", password_hash="$2b$12$hashedpassword")
        )

    def test_register_duplicate_user_raises_error(
        self,
        service: UserService,
        mock_repository: MagicMock,
    ) -> None:
        """Test that registering a duplicate user raises UserAlreadyExistsError."""
        mock_repository.find.return_value = User(
            username="alice", password_hash="hashed"
        )

        with pytest.raises(UserAlreadyExistsError):
            service.register("alice", "Password1!")

        mock_repository.save.assert_not_called()

    def test_register_weak_password_too_short(
        self,
        service: UserService,
    ) -> None:
        """Test that a password shorter than 8 chars is rejected."""
        with pytest.raises(InvalidPasswordError):
            service.register("alice", "Ab1!")

    def test_register_password_no_uppercase(
        self,
        service: UserService,
    ) -> None:
        """Test that a password without uppercase is rejected."""
        with pytest.raises(InvalidPasswordError):
            service.register("alice", "password1!")

    def test_register_password_no_lowercase(
        self,
        service: UserService,
    ) -> None:
        """Test that a password without lowercase is rejected."""
        with pytest.raises(InvalidPasswordError):
            service.register("alice", "PASSWORD1!")

    def test_register_password_no_digit(
        self,
        service: UserService,
    ) -> None:
        """Test that a password without a digit is rejected."""
        with pytest.raises(InvalidPasswordError):
            service.register("alice", "Password!")

    def test_register_password_no_symbol(
        self,
        service: UserService,
    ) -> None:
        """Test that a password without a symbol is rejected."""
        with pytest.raises(InvalidPasswordError):
            service.register("alice", "Password1")

    def test_repository_property_exposes_repository(
        self,
        service: UserService,
        mock_repository: MagicMock,
    ) -> None:
        """Test that the repository property returns the injected repository."""
        assert service.repository is mock_repository
