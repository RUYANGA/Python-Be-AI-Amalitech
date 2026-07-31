"""Tests for :mod:`student_analytics.analyzer`."""

import pytest

from student_analytics.analytics.analyzer import StudentGradeAnalyzer
from student_analytics.models import ReportPayload, Student


class InMemoryReader:
    """Return a fixed list of students without touching the filesystem."""

    def __init__(self, students: list[Student]) -> None:
        self._students = students

    def read(self) -> list[Student]:
        return self._students


class InMemoryWriter:
    """Store the payload written to it for later inspection."""

    def __init__(self) -> None:
        self.payload: ReportPayload | None = None

    def write(self, payload: ReportPayload) -> None:
        self.payload = payload


class TestStudentGradeAnalyzer:
    def test_pipeline_produces_expected_payload(self, sample_students: list[Student]) -> None:
        reader = InMemoryReader(sample_students)
        writer = InMemoryWriter()
        analyzer = StudentGradeAnalyzer(
            reader=reader, writer=writer, top_performer_limit=2, rolling_window_size=2
        )
        payload = analyzer.run()
        assert writer.payload is payload
        assert payload["total_students"] == 3
        assert payload["grade_distribution"]["A"] == 1  # 95.0
        assert payload["grade_distribution"]["F"] == 1  # 55.0
        assert payload["students_by_major"] == {
            "CS": ["S001", "S003"],
            "MATH": ["S002"],
        }
        assert payload["students_by_year"] == {
            "1": ["S003"],
            "2": ["S001"],
            "3": ["S002"],
        }
        assert len(payload["top_performers"]) == 2
        assert payload["top_performers"][0]["student_id"] == "S001"

    def test_pipeline_with_empty_input(self) -> None:
        reader = InMemoryReader([])
        writer = InMemoryWriter()
        analyzer = StudentGradeAnalyzer(reader=reader, writer=writer)
        payload = analyzer.run()
        assert payload["total_students"] == 0
        assert payload["top_performers"] == []
        assert payload["students_by_major"] == {}
        assert payload["students_by_year"] == {}
        # Statistics for empty input should all be zero.
        assert all(value == 0.0 for value in payload["statistics"].values())

    def test_generated_at_is_iso_format(self, sample_students: list[Student]) -> None:
        reader = InMemoryReader(sample_students)
        writer = InMemoryWriter()
        analyzer = StudentGradeAnalyzer(reader=reader, writer=writer)
        payload = analyzer.run()
        # ISO-8601 with timezone -> ends with an offset like +00:00.
        assert "T" in payload["generated_at"]
        assert payload["generated_at"].endswith("+00:00")

    def test_rolling_averages_ordered_by_semester(self, sample_students: list[Student]) -> None:
        reader = InMemoryReader(sample_students)
        writer = InMemoryWriter()
        analyzer = StudentGradeAnalyzer(reader=reader, writer=writer, rolling_window_size=2)
        payload = analyzer.run()
        # S001: Fall2023=85, Spring2024=95 -> rolling: [85.0, 90.0]
        assert payload["rolling_averages"]["S001"] == pytest.approx([85.0, 90.0])
