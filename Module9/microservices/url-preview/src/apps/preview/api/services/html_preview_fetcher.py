"""Single-attempt HTML preview fetcher.

Fetches a URL once and parses its title/description/favicon out of the
HTML — no retry logic here at all (that's ``call_with_backoff``'s and
``PreviewService``'s job, same separation as ``URLShortenerService`` vs.
``DjangoURLRepository``). Any failure — a network error, a non-2xx
response, or a non-HTML ``Content-Type`` — raises ``PreviewFetchError``.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from django.conf import settings

from apps.preview.api.exceptions import PreviewFetchError
from apps.preview.api.interfaces.fetcher import IPreviewFetcher, PreviewResult

logger = logging.getLogger(__name__)


class HTMLPreviewFetcher(IPreviewFetcher):
    """Fetches a page's HTML and extracts title/description/favicon from it."""

    def fetch(self, url: str) -> PreviewResult:
        try:
            response = requests.get(
                url,
                timeout=settings.PREVIEW_FETCH_TIMEOUT,
                stream=True,
                headers={"User-Agent": "url-preview-service/1.0"},
            )
        except requests.RequestException as exc:
            logger.warning("html_preview_fetcher.request_failed url=%s error=%s", url, exc)
            raise PreviewFetchError(f"Request to '{url}' failed: {exc}") from exc

        try:
            if not (200 <= response.status_code < 300):
                raise PreviewFetchError(f"'{url}' returned non-2xx status {response.status_code}.")

            content_type = response.headers.get("Content-Type", "")
            if "html" not in content_type.lower():
                raise PreviewFetchError(f"'{url}' returned non-HTML content-type '{content_type}'.")

            html = self._read_capped_body(response, url)
        finally:
            response.close()

        soup = BeautifulSoup(html, "html.parser")
        return PreviewResult(
            title=self._extract_title(soup),
            description=self._extract_description(soup),
            favicon_url=self._extract_favicon(soup, url),
        )

    # ------------------------------------------------------------------
    # Body reading
    # ------------------------------------------------------------------

    def _read_capped_body(self, response: requests.Response, url: str) -> str:
        """Read the response body, streamed, capped at ``PREVIEW_MAX_BODY_BYTES``."""
        max_bytes = settings.PREVIEW_MAX_BODY_BYTES
        chunks: list[bytes] = []
        total = 0
        try:
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                chunks.append(chunk)
                total += len(chunk)
                if total >= max_bytes:
                    break
        except requests.RequestException as exc:
            logger.warning("html_preview_fetcher.body_read_failed url=%s error=%s", url, exc)
            raise PreviewFetchError(f"Reading body of '{url}' failed: {exc}") from exc

        body = b"".join(chunks)[:max_bytes]
        encoding = response.encoding or "utf-8"
        return body.decode(encoding, errors="replace")

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def _extract_title(self, soup: BeautifulSoup) -> str:
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        return ""

    def _extract_description(self, soup: BeautifulSoup) -> str:
        og_description = soup.find("meta", attrs={"property": "og:description"})
        if og_description and og_description.get("content"):
            return str(og_description["content"]).strip()

        description = soup.find("meta", attrs={"name": "description"})
        if description and description.get("content"):
            return str(description["content"]).strip()

        return ""

    def _extract_favicon(self, soup: BeautifulSoup, url: str) -> str:
        for rel in ("icon", "shortcut icon"):
            link = soup.find("link", attrs={"rel": rel})
            if link and link.get("href"):
                return urljoin(url, str(link["href"]))

        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
