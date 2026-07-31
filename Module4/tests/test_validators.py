"""Tests for UserValidator."""

import pytest

from social_media.exceptions import (
    InvalidBioError,
    InvalidEmailError,
    InvalidFullNameError,
)
from social_media.utils.validators import UserValidator


class TestNormalizeEmail:
    def test_lowercases_email(self):
        assert UserValidator().normalize_email("Alice@Example.COM") == "alice@example.com"

    def test_strips_whitespace(self):
        assert UserValidator().normalize_email("  bob@example.com  ") == "bob@example.com"

    def test_rejects_invalid_email(self):
        with pytest.raises(InvalidEmailError):
            UserValidator().normalize_email("not-an-email")

    def test_normalize_email_for_login(self):
        assert UserValidator().normalize_email_for_login("  Alice@Example.COM ") == (
            "alice@example.com"
        )


class TestValidateFullName:
    def test_accepts_valid_name(self):
        assert UserValidator().validate_full_name("Alice Johnson") == "Alice Johnson"

    def test_trims_name(self):
        assert UserValidator().validate_full_name("  Alice Johnson  ") == "Alice Johnson"

    def test_rejects_hyphen_and_apostrophe(self):
        with pytest.raises(InvalidFullNameError):
            UserValidator().validate_full_name("Jean-Pierre O'Neil")

    def test_rejects_consecutive_spaces(self):
        with pytest.raises(InvalidFullNameError):
            UserValidator().validate_full_name("Alice  Johnson")

    def test_rejects_too_short(self):
        with pytest.raises(InvalidFullNameError, match="at least 5"):
            UserValidator().validate_full_name("Bob")

    def test_rejects_too_long(self):
        with pytest.raises(InvalidFullNameError, match="at most 100"):
            UserValidator().validate_full_name("A" * 101)

    def test_rejects_invalid_characters(self):
        with pytest.raises(InvalidFullNameError, match="letters"):
            UserValidator().validate_full_name("Alice123!")


class TestValidateBio:
    def test_accepts_short_bio(self):
        assert UserValidator().validate_bio("Hello world") == "Hello world"

    def test_trims_bio(self):
        assert UserValidator().validate_bio("  Hi  ") == "Hi"

    def test_rejects_too_long(self):
        with pytest.raises(InvalidBioError, match="at most 160"):
            UserValidator().validate_bio("x" * 161)
