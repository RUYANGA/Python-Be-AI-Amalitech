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
    """Registration and authentication for users."""

    def __init__(
        self,
        user_repo: IUserRepository,
        hasher: PasswordHasher,
        password_validator: PasswordValidator | None = None,
    ):
        self._user_repo = user_repo
        self._hasher = hasher
        self._password_validator = password_validator or PasswordValidator()

    def register(self, email: str, password: str, full_name: str | None = None) -> dict:
        """Create a new user after validating the email and password strength."""
        try:
            email = validate_email(email, check_deliverability=False).normalized
        except EmailNotValidError as exc:
            raise InvalidEmailError(str(exc)) from exc

        self._password_validator.validate(password)

        if self._user_repo.find_by_email(email):
            raise UserAlreadyExistsError(email)

        new_user = User(
            email=email,
            password_hash=self._hasher.hash(password),
            full_name=full_name,
        )
        user_id = self._user_repo.insert(new_user.to_doc())
        log.debug("Registered user %s (%s)", email, user_id)
        user = self._user_repo.find_by_id(user_id)
        assert user is not None
        return user

    def authenticate(self, email: str, password: str) -> dict:
        """Return the user doc if the email/password pair is valid."""
        user = self._user_repo.find_by_email(email)
        if not user or not self._hasher.verify(password, user["password_hash"]):
            raise InvalidCredentialsError()
        log.debug("User authenticated: %s", email)
        return user
