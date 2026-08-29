"""Unit tests for :class:`Base62ShortCodeGenerator`."""

from __future__ import annotations

import pytest

from apps.shortener.api.exceptions import InvalidShortCodeLengthError
from apps.shortener.api.services.short_code_generator import Base62ShortCodeGenerator


class TestBase62ShortCodeGenerator:
    def setup_method(self) -> None:
        self.generator = Base62ShortCodeGenerator()

    def test_default_length_is_seven(self):
        assert len(self.generator.generate()) == 7

    def test_respects_custom_length(self):
        assert len(self.generator.generate(length=12)) == 12

    def test_only_uses_alphanumeric_characters(self):
        code = self.generator.generate(length=100)
        assert code.isalnum()

    def test_rejects_non_positive_length(self):
        with pytest.raises(InvalidShortCodeLengthError):
            self.generator.generate(length=0)
        with pytest.raises(InvalidShortCodeLengthError):
            self.generator.generate(length=-3)

    def test_produces_high_entropy(self):
        # 62**7 keyspace: collisions across 200 draws are astronomically rare.
        codes = {self.generator.generate() for _ in range(200)}
        assert len(codes) >= 198
