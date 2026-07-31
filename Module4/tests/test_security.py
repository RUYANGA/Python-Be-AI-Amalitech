"""Tests for PasswordHasher and PasswordValidator."""

import pytest

from social_media.exceptions import WeakPasswordError
from social_media.utils.security import PasswordHasher, PasswordValidator


class TestPasswordHasher:
    def test_hash_and_verify_roundtrip(self):
        hasher = PasswordHasher()
        hashed = hasher.hash("S3cret!x")
        assert hasher.verify("S3cret!x", hashed) is True

    def test_verify_rejects_wrong_password(self):
        hasher = PasswordHasher()
        hashed = hasher.hash("S3cret!x")
        assert hasher.verify("wrong", hashed) is False


class TestPasswordValidator:
    def test_accepts_strong_password(self):
        PasswordValidator().validate("Str0ng!Pass")  # should not raise

    def test_rejects_too_short(self):
        with pytest.raises(WeakPasswordError, match="at least 8 characters"):
            PasswordValidator().validate("Sh0rt!")

    def test_rejects_missing_uppercase(self):
        with pytest.raises(WeakPasswordError, match="uppercase"):
            PasswordValidator().validate("lower1!ng")

    def test_rejects_missing_lowercase(self):
        with pytest.raises(WeakPasswordError, match="lowercase"):
            PasswordValidator().validate("UPPER1!NG")

    def test_rejects_missing_digit(self):
        with pytest.raises(WeakPasswordError, match="number"):
            PasswordValidator().validate("NoDigits!")

    def test_rejects_missing_symbol(self):
        with pytest.raises(WeakPasswordError, match="symbol"):
            PasswordValidator().validate("NoSymbols1")

    def test_reports_all_missing_criteria_at_once(self):
        with pytest.raises(WeakPasswordError) as exc_info:
            PasswordValidator().validate("weak")
        message = str(exc_info.value)
        assert "8 characters" in message
        assert "uppercase" in message
        assert "number" in message
        assert "symbol" in message
