"""Unit tests for ``HTMLPreviewFetcher``.

``requests.get`` is mocked at the module it's imported into (same style
as ``test_url_ownership_client.py``/``test_click_publisher.py``), never
hitting the network. The mocked response exposes ``iter_content`` (what
the fetcher actually reads, streamed and capped) rather than ``.text``.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import requests

from apps.preview.api.exceptions import PreviewFetchError
from apps.preview.api.services.html_preview_fetcher import HTMLPreviewFetcher

_SAMPLE_HTML = b"""
<html>
<head>
    <title>  Example Page  </title>
    <meta property="og:description" content="An example page for tests.">
    <meta name="description" content="Fallback description, should be ignored.">
    <link rel="icon" href="/static/favicon.png">
</head>
<body></body>
</html>
"""


def _mock_response(
    *,
    status_code: int = 200,
    content_type: str = "text/html; charset=utf-8",
    body: bytes = _SAMPLE_HTML,
) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.headers = {"Content-Type": content_type}
    response.iter_content.return_value = [body]
    response.encoding = "utf-8"
    return response


class TestFetch:
    def test_extracts_title_description_and_favicon(self):
        with patch(
            "apps.preview.api.services.html_preview_fetcher.requests.get",
            return_value=_mock_response(),
        ):
            result = HTMLPreviewFetcher().fetch("https://example.com/page")

        assert result.title == "Example Page"
        assert result.description == "An example page for tests."
        assert result.favicon_url == "https://example.com/static/favicon.png"

    def test_missing_meta_description_falls_back_to_empty_string(self):
        html = b"<html><head><title>No Description</title></head></html>"
        with patch(
            "apps.preview.api.services.html_preview_fetcher.requests.get",
            return_value=_mock_response(body=html),
        ):
            result = HTMLPreviewFetcher().fetch("https://example.com/page")

        assert result.description == ""

    def test_uses_the_name_description_meta_when_no_og_description(self):
        html = (
            b"<html><head><title>T</title>"
            b'<meta name="description" content="Plain description.">'
            b"</head></html>"
        )
        with patch(
            "apps.preview.api.services.html_preview_fetcher.requests.get",
            return_value=_mock_response(body=html),
        ):
            result = HTMLPreviewFetcher().fetch("https://example.com/page")

        assert result.description == "Plain description."

    def test_missing_favicon_link_falls_back_to_origin_favicon_ico(self):
        html = b"<html><head><title>No Favicon</title></head></html>"
        with patch(
            "apps.preview.api.services.html_preview_fetcher.requests.get",
            return_value=_mock_response(body=html),
        ):
            result = HTMLPreviewFetcher().fetch("https://example.com/page")

        assert result.favicon_url == "https://example.com/favicon.ico"

    def test_non_html_content_type_raises_preview_fetch_error(self):
        with (
            patch(
                "apps.preview.api.services.html_preview_fetcher.requests.get",
                return_value=_mock_response(content_type="application/json"),
            ),
            pytest.raises(PreviewFetchError),
        ):
            HTMLPreviewFetcher().fetch("https://example.com/data.json")

    def test_non_2xx_status_raises_preview_fetch_error(self):
        with (
            patch(
                "apps.preview.api.services.html_preview_fetcher.requests.get",
                return_value=_mock_response(status_code=404),
            ),
            pytest.raises(PreviewFetchError),
        ):
            HTMLPreviewFetcher().fetch("https://example.com/missing")

    def test_connection_error_raises_preview_fetch_error(self):
        with (
            patch(
                "apps.preview.api.services.html_preview_fetcher.requests.get",
                side_effect=requests.ConnectionError("down"),
            ),
            pytest.raises(PreviewFetchError),
        ):
            HTMLPreviewFetcher().fetch("https://unreachable.example.com")
