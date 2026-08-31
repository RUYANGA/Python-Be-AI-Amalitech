"""Publishes click events for the analytics service to consume.

This is the seam that replaces the old in-process ``record_click``: the
redirect/resolve endpoints are the highest-traffic, latency-critical,
unauthenticated path in the whole system, so they must never block on —
or fail because of — the analytics service being slow or down.
Publishing to Kafka is fire-and-forget: ``produce()`` only enqueues the
message locally and returns immediately (the client's own background
I/O thread does the actual send); a publish failure is logged and
swallowed, never raised.
"""

from __future__ import annotations

import json
import logging

from confluent_kafka import KafkaException, Producer
from django.conf import settings

logger = logging.getLogger(__name__)

CLICKS_TOPIC = "clicks"

_PRODUCER: Producer | None = None


def _get_producer() -> Producer:
    """Return the singleton :class:`Producer`.

    A fresh ``Producer`` per request would each spin up their own
    background I/O thread and broker connection for no reason — this is
    built once per process and reused, the same way ``get_redis_client``
    is for the Redis-backed cache.
    """
    global _PRODUCER
    if _PRODUCER is None:
        _PRODUCER = Producer({"bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS})
    return _PRODUCER


class ClickEventPublisher:
    """Publishes ``ClickRecorded`` events to the shared ``clicks`` Kafka topic."""

    def __init__(self, producer: Producer | None = None) -> None:
        self._producer = producer or _get_producer()

    def publish(
        self,
        short_code: str,
        ip_address: str | None = None,
        user_agent: str = "",
        referer: str = "",
    ) -> None:
        payload = json.dumps(
            {
                "short_code": short_code,
                "ip_address": ip_address or "",
                "user_agent": user_agent,
                "referer": referer,
            }
        ).encode("utf-8")
        try:
            # Keyed by short_code so all of one link's clicks land on the
            # same partition — not required for correctness here, but
            # keeps per-link ordering if that ever starts to matter.
            self._producer.produce(
                CLICKS_TOPIC,
                key=short_code.encode("utf-8"),
                value=payload,
                callback=self._delivery_callback,
            )
            # Non-blocking: services queued delivery-report callbacks
            # without waiting on this message's own acknowledgement.
            self._producer.poll(0)
        except (KafkaException, BufferError):
            logger.warning("click_event.publish_dropped short_code=%s", short_code, exc_info=True)

    @staticmethod
    def _delivery_callback(err, msg) -> None:
        if err is not None:
            logger.warning("click_event.delivery_failed error=%s", err)
        else:
            logger.debug(
                "click_event.delivered short_code=%s partition=%s offset=%s",
                msg.key().decode("utf-8") if msg.key() else "",
                msg.partition(),
                msg.offset(),
            )
