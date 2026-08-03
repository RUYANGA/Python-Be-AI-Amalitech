"""High-level orchestrator that ties every component together.

The :class:`StudentGradeAnalyzer` is deliberately thin: it reads students,
delegates report assembly to a :class:`ReportPayloadBuilder`, and persists
the result through a writer. It depends only on abstractions — the
:class:`StudentReader`, :class:`ReportWriter`, and :class:`MetricCalculator`
protocols — so every collaborator can be replaced without modifying the
analyzer (Single-Responsibility, Dependency-Inversion, and Open/Closed
Principles).
"""

from collections.abc import Sequence
from typing import Final

from student_analytics.analytics.builder import ReportPayloadBuilder
from student_analytics.analytics.metrics import MetricCalculator, build_default_metrics
from student_analytics.logger import get_logger
from student_analytics.models import ReportPayload
from student_analytics.models.protocols import ReportWriter, StudentReader

_logger = get_logger("analyzer")

DEFAULT_TOP_PERFORMER_LIMIT = 5
DEFAULT_ROLLING_WINDOW_SIZE = 3


class StudentGradeAnalyzer:
    """Compose the pipeline that produces a :class:`ReportPayload`."""

    def __init__(
        self,
        reader: StudentReader,
        writer: ReportWriter,
        *,
        top_performer_limit: int = DEFAULT_TOP_PERFORMER_LIMIT,
        rolling_window_size: int = DEFAULT_ROLLING_WINDOW_SIZE,
        payload_builder: ReportPayloadBuilder | None = None,
        metrics: Sequence[MetricCalculator] | None = None,
    ) -> None:
        """Initialise the analyzer with its collaborators.

        By default the analyzer builds its own :class:`ReportPayloadBuilder`
        from the standard metric set. Callers may instead inject a complete
        builder, or a custom ordered sequence of metrics, to change what the
        report contains — no subclassing required.

        Args:
            reader: Source of the student data.
            writer: Destination for the generated report.
            top_performer_limit: Maximum number of top performers reported.
            rolling_window_size: Window size for the rolling average.
            payload_builder: Optional custom :class:`ReportPayloadBuilder`.
            metrics: Optional ordered sequence of :class:`MetricCalculator`
                implementations defining the report sections.

        Raises:
            ValueError: If both ``payload_builder`` and ``metrics`` are
                supplied, or if the resulting builder is invalid.
        """
        if payload_builder is not None and metrics is not None:
            raise ValueError("Provide either payload_builder or metrics, not both.")
        if payload_builder is None:
            if metrics is None:
                metrics = build_default_metrics(
                    top_performer_limit=top_performer_limit,
                    rolling_window_size=rolling_window_size,
                )
            payload_builder = ReportPayloadBuilder(metrics=list(metrics))
        self._reader: Final[StudentReader] = reader
        self._writer: Final[ReportWriter] = writer
        self._payload_builder: Final[ReportPayloadBuilder] = payload_builder

    def run(self) -> ReportPayload:
        """Execute the analytics pipeline end-to-end.

        Returns:
            The :class:`ReportPayload` that was persisted through the writer.
        """
        _logger.info("Starting student analytics pipeline")
        students = self._reader.read()
        payload = self._payload_builder.build(students)
        self._writer.write(payload)
        _logger.info("Pipeline completed successfully")
        return payload
