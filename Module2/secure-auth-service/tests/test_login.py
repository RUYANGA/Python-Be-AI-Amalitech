"""Tests for user login functionality."""

from unittest.mock import MagicMock

import pytest

from app.exceptions import InvalidCredentialsError, UserNotFoundError
from app.models import User
from app.services.user_service import UserService


@pytest.fixture
def mock_repository() -> MagicMock:
    """Create a mock UserRepository."""
    return MagicMock()


@pytest.fixture
def mock_hasher() -> MagicMock:
    """Create a mock PasswordHasher."""
    hasher = MagicMock()
    hasher.verify.return_value = True
    return hasher


@pytest.fixture
def service(mock_repository: MagicMock, mock_hasher: MagicMock) -> UserService:
    """Create a UserService with mocked dependencies."""
    return UserService(repository=mock_repository, hasher=mock_hasher)


class TestLogin:
    """Tests for user login."""

    def test_login_success(
        self,
        service: UserService,
        mock_repository: MagicMock,
        mock_hasher: MagicMock,
    ) -> None:
        """Test successful login with valid credentials."""
        user = User(username="alice", password_hash="hashed_pw")
        mock_repository.find.return_value = user
        mock_hasher.verify.return_value = True

        result = service.login("alice", "Password1!")

        assert result == user
        mock_repository.find.assert_called_once_with("alice")
        mock_hasher.verify.assert_called_once_with("Password1!", "hashed_pw")

    def test_login_user_not_found(
        self,
        service: UserService,
        mock_repository: MagicMock,
    ) -> None:
        """Test login with non-existent user raises UserNotFoundError."""
        mock_repository.find.return_value = None

        with pytest.raises(UserNotFoundError):
            service.login("nonexistent", "Password1!")

    def test_login_wrong_password(
        self,
        service: UserService,
        mock_repository: MagicMock,
        mock_hasher: MagicMock,
    ) -> None:
        """Test login with wrong password raises InvalidCredentialsError."""
        user = User(username="alice", password_hash="hashed_pw")
        mock_repository.find.return_value = user
        mock_hasher.verify.return_value = False

        with pytest.raises(InvalidCredentialsError):
            service.login("alice", "WrongPassword1!")

    def test_login_returns_user_object(
        self,
        service: UserService,
        mock_repository: MagicMock,
    ) -> None:
        """Test that login returns the correct User object."""
        expected = User(username="alice", password_hash="hashed_pw")
        mock_repository.find.return_value = expected

        result = service.login("alice", "Password1!")

        assert result is expected
