"""``GET /health/`` — liveness/readiness probe for orchestrators and monitoring.

Checks the two dependencies this service's hot-path requests actually
need: the database (a real round-trip query, not just a connection
object) and Redis (backs ``CachedClickAnalyticsRepository``). No authentication —
this is called by container healthchecks and monitoring, never through
the gateway's ``auth_request``.
"""

from __future__ import annotations

import logging

from django.db import connections
from django.db.utils import Error as DatabaseError
from django.http import JsonResponse

from apps.analytics.api.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)


def health_check(_request):
    """Return ``200`` with a per-dependency breakdown, or ``503`` if any check fails."""
    checks = {"database": _check_database(), "redis": _check_redis()}
    healthy = all(checks.values())
    if not healthy:
        logger.error("health_check.failed checks=%s", checks)
    return JsonResponse(
        {"status": "ok" if healthy else "unhealthy", "checks": checks},
        status=200 if healthy else 503,
    )


def _check_database() -> bool:
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except DatabaseError:
        logger.error("health_check.database_unreachable", exc_info=True)
        return False


def _check_redis() -> bool:
    try:
        return get_redis_client().ping()
    except Exception:
        logger.error("health_check.redis_unreachable", exc_info=True)
        return False
