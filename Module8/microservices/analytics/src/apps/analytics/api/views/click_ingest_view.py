"""REST endpoint that ingests click events from the shortener service.

Implements ``POST /api/v1/internal/clicks/`` — the service-to-service
endpoint that replaced the Kafka ``clicks`` topic and its
``consume_clicks`` consumer. The shortener service calls this once per
redirect/resolve, on a background thread, so a slow or unreachable
analytics service can never make those hot-path endpoints slow or fail.

The write-behind pattern continues past this endpoint: the view itself
never touches the database or does the geo lookup — it just validates
the payload and hands it to Celery (``apps.analytics.tasks.track_click_task``),
so a burst of clicks can never back up as slow database writes here
either. Authenticated with a shared static secret in the
``X-Internal-Token`` header, never a user's JWT.
"""

from __future__ import annotations

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.api.permissions import HasInternalServiceToken
from apps.analytics.tasks import track_click_task

logger = logging.getLogger(__name__)


class ClickIngestView(APIView):
    """Enqueues a single click event reported by the shortener service."""

    permission_classes = [HasInternalServiceToken]

    @extend_schema(exclude=True)
    def post(self, request: Request) -> Response:
        short_code = request.data.get("short_code", "")
        if not short_code:
            logger.warning("click_ingest.dropped_malformed_entry data=%s", request.data)
            return Response({"detail": "short_code is required."}, status=400)

        try:
            track_click_task.delay(
                short_code,
                request.data.get("ip_address") or None,
                request.data.get("user_agent", ""),
                request.data.get("referer", ""),
            )
        except Exception:
            logger.exception("click_ingest.enqueue_failed short_code=%s", short_code)
            return Response({"detail": "Failed to record click."}, status=500)

        return Response(status=202)
