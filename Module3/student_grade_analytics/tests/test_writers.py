"""Tests for :mod:`student_analytics.writers`."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from student_analytics.exceptions import ReportWriteError
from student_analytics.io.writers import JSONReportWriter
from student_analytics.models import ReportPayload


def _payload() -> ReportPayload:
    return {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "total_students": 0,
        "grade_distribution": {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0},
        "students_by_major": {},
        "students_by_year": {},
        "top_performers": [],
        "statistics": {},
        "rolling_averages": {},
    }


class TestJSONReportWriter:
    def test_writes_valid_json(self, tmp_path: Path) -> None:
        target = tmp_path / "report.json"
        writer = JSONReportWriter(target)
        writer.write(_payload())
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded["total_students"] == 0

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "deep" / "report.json"
        writer = JSONReportWriter(target)
        writer.write(_payload())
        assert target.exists()

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        target = tmp_path / "report.json"
        writer = JSONReportWriter(str(target))
        writer.write(_payload())
        assert target.exists()

    def test_permission_error_translated(self, tmp_path: Path) -> None:
        target = tmp_path / "report.json"
        writer = JSONReportWriter(target)
        with (
            patch("pathlib.Path.open", side_effect=PermissionError("locked")),
            pytest.raises(ReportWriteError, match="Permission denied"),
        ):
            writer.write(_payload())

    def test_os_error_translated(self, tmp_path: Path) -> None:
        target = tmp_path / "report.json"
        writer = JSONReportWriter(target)
        with (
            patch("pathlib.Path.open", side_effect=OSError("disk full")),
            pytest.raises(ReportWriteError, match="Unable to write"),
        ):
            writer.write(_payload())

    def test_custom_indent_is_used(self, tmp_path: Path) -> None:
        target = tmp_path / "report.json"
        writer = JSONReportWriter(target, indent=4)
        writer.write(_payload())
        # With indent=4, the second line will start with four spaces.
        second_line = target.read_text(encoding="utf-8").splitlines()[1]
        assert second_line.startswith("    ")
