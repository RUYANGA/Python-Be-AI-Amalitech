from abc import ABC, abstractmethod


class LoginRateLimiter(ABC):
    """Contract for throttling repeated failed login attempts (Dependency Inversion)."""

    @abstractmethod
    def check(self, identifier: str) -> None:
        """Raise ``TooManyLoginAttemptsError`` if ``identifier`` is currently blocked."""

    @abstractmethod
    def register_failure(self, identifier: str) -> int:
        """Record a failed attempt, blocking the identifier once the threshold is hit.

        Returns the number of attempts remaining before the identifier is
        blocked (``0`` once this failure has triggered the block).
        """

    @abstractmethod
    def reset(self, identifier: str) -> None:
        """Clear attempt history after a successful login."""
