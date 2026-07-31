"""User-related business logic. Depends on repository abstractions."""

from datetime import UTC, datetime
from typing import Any

from social_media.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from social_media.models.postgres_entities import User
from social_media.repositories.base import IUserRepository
from social_media.utils.logger import get_logger
from social_media.utils.security import PasswordHasher, PasswordValidator
from social_media.utils.validators import UserValidator

log = get_logger(__name__)


class UserService:
    """Registration and authentication for users."""

    def __init__(
        self,
        user_repo: IUserRepository,
        hasher: PasswordHasher,
        password_validator: PasswordValidator | None = None,
        user_validator: UserValidator | None = None,
    ):
        self._user_repo = user_repo
        self._hasher = hasher
        self._password_validator = password_validator or PasswordValidator()
        self._user_validator = user_validator or UserValidator()

    def register(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
        bio: str | None = None,
    ) -> dict:
        """Create a new user after validating email, password, name, and bio."""
        email = self._user_validator.normalize_email(email)

        self._password_validator.validate(password)

        full_name = self._user_validator.validate_full_name(full_name) if full_name else None
        bio = self._user_validator.validate_bio(bio) if bio else None

        if self._user_repo.find_by_email(email):
            raise UserAlreadyExistsError(email)

        new_user = User(
            email=email,
            password_hash=self._hasher.hash(password),
            full_name=full_name,
            bio=bio,
        )
        user_id = self._user_repo.insert(new_user.to_doc())
        log.debug("Registered user %s (%s)", email, user_id)
        user = self._user_repo.find_by_id(user_id)
        assert user is not None
        return user

    def update_profile(
        self,
        user_id: Any,
        *,
        full_name: str | None = None,
        bio: str | None = None,
        email: str | None = None,
    ) -> dict:
        """Update profile details; None means keep the current value."""
        changes: dict = {}
        if full_name is not None:
            changes["full_name"] = self._user_validator.validate_full_name(full_name)
        if bio is not None:
            changes["bio"] = self._user_validator.validate_bio(bio)
        if email is not None:
            new_email = self._user_validator.normalize_email(email)
            existing = self._user_repo.find_by_email(new_email)
            if existing is not None and existing["id"] != user_id:
                raise UserAlreadyExistsError(new_email)
            changes["email"] = new_email
        if changes:
            changes["updated_at"] = datetime.now(UTC)
            self._user_repo.update(user_id, changes)
            log.debug("Profile updated for user %s", user_id)
        user = self._user_repo.find_by_id(user_id)
        assert user is not None
        return user

    def authenticate(self, email: str, password: str) -> dict:
        """Return the user doc if the email/password pair is valid."""
        email = self._user_validator.normalize_email_for_login(email)
        user = self._user_repo.find_by_email(email)
        if not user or not self._hasher.verify(password, user["password_hash"]):
            raise InvalidCredentialsError()
        log.debug("User authenticated: %s", email)
        return user
