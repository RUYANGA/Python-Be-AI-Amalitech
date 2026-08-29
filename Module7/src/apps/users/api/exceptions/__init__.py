"""Domain exceptions for the users (auth) API."""

from apps.users.api.exceptions.authentication_error import AuthenticationError
from apps.users.api.exceptions.base import AuthError
from apps.users.api.exceptions.email_taken_error import EmailTakenError
from apps.users.api.exceptions.inactive_account_error import InactiveAccountError
from apps.users.api.exceptions.too_many_login_attempts_error import TooManyLoginAttemptsError
from apps.users.api.exceptions.username_taken_error import UsernameTakenError

__all__ = [
    "AuthError",
    "AuthenticationError",
    "EmailTakenError",
    "InactiveAccountError",
    "TooManyLoginAttemptsError",
    "UsernameTakenError",
]
