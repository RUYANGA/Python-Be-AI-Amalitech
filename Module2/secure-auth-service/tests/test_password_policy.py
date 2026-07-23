"""Tests for password policy enforcement."""

from unittest.mock import MagicMock

import pytest

from app.exceptions import InvalidPasswordError
from app.services.user_service import UserService


@pytest.fixture
def service() -> UserService:
    """Create a UserService with mocked dependencies for policy testing."""
    repo = MagicMock()
    repo.find.return_value = None
    hasher = MagicMock()
    hasher.hash_password.return_value = "hashed"
    return UserService(repository=repo, hasher=hasher)


class TestPasswordPolicy:
    """Tests for password validation rules."""

    def test_password_minimum_length(self, service: UserService) -> None:
        """Password must be at least 8 characters."""
        with pytest.raises(InvalidPasswordError):
            service.register("user", "Ab1!")

    def test_password_requires_uppercase(self, service: UserService) -> None:
        """Password must contain at least one uppercase letter."""
        with pytest.raises(InvalidPasswordError):
            service.register("user", "lowercase1!")

    def test_password_requires_lowercase(self, service: UserService) -> None:
        """Password must contain at least one lowercase letter."""
        with pytest.raises(InvalidPasswordError):
            service.register("user", "UPPERCASE1!")

    def test_password_requires_digit(self, service: UserService) -> None:
        """Password must contain at least one digit."""
        with pytest.raises(InvalidPasswordError):
            service.register("user", "NoDigitHere!")

    def test_password_requires_symbol(self, service: UserService) -> None:
        """Password must contain at least one special character."""
        with pytest.raises(InvalidPasswordError):
            service.register("user", "NoSymbolHere1")

    def test_valid_password_accepted(self, service: UserService) -> None:
        """A password meeting all criteria should be accepted."""
        service.register("user", "Valid1!abc")
        service.hasher.hash_password.assert_called_once()

    def test_empty_password_rejected(self, service: UserService) -> None:
        """An empty password should be rejected."""
        with pytest.raises(InvalidPasswordError):
            service.register("user", "")

    def test_exactly_8_chars_valid(self, service: UserService) -> None:
        """Password of exactly 8 chars meeting all rules should work."""
        service.register("user", "Abcdef1!")
        service.hasher.hash_password.assert_called_once()

    def test_symbols_include_common_chars(self, service: UserService) -> None:
        """Various common symbols should be accepted."""
        for symbol in "!@#$%^&*":
            service.register("user", f"Passw0r{symbol}")

    def test_password_not_numeric_only(self, service: UserService) -> None:
        """Password that is only digits should be rejected."""
        with pytest.raises(InvalidPasswordError):
            service.register("user", "12345678")
