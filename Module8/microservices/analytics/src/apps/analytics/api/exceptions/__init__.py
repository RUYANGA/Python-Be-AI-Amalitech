"""Domain exceptions for the analytics API."""

from apps.analytics.api.exceptions.base import AnalyticsError
from apps.analytics.api.exceptions.repository_error import RepositoryError
from apps.analytics.api.exceptions.url_not_accessible_error import URLNotAccessibleError

__all__ = ["AnalyticsError", "RepositoryError", "URLNotAccessibleError"]
