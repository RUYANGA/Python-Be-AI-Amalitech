"""Assembly of the final analytics report payload.

:class:`ReportPayloadBuilder` is the only place that knows how the report is
structured. It takes an ordered collection of :class:`MetricCalculator`
implementations, runs each one against the students, and merges their
results into the :class:`ReportPayload`. Because the builder depends only on
the :class:`MetricCalculator` protocol, new report sections can be added by
supplying additional metrics — the builder itself never needs to change.
"""

from datetime import UTC, datetime
from typing import Final, cast

from student_analytics.analytics.metrics import (
    MetricCalculator,
    ensure_unique_metric_keys,
)
from student_analytics.models import ReportPayload, Student


class ReportPayloadBuilder:
    """Assemble a :class:`ReportPayload` from an ordered set of metrics."""

    def __init__(self, metrics: list[MetricCalculator] | None = None) -> None:
        """Initialise the builder with the metrics that define the report.

        Args:
            metrics: Ordered metric calculators to evaluate. Defaults to an
                empty sequence, which is rejected.

        Raises:
            ValueError: If ``metrics`` is empty or contains duplicate keys.
        """
        self._metrics: Final[tuple[MetricCalculator, ...]] = tuple(metrics or [])
        if not self._metrics:
            raise ValueError("At least one metric calculator is required.")
        ensure_unique_metric_keys(self._metrics)

    def build(self, students: list[Student]) -> ReportPayload:
        """Evaluate every metric and merge the results into a payload.

        Args:
            students: The students to analyse.

        Returns:
            The fully assembled :class:`ReportPayload`.
        """
        payload: dict[str, object] = {
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "total_students": len(students),
        }
        for metric in self._metrics:
            payload[metric.key] = metric.compute(students)
        return cast("ReportPayload", payload)
