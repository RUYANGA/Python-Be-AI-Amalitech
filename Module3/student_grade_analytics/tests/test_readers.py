"""Tests for :mod:`student_analytics.readers`."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from student_analytics.exceptions import StudentDataError
from student_analytics.io.readers import CSVStudentReader


class TestCSVStudentReader:
    def test_reads_valid_csv(self, valid_csv_path: Path) -> None:
        reader = CSVStudentReader(valid_csv_path)
        students = reader.read()
        assert len(students) == 3
        first = next(student for student in students if student.student_id == "S001")
        assert first.full_name == "John Doe"
        assert len(first.grades) == 2

    def test_reads_valid_csv_from_string_path(self, valid_csv_path: Path) -> None:
        reader = CSVStudentReader(str(valid_csv_path))
        students = reader.read()
        assert len(students) == 3

    def test_missing_file_raises_student_data_error(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist.csv"
        reader = CSVStudentReader(missing)
        with pytest.raises(StudentDataError, match="CSV file not found"):
            reader.read()

    def test_missing_required_columns_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.csv"
        bad.write_text("student_id,first_name\nS001,John\n", encoding="utf-8")
        reader = CSVStudentReader(bad)
        with pytest.raises(StudentDataError, match="missing required columns"):
            reader.read()

    def test_malformed_numeric_row_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "malformed.csv"
        bad.write_text(
            "student_id,first_name,last_name,major,year,course_code,course_name,credits,semester,score\n"
            "S001,John,Doe,CS,NOT_A_NUMBER,CS101,Intro,3,Fall2023,80\n",
            encoding="utf-8",
        )
        reader = CSVStudentReader(bad)
        with pytest.raises(StudentDataError, match="Malformed row"):
            reader.read()

    def test_invalid_grade_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "invalid_score.csv"
        bad.write_text(
            "student_id,first_name,last_name,major,year,course_code,course_name,credits,semester,score\n"
            "S001,John,Doe,CS,2,CS101,Intro,3,Fall2023,150.0\n",
            encoding="utf-8",
        )
        reader = CSVStudentReader(bad)
        with pytest.raises(StudentDataError, match="Invalid grade"):
            reader.read()

    def test_permission_error_is_translated(self, tmp_path: Path) -> None:
        target = tmp_path / "students.csv"
        target.write_text("dummy", encoding="utf-8")
        reader = CSVStudentReader(target)
        with (
            patch("pathlib.Path.open", side_effect=PermissionError("locked")),
            pytest.raises(StudentDataError, match="Permission denied"),
        ):
            reader.read()

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod semantics differ on Windows")
    def test_os_error_is_translated(self, tmp_path: Path) -> None:
        target = tmp_path / "students.csv"
        target.write_text("dummy", encoding="utf-8")
        reader = CSVStudentReader(target)
        with (
            patch("pathlib.Path.open", side_effect=OSError("disk failure")),
            pytest.raises(StudentDataError, match="Unable to read"),
        ):
            reader.read()

    def test_duplicate_student_rows_are_merged(self, tmp_path: Path) -> None:
        target = tmp_path / "students.csv"
        target.write_text(
            "student_id,first_name,last_name,major,year,course_code,course_name,credits,semester,score\n"
            "S001,John,Doe,CS,2,CS101,Intro,3,Fall2023,80.0\n"
            "S001,John,Doe,CS,2,CS201,DS,3,Spring2024,90.0\n"
            "S001,John,Doe,CS,2,MA101,Calc,4,Fall2023,70.0\n",
            encoding="utf-8",
        )
        students = CSVStudentReader(target).read()
        assert len(students) == 1
        assert len(students[0].grades) == 3

    def test_reader_exposes_path_and_encoding(self, tmp_path: Path) -> None:
        target = tmp_path / "students.csv"
        reader = CSVStudentReader(target, encoding="latin-1")
        assert reader.path == target
        assert reader.encoding == "latin-1"
