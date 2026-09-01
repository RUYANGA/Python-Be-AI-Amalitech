"""HTTP views for the analytics API endpoints."""

from apps.analytics.api.views.analytics_by_code_view import URLAnalyticsByCodeView
from apps.analytics.api.views.click_ingest_view import ClickIngestView

__all__ = ["ClickIngestView", "URLAnalyticsByCodeView"]
