"""Consumes ``ClickRecorded`` events from the shortener service's Kafka topic.

Runs as its own long-lived process — a separate container from the web
process (see ``analytics-worker`` in the top-level ``docker-compose.yml``)
— so ingesting clicks can never compete with, or be blocked by, serving
the ``GET /api/v1/analytics/{short_code}/`` endpoint.

Commits offsets manually, only *after* a message has been persisted
(``enable.auto.commit: False``) — a crash mid-batch just means the
message gets redelivered on restart instead of silently dropped.
Country/city are resolved here, not by the shortener service — geo
enrichment is an analytics concern.
"""

from __future__ import annotations

import json
import logging

from confluent_kafka import Consumer
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.analytics.api.geo import GeoIP2FastLocator
from apps.analytics.api.repositories.analytics_repository import DjangoClickAnalyticsRepository

logger = logging.getLogger(__name__)

CLICKS_TOPIC = "clicks"
CONSUMER_GROUP = "analytics-workers"
POLL_TIMEOUT_SECONDS = 5.0


class Command(BaseCommand):
    help = "Consume click events published by the shortener service and persist them."

    def handle(self, *_args, **_options):
        consumer = Consumer(
            {
                "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "group.id": CONSUMER_GROUP,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        consumer.subscribe([CLICKS_TOPIC])

        repository = DjangoClickAnalyticsRepository()
        geo_locator = GeoIP2FastLocator()

        self.stdout.write(self.style.SUCCESS(f"consume_clicks: listening on '{CLICKS_TOPIC}'"))

        try:
            while True:
                msg = consumer.poll(timeout=POLL_TIMEOUT_SECONDS)
                if msg is None:
                    continue
                if msg.error():
                    logger.warning("consume_clicks.kafka_error error=%s", msg.error())
                    continue

                self._process_one(repository, geo_locator, msg.value())
                consumer.commit(msg)
        finally:
            consumer.close()

    @staticmethod
    def _process_one(repository, geo_locator, raw: bytes | None) -> None:
        try:
            fields = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            logger.warning("consume_clicks.dropped_malformed_entry raw=%r", raw)
            return

        short_code = fields.get("short_code", "")
        if not short_code:
            logger.warning("consume_clicks.dropped_malformed_entry fields=%s", fields)
            return

        ip_address = fields.get("ip_address") or None
        country = geo_locator.country_code(ip_address)
        try:
            repository.record_click(
                short_code,
                ip_address=ip_address,
                user_agent=fields.get("user_agent", ""),
                referer=fields.get("referer", ""),
                country=country,
            )
        except Exception:
            logger.exception("consume_clicks.record_failed short_code=%s", short_code)
