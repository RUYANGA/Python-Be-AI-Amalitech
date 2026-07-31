"""Tests for :mod:`student_analytics.models`."""

import pytest

from student_analytics.exceptions import InvalidGradeError
from student_analytics.models import Course, Grade, GradeLetter, Student


class TestGradeLetter:
    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (100.0, GradeLetter.A),
            (90.0, GradeLetter.A),
            (89.99, GradeLetter.B),
            (80.0, GradeLetter.B),
            (75.0, GradeLetter.C),
            (70.0, GradeLetter.C),
            (65.0, GradeLetter.D),
            (60.0, GradeLetter.D),
            (59.99, GradeLetter.F),
            (0.0, GradeLetter.F),
        ],
    )
    def test_from_score_boundaries(self, score: float, expected: GradeLetter) -> None:
        assert GradeLetter.from_score(score) is expected

    @pytest.mark.parametrize("invalid", [-0.01, 100.01, -50.0, 200.0])
    def test_from_score_rejects_out_of_range_values(self, invalid: float) -> None:
        with pytest.raises(InvalidGradeError):
            GradeLetter.from_score(invalid)


class TestCourse:
    def test_course_is_namedtuple(self) -> None:
        course = Course(code="CS101", name="Intro to CS", credits=3)
        assert course.code == "CS101"
        assert course.name == "Intro to CS"
        assert course.credits == 3
        # Tuple immutability
        assert isinstance(course, tuple)


class TestGrade:
    def test_grade_stores_values(self) -> None:
        course = Course(code="CS101", name="Intro to CS", credits=3)
        grade = Grade(course=course, semester="Fall2023", score=88.0)
        assert grade.course == course
        assert grade.semester == "Fall2023"
        assert grade.score == 88.0

    def test_grade_letter_property(self) -> None:
        course = Course(code="CS101", name="Intro to CS", credits=3)
        assert (
            Grade(course=course, semester="Fall2023", score=91.0).letter
            is GradeLetter.A
        )
        assert (
            Grade(course=course, semester="Fall2023", score=45.0).letter
            is GradeLetter.F
        )

    @pytest.mark.parametrize("bad_score", [-1.0, 100.5, 150.0])
    def test_grade_rejects_bad_scores(self, bad_score: float) -> None:
        course = Course(code="CS101", name="Intro to CS", credits=3)
        with pytest.raises(InvalidGradeError):
            Grade(course=course, semester="Fall2023", score=bad_score)

    def test_grade_is_frozen(self) -> None:
        course = Course(code="CS101", name="Intro to CS", credits=3)
        grade = Grade(course=course, semester="Fall2023", score=90.0)
        with pytest.raises(Exception):  # noqa: B017 - dataclass FrozenInstanceError
            grade.score = 50.0  # type: ignore[misc]


class TestStudent:
    def test_full_name_property(self) -> None:
        student = Student(
            student_id="S001",
            first_name="John",
            last_name="Doe",
            major="CS",
            year=2,
        )
        assert student.full_name == "John Doe"

    def test_gpa_with_no_grades_returns_zero(self) -> None:
        student = Student(
            student_id="S001",
            first_name="John",
            last_name="Doe",
            major="CS",
            year=2,
        )
        assert student.gpa == 0.0

    def test_gpa_computes_average(self, sample_student: Student) -> None:
        # Two grades: 85 and 95 -> mean 90
        assert sample_student.gpa == pytest.approx(90.0)

    def test_add_grade_extends_transcript(self, sample_student: Student) -> None:
        course = Course(code="EN101", name="English", credits=3)
        new_grade = Grade(course=course, semester="Fall2024", score=70.0)
        sample_student.add_grade(new_grade)
        assert new_grade in sample_student.grades
        assert len(sample_student.grades) == 3
