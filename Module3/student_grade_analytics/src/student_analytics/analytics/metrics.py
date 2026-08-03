"""Report metrics computed from a list of students.

Every metric is a small, single-responsibility object that computes exactly
one slice of the analytics report and implements the
:class:`MetricCalculator` protocol. Consumers depend only on that narrow
abstraction, so new metrics can be added — or existing ones swapped for
different implementations — without touching the analyzer or the payload
builder. That is a direct application of the Open/Closed and
Dependency-Inversion Principles.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from student_analytics.analytics.aggregators import (
    GradeDistributionAggregator,
    OrderedReportAggregator,
    StudentGroupAggregator,
)
from student_analytics.analytics.rolling_average import RollingAverageCalculator
from student_analytics.analytics.statistics import GradeStatistics
from student_analytics.models import Student


@runtime_checkable
class MetricCalculator(Protocol):
    """Compute one named slice of the analytics report."""

    key: str

    def compute(self, students: list[Student]) -> object:
        """Return the metric value computed from ``students``."""
        ...


class GradeDistributionMetric:
    """Tally every letter-grade bucket present in the students' grades."""

    key = "grade_distribution"

    def __init__(self, aggregator: GradeDistributionAggregator | None = None) -> None:
        """Initialise the metric with an optional custom aggregator.

        Args:
            aggregator: Custom :class:`GradeDistributionAggregator`. Defaults
                to a freshly constructed instance.
        """
        self._aggregator = aggregator or GradeDistributionAggregator()

    def compute(self, students: list[Student]) -> dict[str, int]:
        """Return a mapping of letter grade -> frequency."""
        distribution = self._aggregator.aggregate(students)
        return {letter.value: distribution[letter] for letter in distribution}


class StudentsByMajorMetric:
    """Group student ids by their declared major."""

    key = "students_by_major"

    def __init__(self, aggregator: StudentGroupAggregator | None = None) -> None:
        """Initialise the metric with an optional custom aggregator.

        Args:
            aggregator: Custom :class:`StudentGroupAggregator`. Defaults to
                a freshly constructed instance.
        """
        self._aggregator = aggregator or StudentGroupAggregator()

    def compute(self, students: list[Student]) -> dict[str, list[str]]:
        """Return a sorted mapping of major -> sorted student ids."""
        groups = self._aggregator.group_by_major(students)
        return {
            major: sorted(student.student_id for student in group)
            for major, group in sorted(groups.items())
        }


class StudentsByYearMetric:
    """Group student ids by their academic year."""

    key = "students_by_year"

    def __init__(self, aggregator: StudentGroupAggregator | None = None) -> None:
        """Initialise the metric with an optional custom aggregator.

        Args:
            aggregator: Custom :class:`StudentGroupAggregator`. Defaults to
                a freshly constructed instance.
        """
        self._aggregator = aggregator or StudentGroupAggregator()

    def compute(self, students: list[Student]) -> dict[str, list[str]]:
        """Return a sorted mapping of year -> sorted student ids."""
        groups = self._aggregator.group_by_year(students)
        return {
            str(year): sorted(student.student_id for student in group)
            for year, group in sorted(groups.items())
        }


class TopPerformersMetric:
    """Rank the strongest students by descending overall GPA."""

    key = "top_performers"

    def __init__(
        self,
        aggregator: OrderedReportAggregator | None = None,
        limit: int = 5,
    ) -> None:
        """Initialise the metric.

        Args:
            aggregator: Custom :class:`OrderedReportAggregator`. Defaults to
                a freshly constructed instance.
            limit: Maximum number of performers to include.
        """
        self._aggregator = aggregator or OrderedReportAggregator()
        self._limit = limit

    def compute(self, students: list[Student]) -> list[dict[str, str | float]]:
        """Return the top performers with their GPAs rounded to 2 decimals."""
        ranked = self._aggregator.top_performers(students, limit=self._limit)
        return [
            {"student_id": student_id, "gpa": round(gpa, 2)} for student_id, gpa in ranked.items()
        ]


class StatisticsMetric:
    """Summarise every raw grade score across the whole student body."""

    key = "statistics"

    def __init__(self, statistics: GradeStatistics | None = None) -> None:
        """Initialise the metric with an optional custom calculator.

        Args:
            statistics: Custom :class:`GradeStatistics`. Defaults to a
                freshly constructed instance.
        """
        self._statistics = statistics or GradeStatistics()

    def compute(self, students: list[Student]) -> dict[str, float]:
        """Return the statistical summary rounded to 2 decimals."""
        summary = self._statistics.compute_summary(students)
        return {key: round(value, 2) for key, value in summary.items()}


class RollingAveragesMetric:
    """Compute per-student rolling averages ordered by semester."""

    key = "rolling_averages"

    def __init__(self, window_size: int = 3) -> None:
        """Initialise the metric.

        Args:
            window_size: Window size for the rolling-average calculator.
        """
        self._window_size = window_size

    def compute(self, students: list[Student]) -> dict[str, list[float]]:
        """Return a mapping of student id -> list of rolling averages."""
        rolling_averages: dict[str, list[float]] = {}
        for student in students:
            calculator = RollingAverageCalculator(window_size=self._window_size)
            ordered_grades = sorted(student.grades, key=lambda grade: grade.semester)
            values = calculator.extend(grade.score for grade in ordered_grades)
            rolling_averages[student.student_id] = [round(value, 2) for value in values]
        return rolling_averages


def build_default_metrics(
    *,
    top_performer_limit: int,
    rolling_window_size: int,
) -> list[MetricCalculator]:
    """Assemble the standard set of metrics for the analytics report.

    Args:
        top_performer_limit: Maximum number of top performers reported.
        rolling_window_size: Window size used by the rolling-average metric.

    Returns:
        An ordered list of :class:`MetricCalculator` implementations covering
        every section of the default report payload.
    """
    metrics: list[MetricCalculator] = [
        GradeDistributionMetric(),
        StudentsByMajorMetric(),
        StudentsByYearMetric(),
        TopPerformersMetric(limit=top_performer_limit),
        StatisticsMetric(),
        RollingAveragesMetric(window_size=rolling_window_size),
    ]
    return metrics


def ensure_unique_metric_keys(
    metrics: Sequence[MetricCalculator],
) -> None:
    """Raise a :class:`ValueError` if two metrics share the same key.

    Duplicate keys would silently overwrite one another inside the report
    payload, so this guard makes the collision explicit.

    Args:
        metrics: The metric calculators to validate.

    Raises:
        ValueError: If any key appears more than once.
    """
    keys = [metric.key for metric in metrics]
    if len(keys) != len(set(keys)):
        raise ValueError(f"Metric keys must be unique; got {keys!r}.")
