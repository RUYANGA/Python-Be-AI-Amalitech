"""Service contracts (abstract base classes) for the url-preview API."""

from apps.preview.api.interfaces.fetcher import IPreviewFetcher, PreviewResult

__all__ = ["IPreviewFetcher", "PreviewResult"]
