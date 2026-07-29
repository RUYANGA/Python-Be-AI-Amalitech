"""Shared pytest fixtures for the student analytics test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from student_analytics.models import Course, Grade, Student

VALID_CSV_CONTENT = """student_id,first_name,last_name,major,year,course_code,course_name,credits,semester,score
S001,John,Doe,CS,2,CS101,Intro to CS,3,Fall2023,85.5
S001,John,Doe,CS,2,CS201,Data Structures,3,Spring2024,92.0
S002,Jane,Smith,MATH,3,MA301,Linear Algebra,3,Fall2023,95.0
S002,Jane,Smith,MATH,3,MA302,Real Analysis,3,Fall2023,89.0
S003,Alice,Johnson,CS,1,CS101,Intro to CS,3,Fall2023,65.0
"""


@pytest.fixture
def valid_csv_path(tmp_path: Path) -> Path:
    """Return a path to a temporary CSV file populated with valid rows."""
    path = tmp_path / "students.csv"
    path.write_text(VALID_CSV_CONTENT, encoding="utf-8")
    return path


@pytest.fixture
def sample_course() -> Course:
    """Return a reusable :class:`Course` instance."""
    return Course(code="CS101", name="Intro to CS", credits=3)


@pytest.fixture
def sample_student(sample_course: Course) -> Student:
    """Return a student pre-populated with two graded courses."""
    student = Student(
        student_id="S001",
        first_name="John",
        last_name="Doe",
        major="CS",
        year=2,
    )
    student.add_grade(Grade(course=sample_course, semester="Fall2023", score=85.0))
    student.add_grade(Grade(course=sample_course, semester="Spring2024", score=95.0))
    return student


@pytest.fixture
def sample_students() -> list[Student]:
    """Return three students with varied grade distributions."""
    course_a = Course(code="CS101", name="Intro to CS", credits=3)
    course_b = Course(code="MA201", name="Calc II", credits=4)

    alpha = Student(
        student_id="S001",
        first_name="John",
        last_name="Doe",
        major="CS",
        year=2,
        grades=[
            Grade(course=course_a, semester="Fall2023", score=85.0),
            Grade(course=course_b, semester="Spring2024", score=95.0),
        ],
    )
    beta = Student(
        student_id="S002",
        first_name="Jane",
        last_name="Smith",
        major="MATH",
        year=3,
        grades=[
            Grade(course=course_a, semester="Fall2023", score=72.0),
            Grade(course=course_b, semester="Spring2024", score=68.0),
        ],
    )
    gamma = Student(
        student_id="S003",
        first_name="Alice",
        last_name="Johnson",
        major="CS",
        year=1,
        grades=[
            Grade(course=course_a, semester="Fall2023", score=55.0),
        ],
    )
    return [alpha, beta, gamma]
