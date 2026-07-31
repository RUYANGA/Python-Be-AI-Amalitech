"""Collection-based aggregators for student data.

Each aggregator has a single responsibility and demonstrates a specific
standard-library collection:

* :class:`GradeDistributionAggregator` — :class:`collections.Counter`
* :class:`StudentGroupAggregator`      — :class:`collections.defaultdict`
* :class:`OrderedReportAggregator`     — :class:`collections.OrderedDict`
"""

from collections import Counter, OrderedDict, defaultdict

from student_analytics.logger import get_logger
from student_analytics.models import GradeLetter, Student

_logger = get_logger("aggregators")


class GradeDistributionAggregator:
    """Count how many grades fall into each :class:`GradeLetter` bucket."""

    def aggregate(self, students: list[Student]) -> Counter[GradeLetter]:
        """Return a :class:`Counter` of :class:`GradeLetter` frequencies.

        Args:
            students: Students whose grades should be tallied.

        Returns:
            A :class:`Counter` mapping each letter grade to its frequency.
            Every :class:`GradeLetter` key is guaranteed to be present, even
            when the count is zero, so downstream code can safely iterate
            without ``KeyError``.
        """
        counter: Counter[GradeLetter] = Counter()
        # Ensure every letter grade appears, even if unused.
        counter.update(dict.fromkeys(GradeLetter, 0))
        for student in students:
            for grade in student.grades:
                counter[grade.letter] += 1
        _logger.debug("Grade distribution computed: %s", dict(counter))
        return counter


class StudentGroupAggregator:
    """Group students by an attribute using :class:`collections.defaultdict`."""

    def group_by_major(self, students: list[Student]) -> dict[str, list[Student]]:
        """Return a mapping of major -> list of students.

        Args:
            students: The students to group.

        Returns:
            A dictionary keyed by the ``major`` attribute of each student.
        """
        groups: defaultdict[str, list[Student]] = defaultdict(list)
        for student in students:
            groups[student.major].append(student)
        _logger.debug("Grouped %d students into %d majors", len(students), len(groups))
        return dict(groups)

    def group_by_year(self, students: list[Student]) -> dict[int, list[Student]]:
        """Return a mapping of year -> list of students.

        Args:
            students: The students to group.

        Returns:
            A dictionary keyed by the ``year`` attribute of each student.
        """
        groups: defaultdict[int, list[Student]] = defaultdict(list)
        for student in students:
            groups[student.year].append(student)
        _logger.debug("Grouped %d students into %d cohorts", len(students), len(groups))
        return dict(groups)


class OrderedReportAggregator:
    """Assemble a stable, ordered ranking of top-performing students."""

    def top_performers(self, students: list[Student], limit: int = 5) -> OrderedDict[str, float]:
        """Return an :class:`OrderedDict` of the top ``limit`` students by GPA.

        The dictionary preserves descending GPA order. Ties are broken by
        student id so that the output is deterministic across runs.

        Args:
            students: Candidate students.
            limit: Maximum number of entries to return. Must be positive.

        Returns:
            An :class:`OrderedDict` mapping ``student_id`` to GPA in the
            order they should appear in reports.

        Raises:
            ValueError: If ``limit`` is not a positive integer.
        """
        if limit <= 0:
            raise ValueError(f"limit must be a positive integer; got {limit!r}.")

        ranked = sorted(
            students,
            key=lambda student: (-student.gpa, student.student_id),
        )
        ordered: OrderedDict[str, float] = OrderedDict()
        for student in ranked[:limit]:
            ordered[student.student_id] = student.gpa
        _logger.debug(
            "Selected top %d performers (requested %d) from %d students",
            len(ordered),
            limit,
            len(students),
        )
        return ordered
