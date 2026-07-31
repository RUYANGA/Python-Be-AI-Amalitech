"""Normalization and validation helpers for user profile input."""

import re

from email_validator import EmailNotValidError, validate_email

from social_media.exceptions import InvalidBioError, InvalidEmailError, InvalidFullNameError

MIN_FULL_NAME_LENGTH = 5
MAX_FULL_NAME_LENGTH = 100
MAX_BIO_LENGTH = 160

_NAME_PATTERN = re.compile(r"^[^\W\d_]+(?: [^\W\d_]+)*$")


class UserValidator:
    """Validate and normalize email, full name, and bio before persistence."""

    def normalize_email(self, email: str) -> str:
        """Validate an email address and return it lowercased."""
        try:
            normalized = validate_email(email.strip(), check_deliverability=False).normalized
            return normalized.lower()
        except EmailNotValidError as exc:
            raise InvalidEmailError(str(exc)) from exc

    def normalize_email_for_login(self, email: str) -> str:
        """Lowercase and strip an email without raising validation errors."""
        return email.strip().lower()

    def validate_full_name(self, full_name: str) -> str:
        """Validate a full name and return it trimmed."""
        name = full_name.strip()
        if len(name) < MIN_FULL_NAME_LENGTH:
            raise InvalidFullNameError(
                f"Full name must be at least {MIN_FULL_NAME_LENGTH} characters."
            )
        if len(name) > MAX_FULL_NAME_LENGTH:
            raise InvalidFullNameError(
                f"Full name must be at most {MAX_FULL_NAME_LENGTH} characters."
            )
        if not _NAME_PATTERN.match(name):
            raise InvalidFullNameError(
                "Full name may contain only letters and spaces (space in the middle)."
            )
        return name

    def validate_bio(self, bio: str) -> str:
        """Validate a bio and return it trimmed."""
        text = bio.strip()
        if len(text) > MAX_BIO_LENGTH:
            raise InvalidBioError(f"Bio must be at most {MAX_BIO_LENGTH} characters.")
        return text
