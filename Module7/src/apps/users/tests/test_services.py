"""Tests for the users API service layer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from apps.users.api.exceptions import (
    AuthenticationError,
    InactiveAccountError,
    TooManyLoginAttemptsError,
)
from apps.users.api.services import (
    JWTTokenService,
    RedisLoginRateLimiter,
    UserAuthService,
)

pytestmark = pytest.mark.django_db


class FakeRedisClient:
    """Minimal in-memory stand-in for ``RedisClient``, incl. atomic ``incr``.

    ``ttl`` reports whatever value was passed to ``set``/``incr`` — it does
    not decay with real time, so tests that need a countdown to actually
    shrink set the key's ttl directly rather than sleeping.
    """

    def __init__(self) -> None:
        self._store: dict[str, object] = {}
        self._ttls: dict[str, int] = {}

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value, ttl=None):
        self._store[key] = value
        if ttl is not None:
            self._ttls[key] = ttl
        return True

    def delete(self, key):
        self._ttls.pop(key, None)
        return bool(self._store.pop(key, None))

    def exists(self, key):
        return key in self._store

    def incr(self, key, ttl=None):
        value = self._store.get(key, 0) + 1
        self._store[key] = value
        if value == 1 and ttl is not None:
            self._ttls[key] = ttl
        return value

    def ttl(self, key):
        return self._ttls.get(key, 0) if key in self._store else 0


class TestUserAuthServiceRegister:
    def test_creates_and_returns_user(self):
        service = UserAuthService()
        user = service.register(
            {
                "username": "newuser",
                "email": "new@example.com",
                "password": "StrongPass123",
            }
        )
        assert user.pk is not None
        assert user.check_password("StrongPass123")


class TestUserAuthServiceLogin:
    def setup_method(self) -> None:
        self.token_service = MagicMock()
        self.token_service.generate_tokens.return_value = {
            "refresh": "refresh-token",
            "access": "access-token",
        }
        self.service = UserAuthService(token_service=self.token_service)

    def test_returns_user_and_tokens_on_success(self, user):
        result = self.service.login("alice", "testpass123")
        assert result["user"] == user
        assert result["tokens"] == {"refresh": "refresh-token", "access": "access-token"}
        self.token_service.generate_tokens.assert_called_once_with(user)

    def test_raises_for_unknown_username(self):
        with pytest.raises(AuthenticationError):
            self.service.login("nobody", "whatever")

    def test_raises_for_wrong_password(self, user):
        with pytest.raises(AuthenticationError):
            self.service.login("alice", "wrongpassword")

    def test_wrong_password_reports_remaining_attempts(self, user):
        with pytest.raises(AuthenticationError) as exc_info:
            self.service.login("alice", "wrongpassword")

        assert exc_info.value.remaining_attempts == RedisLoginRateLimiter.MAX_ATTEMPTS - 1

    def test_raises_for_inactive_account(self, inactive_user):
        with pytest.raises(InactiveAccountError):
            self.service.login("bob", "testpass123")


class TestUserAuthServiceLoginRateLimiting:
    def setup_method(self) -> None:
        self.token_service = MagicMock()
        self.token_service.generate_tokens.return_value = {
            "refresh": "refresh-token",
            "access": "access-token",
        }
        self.rate_limiter = RedisLoginRateLimiter(redis_client=FakeRedisClient())
        self.service = UserAuthService(
            token_service=self.token_service, rate_limiter=self.rate_limiter
        )

    def test_blocks_after_max_attempts_even_with_correct_password(self, user):
        for _ in range(RedisLoginRateLimiter.MAX_ATTEMPTS):
            with pytest.raises(AuthenticationError):
                self.service.login("alice", "wrongpassword")

        with pytest.raises(TooManyLoginAttemptsError) as exc_info:
            self.service.login("alice", "testpass123")
        assert exc_info.value.retry_after_seconds == RedisLoginRateLimiter.BLOCK_SECONDS

    def test_remaining_attempts_counts_down_to_zero(self, user):
        expected = list(range(RedisLoginRateLimiter.MAX_ATTEMPTS - 1, -1, -1))
        actual = []
        for _ in range(RedisLoginRateLimiter.MAX_ATTEMPTS):
            with pytest.raises(AuthenticationError) as exc_info:
                self.service.login("alice", "wrongpassword")
            actual.append(exc_info.value.remaining_attempts)

        assert actual == expected

    def test_does_not_block_below_the_threshold(self, user):
        for _ in range(RedisLoginRateLimiter.MAX_ATTEMPTS - 1):
            with pytest.raises(AuthenticationError):
                self.service.login("alice", "wrongpassword")

        result = self.service.login("alice", "testpass123")
        assert result["user"] == user

    def test_successful_login_resets_the_failure_counter(self, user):
        for _ in range(RedisLoginRateLimiter.MAX_ATTEMPTS - 1):
            with pytest.raises(AuthenticationError):
                self.service.login("alice", "wrongpassword")

        self.service.login("alice", "testpass123")

        for _ in range(RedisLoginRateLimiter.MAX_ATTEMPTS - 1):
            with pytest.raises(AuthenticationError):
                self.service.login("alice", "wrongpassword")

        result = self.service.login("alice", "testpass123")
        assert result["user"] == user

    def test_rate_limiting_is_scoped_per_username(self, user, inactive_user):
        for _ in range(RedisLoginRateLimiter.MAX_ATTEMPTS):
            with pytest.raises(AuthenticationError):
                self.service.login("alice", "wrongpassword")

        with pytest.raises(InactiveAccountError):
            self.service.login("bob", "testpass123")


class TestRedisLoginRateLimiter:
    def setup_method(self) -> None:
        self.redis = FakeRedisClient()
        self.limiter = RedisLoginRateLimiter(redis_client=self.redis)

    def test_check_allows_when_not_blocked(self):
        self.limiter.check("alice")

    def test_blocks_once_max_attempts_is_reached(self):
        for _ in range(RedisLoginRateLimiter.MAX_ATTEMPTS):
            self.limiter.register_failure("alice")

        with pytest.raises(TooManyLoginAttemptsError):
            self.limiter.check("alice")

    def test_does_not_block_below_max_attempts(self):
        for _ in range(RedisLoginRateLimiter.MAX_ATTEMPTS - 1):
            self.limiter.register_failure("alice")

        self.limiter.check("alice")

    def test_register_failure_returns_remaining_attempts(self):
        remaining = self.limiter.register_failure("alice")
        assert remaining == RedisLoginRateLimiter.MAX_ATTEMPTS - 1

    def test_register_failure_returns_zero_once_the_threshold_is_hit(self):
        for _ in range(RedisLoginRateLimiter.MAX_ATTEMPTS - 1):
            self.limiter.register_failure("alice")

        assert self.limiter.register_failure("alice") == 0

    def test_reset_clears_the_failure_counter(self):
        self.limiter.register_failure("alice")

        self.limiter.reset("alice")

        assert self.redis.get(RedisLoginRateLimiter._attempts_key("alice")) is None

    def test_check_reports_the_live_ttl_not_the_full_block_duration(self):
        """``retry_after_seconds`` must count down as the block ages, not stay
        pinned at ``BLOCK_SECONDS`` for the whole 30 minutes."""
        self.redis.set(RedisLoginRateLimiter._blocked_key("alice"), True, ttl=42)

        with pytest.raises(TooManyLoginAttemptsError) as exc_info:
            self.limiter.check("alice")

        assert exc_info.value.retry_after_seconds == 42

    def test_defaults_to_the_shared_redis_client(self):
        limiter = RedisLoginRateLimiter()
        assert limiter._cache is not None


class TestUserAuthServiceLogout:
    def test_delegates_to_token_service(self):
        token_service = MagicMock()
        service = UserAuthService(token_service=token_service)

        service.logout("some-refresh-token")

        token_service.blacklist_refresh.assert_called_once_with("some-refresh-token")

    def test_defaults_to_jwt_token_service(self):
        service = UserAuthService()
        assert isinstance(service.token_service, JWTTokenService)


class TestJWTTokenService:
    def setup_method(self) -> None:
        self.service = JWTTokenService()

    def test_generate_tokens_returns_refresh_and_access(self, user):
        tokens = self.service.generate_tokens(user)
        assert set(tokens.keys()) == {"refresh", "access"}
        assert tokens["refresh"]
        assert tokens["access"]

    def test_blacklist_refresh_invalidates_token(self, user):
        tokens = self.service.generate_tokens(user)

        self.service.blacklist_refresh(tokens["refresh"])

        assert BlacklistedToken.objects.count() == 1
