"""Unit tests for the SQLAlchemy shortener models."""

from database.shortener.models import URLModel


class TestURLModel:
    def test_tablename_matches_shortener_schema(self):
        assert URLModel.__tablename__ == "urls"

    def test_short_code_unique_and_not_null(self):
        col = URLModel.__table__.columns["short_code"]
        assert col.unique is True
        assert col.nullable is False

    def test_original_url_is_not_null(self):
        col = URLModel.__table__.columns["original_url"]
        assert col.nullable is False

    def test_owner_optional(self):
        col = URLModel.__table__.columns["owner_id"]
        assert col.nullable is True

    def test_default_fields_present(self):
        cols = URLModel.__table__.columns
        for name in ("click_count", "is_active", "created_at", "updated_at"):
            assert name in cols
