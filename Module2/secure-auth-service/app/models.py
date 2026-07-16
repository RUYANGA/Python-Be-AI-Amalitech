"""Data models for the authentication service."""

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    """Represents a user in the system.

    Attributes:
        username: The unique identifier for the user.
        password_hash: The bcrypt-hashed password.
    """

    username: str
    password_hash: str
