"""User-related business logic. Depends on repository abstractions."""

from email_validator import EmailNotValidError, validate_email

from social_media.exceptions import (
    InvalidCredentialsError,
    InvalidEmailError,
    UserAlreadyExistsError,
)
from social_media.models.postgres_entities import User
from social_media.repositories.base import IUserRepository
from social_media.utils.logger import get_logger
from social_media.utils.security import PasswordHasher, PasswordValidator

log = get_logger(__name__)


class UserService:
    def __init__(
        self,
        user_repo: IUserRepository,
        hasher: PasswordHasher,
        password_validator: PasswordValidator | None = None,
    ):
        self._users = user_repo
        self._hasher = hasher
        self._password_validator = password_validator or PasswordValidator()

    def register(self, email: str, password: str, full_name: str | None = None) -> dict:
        try:
            email = validate_email(email, check_deliverability=False).normalized
        except EmailNotValidError as e:
            raise InvalidEmailError(str(e)) from e

        self._password_validator.validate(password)

        if self._users.find_by_email(email):
            raise UserAlreadyExistsError(email)

        user = User(
            email=email,
            password_hash=self._hasher.hash(password),
            full_name=full_name,
        )
        user_id = self._users.insert(user.to_doc())
        log.debug("Registered user %s (%s)", email, user_id)
        doc = self._users.find_by_id(user_id)
        assert doc is not None
        return doc

    def authenticate(self, email: str, password: str) -> dict:
        doc = self._users.find_by_email(email)
        if not doc or not self._hasher.verify(password, doc["password_hash"]):
            raise InvalidCredentialsError()
        log.debug("User authenticated: %s", email)
        return doc
