"""Password hashing, verification, and strength validation."""

import re

import bcrypt

from social_media.exceptions import WeakPasswordError

_SYMBOL_PATTERN = re.compile(r"[^A-Za-z0-9]")


class PasswordHasher:
    """Single-responsibility hasher wrapping bcrypt."""

    def __init__(self, bcrypt_rounds: int = 12):
        self._rounds = bcrypt_rounds

    def hash(self, plain: str) -> str:
        """Hash a plaintext password with a fresh bcrypt salt."""
        salt = bcrypt.gensalt(rounds=self._rounds)
        return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify(plain: str, hashed: str) -> bool:
        """Check a plaintext password against an existing bcrypt hash."""
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


class PasswordValidator:
    """Enforces password strength: minimum length, upper, lower, number, symbol."""

    MIN_LENGTH = 8

    def validate(self, password: str) -> None:
        """Raise WeakPasswordError if the password fails the strength policy."""
        missing = []
        if len(password) < self.MIN_LENGTH:
            missing.append(f"at least {self.MIN_LENGTH} characters")
        if not any(c.isupper() for c in password):
            missing.append("an uppercase letter")
        if not any(c.islower() for c in password):
            missing.append("a lowercase letter")
        if not any(c.isdigit() for c in password):
            missing.append("a number")
        if not _SYMBOL_PATTERN.search(password):
            missing.append("a symbol")
        if missing:
            raise WeakPasswordError(f"Password must contain {', '.join(missing)}.")
