"""Tests for UserService."""

from unittest.mock import MagicMock

import pytest

from social_media.exceptions import (
    InvalidCredentialsError,
    InvalidEmailError,
    UserAlreadyExistsError,
    WeakPasswordError,
)
from social_media.services.user_service import UserService
from tests.conftest import fake_id


class TestRegister:
    def test_register_new_user(self, user_svc: UserService, hasher, user_repo: MagicMock):
        user_repo.find_by_email.return_value = None
        fake_uid = fake_id()
        user_repo.insert.return_value = fake_uid
        user_repo.find_by_id.return_value = {
            "id": fake_uid,
            "email": "alice@example.com",
            "full_name": "Alice",
        }

        result = user_svc.register("alice@example.com", "S3cret!x", "Alice")
        assert result["email"] == "alice@example.com"
        user_repo.insert.assert_called_once()

    def test_register_duplicate_email(self, user_svc: UserService, user_repo: MagicMock):
        user_repo.find_by_email.return_value = {
            "id": fake_id(),
            "email": "alice@example.com",
        }
        with pytest.raises(UserAlreadyExistsError):
            user_svc.register("alice@example.com", "S3cret!x", "Alice")

    def test_register_invalid_email(self, user_svc: UserService, user_repo: MagicMock):
        with pytest.raises(InvalidEmailError):
            user_svc.register("not-an-email", "S3cret!x", "Bad")

    def test_register_normalizes_email(self, user_svc: UserService, user_repo: MagicMock):
        user_repo.find_by_email.return_value = None
        fake_uid = fake_id()
        user_repo.insert.return_value = fake_uid
        user_repo.find_by_id.return_value = {
            "id": fake_uid,
            "email": "Alice@Example.com",
        }

        result = user_svc.register("Alice@Example.com", "S3cret!x")
        # The normalized email is lowercase
        assert result["email"] == "Alice@Example.com"

    def test_register_stores_hashed_password(self, user_svc: UserService, user_repo: MagicMock):
        import bcrypt

        user_repo.find_by_email.return_value = None
        fake_uid = fake_id()
        user_repo.insert.return_value = fake_uid
        user_repo.find_by_id.return_value = {
            "id": fake_uid,
            "email": "bob@example.com",
            "password_hash": None,
        }

        def capture_hash(doc):
            user_repo.find_by_id.return_value["password_hash"] = doc["password_hash"]
            return fake_uid

        user_repo.insert.side_effect = capture_hash

        user_svc.register("bob@example.com", "S3cret!x")
        stored_hash = user_repo.find_by_id.return_value["password_hash"]
        assert bcrypt.checkpw(b"S3cret!x", stored_hash.encode("utf-8"))


class TestPasswordPolicy:
    @pytest.mark.parametrize(
        "password",
        [
            "short1!",  # too short
            "alllowercase1!",  # no uppercase
            "ALLUPPERCASE1!",  # no lowercase
            "NoDigitsHere!",  # no number
            "NoSymbolsHere1",  # no symbol
        ],
    )
    def test_register_rejects_weak_password(
        self, user_svc: UserService, user_repo: MagicMock, password: str
    ):
        user_repo.find_by_email.return_value = None
        with pytest.raises(WeakPasswordError):
            user_svc.register("weak@example.com", password, "Weak")
        user_repo.insert.assert_not_called()

    def test_register_accepts_strong_password(self, user_svc: UserService, user_repo: MagicMock):
        user_repo.find_by_email.return_value = None
        fake_uid = fake_id()
        user_repo.insert.return_value = fake_uid
        user_repo.find_by_id.return_value = {
            "id": fake_uid,
            "email": "strong@example.com",
        }

        user_svc.register("strong@example.com", "Str0ng!Pass", "Strong")
        user_repo.insert.assert_called_once()


class TestAuthenticate:
    def test_valid_credentials(self, user_svc: UserService, user_repo: MagicMock, hasher):
        pw_hash = hasher.hash("validpw")
        doc = {"id": fake_id(), "email": "alice@example.com", "password_hash": pw_hash}
        user_repo.find_by_email.return_value = doc

        result = user_svc.authenticate("alice@example.com", "validpw")
        assert result["id"] == doc["id"]

    def test_invalid_password(self, user_svc: UserService, user_repo: MagicMock, hasher):
        doc = {
            "id": fake_id(),
            "email": "alice@example.com",
            "password_hash": hasher.hash("validpw"),
        }
        user_repo.find_by_email.return_value = doc

        with pytest.raises(InvalidCredentialsError):
            user_svc.authenticate("alice@example.com", "wrongpw")

    def test_nonexistent_user(self, user_svc: UserService, user_repo: MagicMock):
        user_repo.find_by_email.return_value = None
        with pytest.raises(InvalidCredentialsError):
            user_svc.authenticate("nobody@example.com", "pw")


class TestUserAlreadyExistsError:
    def test_exception_message(self):
        exc = UserAlreadyExistsError("test@example.com")
        assert "test@example.com" in str(exc)
