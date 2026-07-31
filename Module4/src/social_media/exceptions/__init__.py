"""Custom exceptions for the social media application."""


class UserAlreadyExistsError(Exception):
    """Raised when trying to register a user with an existing email."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials do not match."""


class SettingsError(Exception):
    """Raised when required environment configuration is missing or invalid."""


class InvalidEmailError(Exception):
    """Raised when an email address fails validation."""


class WeakPasswordError(Exception):
    """Raised when a password fails the strength policy."""


class InvalidFullNameError(Exception):
    """Raised when a full name fails validation."""


class InvalidBioError(Exception):
    """Raised when a bio fails validation."""


class EmptyPostContentError(Exception):
    """Raised when post content is empty or whitespace-only."""


class EmptyCommentError(Exception):
    """Raised when comment content is empty or whitespace-only."""


class SelfFollowError(Exception):
    """Raised when a user tries to follow themselves."""
