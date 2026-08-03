"""Domain models for the student analytics package.

This module defines every value object used across the codebase:

* :class:`Course` — immutable :func:`~typing.NamedTuple` describing a course.
* :class:`Grade`  — a single grade earned by a student in a course.
* :class:`Student` — aggregate root that owns a list of :class:`Grade`.
* :class:`GradeLetter` — enum mapping numeric scores to letter grades.
* :class:`ReportPayload` — :class:`~typing.TypedDict` for JSON output.

The models are kept purely declarative (no I/O, no side effects) so that
they satisfy the Single-Responsibility Principle and can be safely reused
from tests and other modules.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import NamedTuple, TypedDict

from student_analytics.exceptions import InvalidGradeError


class GradeLetter(StrEnum):
    """Letter grade classification derived from a numeric score."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"

    @classmethod
    def from_score(cls, score: float) -> "GradeLetter":
        """Convert a numeric score in ``[0.0, 100.0]`` to a letter grade.

        Args:
            score: The numeric score to classify.

        Returns:
            The matching :class:`GradeLetter` value.

        Raises:
            InvalidGradeError: If ``score`` falls outside ``[0.0, 100.0]``.
        """
        if not 0.0 <= score <= 100.0:
            raise InvalidGradeError(f"Score must be within [0.0, 100.0]; got {score!r}.")
        if score >= 90.0:
            return cls.A
        if score >= 80.0:
            return cls.B
        if score >= 70.0:
            return cls.C
        if score >= 60.0:
            return cls.D
        return cls.F


class Course(NamedTuple):
    """Immutable description of an academic course.

    Attributes:
        code: The unique course code (e.g. ``"CS101"``).
        name: Human-readable course name.
        credits: Credit hours awarded upon completion.
    """

    code: str
    name: str
    credits: int


@dataclass(frozen=True, slots=True)
class Grade:
    """A single grade earned by a student in a specific course and semester.

    Attributes:
        course: The :class:`Course` the grade applies to.
        semester: The semester identifier (e.g. ``"Fall2024"``).
        score: Numeric score in the closed interval ``[0.0, 100.0]``.
    """

    course: Course
    semester: str
    score: float

    def __post_init__(self) -> None:
        """Validate the numeric score after dataclass initialisation.

        Raises:
            InvalidGradeError: If ``score`` is outside ``[0.0, 100.0]``.
        """
        if not 0.0 <= self.score <= 100.0:
            raise InvalidGradeError(
                f"Score for course {self.course.code} must be in [0.0, 100.0]; got {self.score!r}."
            )

    @property
    def letter(self) -> GradeLetter:
        """Return the letter grade equivalent of :attr:`score`."""
        return GradeLetter.from_score(self.score)


@dataclass(slots=True)
class Student:
    """A student together with every grade they have earned.

    Attributes:
        student_id: Unique student identifier (e.g. ``"S001"``).
        first_name: Given name.
        last_name: Family name.
        major: Declared major (e.g. ``"CS"``).
        year: Year of study (1 = freshman, 4 = senior).
        grades: List of :class:`Grade` objects earned by this student.
    """

    student_id: str
    first_name: str
    last_name: str
    major: str
    year: int
    grades: list[Grade] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        """Return the student's full name (``first_name last_name``)."""
        return f"{self.first_name} {self.last_name}"

    @property
    def gpa(self) -> float:
        """Return the student's unweighted GPA on a 0.0-100.0 scale.

        Returns ``0.0`` if the student has no grades recorded.
        """
        if not self.grades:
            return 0.0
        return sum(grade.score for grade in self.grades) / len(self.grades)

    def add_grade(self, grade: Grade) -> None:
        """Append a :class:`Grade` to this student's transcript.

        Args:
            grade: The grade to record.
        """
        self.grades.append(grade)


class ReportPayload(TypedDict):
    """Typed representation of the JSON analytics report.

    The nested containers use plain built-in types so that the payload
    remains JSON-serialisable without custom encoders.
    """

    generated_at: str
    total_students: int
    grade_distribution: dict[str, int]
    students_by_major: dict[str, list[str]]
    students_by_year: dict[str, list[str]]
    top_performers: list[dict[str, str | float]]
    statistics: dict[str, float]
    rolling_averages: dict[str, list[float]]
