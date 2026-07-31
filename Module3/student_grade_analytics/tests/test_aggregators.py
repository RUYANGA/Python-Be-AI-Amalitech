"""Tests for :mod:`student_analytics.aggregators`."""

import pytest

from student_analytics.analytics.aggregators import (
    GradeDistributionAggregator,
    OrderedReportAggregator,
    StudentGroupAggregator,
)
from student_analytics.models import Course, Grade, GradeLetter, Student


class TestGradeDistributionAggregator:
    def test_counts_every_letter(self, sample_students: list[Student]) -> None:
        counter = GradeDistributionAggregator().aggregate(sample_students)
        # sample_students grades: 85 (B), 95 (A), 72 (C), 68 (D), 55 (F)
        assert counter[GradeLetter.A] == 1
        assert counter[GradeLetter.B] == 1
        assert counter[GradeLetter.C] == 1
        assert counter[GradeLetter.D] == 1
        assert counter[GradeLetter.F] == 1

    def test_all_buckets_present_even_when_empty(self) -> None:
        counter = GradeDistributionAggregator().aggregate([])
        for letter in GradeLetter:
            assert letter in counter
            assert counter[letter] == 0


class TestStudentGroupAggregator:
    def test_group_by_major(self, sample_students: list[Student]) -> None:
        groups = StudentGroupAggregator().group_by_major(sample_students)
        assert set(groups.keys()) == {"CS", "MATH"}
        assert {student.student_id for student in groups["CS"]} == {"S001", "S003"}
        assert [student.student_id for student in groups["MATH"]] == ["S002"]

    def test_group_by_year(self, sample_students: list[Student]) -> None:
        groups = StudentGroupAggregator().group_by_year(sample_students)
        assert set(groups.keys()) == {1, 2, 3}
        assert [student.student_id for student in groups[2]] == ["S001"]

    def test_empty_input_yields_empty_groups(self) -> None:
        aggregator = StudentGroupAggregator()
        assert aggregator.group_by_major([]) == {}
        assert aggregator.group_by_year([]) == {}


class TestOrderedReportAggregator:
    def test_returns_top_n_in_descending_gpa_order(self, sample_students: list[Student]) -> None:
        top_performers = OrderedReportAggregator().top_performers(sample_students, limit=2)
        ordered_ids = list(top_performers.keys())
        assert ordered_ids == ["S001", "S002"]
        assert top_performers["S001"] == pytest.approx(90.0)

    def test_limit_larger_than_population_returns_all(self, sample_students: list[Student]) -> None:
        top_performers = OrderedReportAggregator().top_performers(sample_students, limit=99)
        assert len(top_performers) == 3

    def test_tie_broken_by_student_id(self) -> None:
        course = Course(code="CS101", name="Intro to CS", credits=3)

        def build_student(student_id: str, score: float) -> Student:
            return Student(
                student_id=student_id,
                first_name="F",
                last_name="L",
                major="CS",
                year=1,
                grades=[Grade(course=course, semester="Fall2023", score=score)],
            )

        # All three tie at GPA 90. Order should follow sorted student_ids.
        students = [
            build_student("S003", 90.0),
            build_student("S001", 90.0),
            build_student("S002", 90.0),
        ]
        top_performers = OrderedReportAggregator().top_performers(students, limit=3)
        assert list(top_performers.keys()) == ["S001", "S002", "S003"]

    @pytest.mark.parametrize("bad_limit", [0, -1, -100])
    def test_non_positive_limit_raises(self, bad_limit: int) -> None:
        with pytest.raises(ValueError, match="limit must be a positive integer"):
            OrderedReportAggregator().top_performers([], limit=bad_limit)
