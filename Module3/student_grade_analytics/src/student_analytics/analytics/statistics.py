"""Statistical computations over collections of grades and students.

The class is stateless — every method takes its inputs explicitly — which
keeps it trivial to test in isolation and to reuse from other modules.
"""

from collections import Counter
from statistics import mean, median

from student_analytics.logger import get_logger
from student_analytics.models import Student

_logger = get_logger("statistics")


class GradeStatistics:
    """Compute summary statistics over lists of numeric scores."""

    def mean(self, scores: list[float]) -> float:
        """Return the arithmetic mean of ``scores`` (``0.0`` when empty)."""
        if not scores:
            return 0.0
        return float(mean(scores))

    def median(self, scores: list[float]) -> float:
        """Return the median of ``scores`` (``0.0`` when empty)."""
        if not scores:
            return 0.0
        return float(median(scores))

    def mode(self, scores: list[float]) -> float:
        """Return the modal score using :class:`collections.Counter`.

        When multiple scores tie for the highest frequency, the smallest
        such score is returned so that the output is deterministic.

        Args:
            scores: The scores to inspect.

        Returns:
            The modal score, or ``0.0`` if ``scores`` is empty.
        """
        if not scores:
            return 0.0
        counter = Counter(scores)
        highest_frequency = max(counter.values())
        candidates = [
            score for score, count in counter.items() if count == highest_frequency
        ]
        return float(min(candidates))

    def percentile(self, scores: list[float], percentile: float) -> float:
        """Return the value at the given percentile using linear interpolation.

        Args:
            scores: The scores to inspect.
            percentile: Percentile in the closed interval ``[0.0, 100.0]``.

        Returns:
            The interpolated percentile value, or ``0.0`` if ``scores`` is empty.

        Raises:
            ValueError: If ``percentile`` is outside ``[0.0, 100.0]``.
        """
        if not 0.0 <= percentile <= 100.0:
            raise ValueError(f"percentile must be in [0.0, 100.0]; got {percentile!r}.")
        if not scores:
            return 0.0
        ordered = sorted(scores)
        if len(ordered) == 1:
            return float(ordered[0])
        rank = (percentile / 100.0) * (len(ordered) - 1)
        lower_index = int(rank)
        upper_index = min(lower_index + 1, len(ordered) - 1)
        fraction = rank - lower_index
        return float(
            ordered[lower_index]
            + (ordered[upper_index] - ordered[lower_index]) * fraction
        )

    def compute_summary(self, students: list[Student]) -> dict[str, float]:
        """Compute a full statistical summary across every student's grades.

        Args:
            students: Students whose grades should be summarised.

        Returns:
            A dictionary with keys ``mean``, ``median``, ``mode``,
            ``percentile_25``, ``percentile_75``, ``highest``, and
            ``lowest``. Empty inputs yield zeros for every metric.
        """
        scores = [grade.score for student in students for grade in student.grades]
        if not scores:
            _logger.debug("No grades available; returning zeroed summary")
            return {
                "mean": 0.0,
                "median": 0.0,
                "mode": 0.0,
                "percentile_25": 0.0,
                "percentile_75": 0.0,
                "highest": 0.0,
                "lowest": 0.0,
            }
        summary = {
            "mean": self.mean(scores),
            "median": self.median(scores),
            "mode": self.mode(scores),
            "percentile_25": self.percentile(scores, 25.0),
            "percentile_75": self.percentile(scores, 75.0),
            "highest": float(max(scores)),
            "lowest": float(min(scores)),
        }
        _logger.debug("Computed statistics summary: %s", summary)
        return summary
