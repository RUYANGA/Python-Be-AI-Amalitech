"""Tests for custom exception behavior."""

import pytest

from app.exceptions import (
    AuthError,
    InvalidCredentialsError,
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserNotFoundError,
)


class TestExceptions:
    """Tests for exception hierarchy and messages."""

    def test_auth_error_is_base_exception(self) -> None:
        """All custom exceptions should inherit from AuthError."""
        assert issubclass(UserAlreadyExistsError, AuthError)
        assert issubclass(InvalidPasswordError, AuthError)
        assert issubclass(UserNotFoundError, AuthError)
        assert issubclass(InvalidCredentialsError, AuthError)

    def test_user_already_exists_message(self) -> None:
        """UserAlreadyExistsError should include the username."""
        exc = UserAlreadyExistsError("alice")
        assert "alice" in str(exc)
        assert exc.username == "alice"

    def test_user_not_found_message(self) -> None:
        """UserNotFoundError should include the username."""
        exc = UserNotFoundError("bob")
        assert "bob" in str(exc)
        assert exc.username == "bob"

    def test_invalid_password_default_message(self) -> None:
        """InvalidPasswordError should have a default message."""
        exc = InvalidPasswordError()
        assert "Password" in str(exc)

    def test_invalid_password_custom_message(self) -> None:
        """InvalidPasswordError should accept a custom message."""
        exc = InvalidPasswordError("Custom error")
        assert str(exc) == "Custom error"

    def test_invalid_credentials_message(self) -> None:
        """InvalidCredentialsError should have a generic message."""
        exc = InvalidCredentialsError()
        assert "Invalid" in str(exc)

    def test_all_exceptions_are_raised(self) -> None:
        """All exceptions should be raisable."""
        with pytest.raises(AuthError):
            raise AuthError("base")
        with pytest.raises(UserAlreadyExistsError):
            raise UserAlreadyExistsError("u")
        with pytest.raises(UserNotFoundError):
            raise UserNotFoundError("u")
        with pytest.raises(InvalidPasswordError):
            raise InvalidPasswordError()
        with pytest.raises(InvalidCredentialsError):
            raise InvalidCredentialsError()
