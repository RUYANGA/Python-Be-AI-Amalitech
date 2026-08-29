"""Unit tests for the Django shortener models."""

from apps.shortener.models import URL, Click, Tag


class TestURLModel:
    def test_tablename_matches_shortener_schema(self):
        assert URL._meta.db_table == "urls"

    def test_short_code_unique_and_not_null(self):
        field = URL._meta.get_field("short_code")
        assert field.unique is True
        assert field.null is False

    def test_original_url_is_not_null(self):
        field = URL._meta.get_field("original_url")
        assert field.null is False

    def test_owner_optional(self):
        field = URL._meta.get_field("owner")
        assert field.null is True
        assert field.blank is True

    def test_default_fields_present(self):
        names = {f.name for f in URL._meta.get_fields()}
        for name in ("click_count", "is_active", "created_at", "updated_at", "title", "tags"):
            assert name in names


class TestClickModel:
    def test_tablename_matches_shortener_schema(self):
        assert Click._meta.db_table == "clicks"

    def test_city_field_present(self):
        assert Click._meta.get_field("city").max_length == 100

    def test_user_agent_field_present(self):
        assert Click._meta.get_field("user_agent").blank is True


class TestTagModel:
    def test_tablename_matches_shortener_schema(self):
        assert Tag._meta.db_table == "tags"

    def test_name_unique(self):
        assert Tag._meta.get_field("name").unique is True
