"""Generic retry-with-exponential-backoff-and-jitter helper.

Hand-rolled, not a new ``tenacity`` dependency — consistent with this
codebase's existing style of hand-rolled infra (``RedisClient``, the
short-code collision retry in ``URLShortenerService``) rather than
pulling in a library for something this small.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


def call_with_backoff[T](
    fn: Callable[[], T],
    *,
    max_attempts: int,
    base_delay: float,
    retry_on: tuple[type[Exception], ...],
) -> T:
    """Call ``fn`` up to ``max_attempts`` times, backing off between failures.

    Sleeps ``base_delay * 2**attempt + random.uniform(0, base_delay)``
    seconds between attempts (attempt 0 is the first *retry*, i.e. no
    sleep happens before the very first call). Only exceptions matching
    ``retry_on`` are retried — anything else propagates immediately. If
    every attempt fails, the last exception is re-raised.
    """
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except retry_on as exc:
            last_exc = exc
            logger.warning(
                "call_with_backoff.attempt_failed attempt=%s max_attempts=%s error=%s",
                attempt + 1,
                max_attempts,
                exc,
            )
            if attempt == max_attempts - 1:
                break
            delay = base_delay * (2**attempt) + random.uniform(0, base_delay)
            time.sleep(delay)

    assert last_exc is not None  # max_attempts >= 1 guarantees at least one failure here
    raise last_exc
