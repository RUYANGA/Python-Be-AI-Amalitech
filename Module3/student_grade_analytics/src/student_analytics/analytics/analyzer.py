"""High-level orchestrator that ties every component together.

The :class:`StudentGradeAnalyzer` obeys the Dependency-Inversion Principle:
it accepts anything that satisfies the :class:`StudentReader` and
:class:`ReportWriter` protocols, and delegates every specialised task to a
purpose-built collaborator (aggregators, statistics, rolling averages).
That structure makes every collaborator easy to replace in tests and keeps
this class focused on flow control.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

from student_analytics.analytics.aggregators import (
    GradeDistributionAggregator,
    OrderedReportAggregator,
    StudentGroupAggregator,
)
from student_analytics.analytics.rolling_average import RollingAverageCalculator
from student_analytics.analytics.statistics import GradeStatistics
from student_analytics.logger import get_logger

if TYPE_CHECKING:
    from student_analytics.models import ReportPayload, Student
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
        distribution_aggregator: GradeDistributionAggregator | None = None,
        group_aggregator: StudentGroupAggregator | None = None,
        ordered_aggregator: OrderedReportAggregator | None = None,
        statistics: GradeStatistics | None = None,
    ) -> None:
        """Initialise the analyzer with its collaborators.

        Every collaborator has a sensible default, but they can be replaced
        with any object exposing the same public methods — a direct
        application of the Liskov-Substitution Principle.

        Args:
            reader: Source of the student data.
            writer: Destination for the generated report.
            top_performer_limit: Maximum number of top performers reported.
            rolling_window_size: Window size for the rolling average.
            distribution_aggregator: Optional custom :class:`GradeDistributionAggregator`.
            group_aggregator: Optional custom :class:`StudentGroupAggregator`.
            ordered_aggregator: Optional custom :class:`OrderedReportAggregator`.
            statistics: Optional custom :class:`GradeStatistics`.
        """
        self._reader: Final[StudentReader] = reader
        self._writer: Final[ReportWriter] = writer
        self._top_performer_limit: Final[int] = top_performer_limit
        self._rolling_window_size: Final[int] = rolling_window_size
        self._distribution_aggregator: Final[GradeDistributionAggregator] = (
            distribution_aggregator or GradeDistributionAggregator()
        )
        self._group_aggregator: Final[StudentGroupAggregator] = (
            group_aggregator or StudentGroupAggregator()
        )
        self._ordered_aggregator: Final[OrderedReportAggregator] = (
            ordered_aggregator or OrderedReportAggregator()
        )
        self._statistics: Final[GradeStatistics] = statistics or GradeStatistics()

    def run(self) -> ReportPayload:
        """Execute the analytics pipeline end-to-end.

        Returns:
            The :class:`ReportPayload` that was persisted through the writer.
        """
        _logger.info("Starting student analytics pipeline")
        students = self._reader.read()
        payload = self._build_report(students)
        self._writer.write(payload)
        _logger.info("Pipeline completed successfully")
        return payload

    def _build_report(self, students: list[Student]) -> ReportPayload:
        """Build the :class:`ReportPayload` from a list of students.

        Args:
            students: The students to summarise.

        Returns:
            The freshly assembled report payload.
        """
        distribution = self._distribution_aggregator.aggregate(students)
        by_major = self._group_aggregator.group_by_major(students)
        by_year = self._group_aggregator.group_by_year(students)
        top = self._ordered_aggregator.top_performers(students, limit=self._top_performer_limit)
        statistics = self._statistics.compute_summary(students)
        rolling = self._rolling_averages(students)

        payload: ReportPayload = {
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "total_students": len(students),
            "grade_distribution": {letter.value: distribution[letter] for letter in distribution},
            "students_by_major": OrderedDict(
                (major, sorted(student.student_id for student in group))
                for major, group in sorted(by_major.items())
            ),
            "students_by_year": OrderedDict(
                (str(year), sorted(student.student_id for student in group))
                for year, group in sorted(by_year.items())
            ),
            "top_performers": [
                {
                    "student_id": student_id,
                    "gpa": round(gpa, 2),
                }
                for student_id, gpa in top.items()
            ],
            "statistics": {key: round(value, 2) for key, value in statistics.items()},
            "rolling_averages": rolling,
        }
        return payload

    def _rolling_averages(self, students: list[Student]) -> dict[str, list[float]]:
        """Compute per-student rolling averages ordered by semester.

        Args:
            students: The students to analyse.

        Returns:
            A dictionary mapping ``student_id`` to the list of rolling averages
            observed after each recorded grade.
        """
        rolling: dict[str, list[float]] = {}
        for student in students:
            calculator = RollingAverageCalculator(window_size=self._rolling_window_size)
            ordered_grades = sorted(student.grades, key=lambda grade: grade.semester)
            values = calculator.extend(grade.score for grade in ordered_grades)
            rolling[student.student_id] = [round(value, 2) for value in values]
        return rolling
