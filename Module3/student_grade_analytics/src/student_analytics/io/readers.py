"""CSV-based implementations of the :class:`StudentReader` protocol.

The reader consumes a wide CSV where each row represents a single grade
(one student may appear on many rows). Students are aggregated in memory
using a dictionary keyed by ``student_id``. For large inputs the reader
uses a generator internally so that peak memory scales with the number of
distinct students rather than the number of rows.
"""

import csv
from collections.abc import Iterator
from pathlib import Path
from typing import Final

from student_analytics.exceptions import InvalidGradeError, StudentDataError
from student_analytics.logger import get_logger
from student_analytics.models import Course, Grade, Student

_logger = get_logger("readers")

REQUIRED_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "student_id",
        "first_name",
        "last_name",
        "major",
        "year",
        "course_code",
        "course_name",
        "credits",
        "semester",
        "score",
    }
)


class CSVStudentReader:
    """Read students and their grades from a CSV file.

    The expected CSV schema is::

        student_id,first_name,last_name,major,year,
        course_code,course_name,credits,semester,score

    Attributes:
        path: The :class:`~pathlib.Path` to the CSV file.
        encoding: Text encoding used to open the file (defaults to UTF-8).
    """

    def __init__(self, path: Path | str, encoding: str = "utf-8") -> None:
        """Initialise the reader with the target CSV path.

        Args:
            path: Path to the CSV file to load.
            encoding: Text encoding to use when opening the file.
        """
        self.path: Final[Path] = Path(path)
        self.encoding: Final[str] = encoding
        _logger.debug("CSVStudentReader created for %s", self.path)

    def read(self) -> list[Student]:
        """Load every student from the CSV file.

        Returns:
            A list of :class:`Student` objects, one per unique ``student_id``.

        Raises:
            StudentDataError: If the file cannot be found, cannot be read,
                is missing required columns, or contains malformed rows.
        """
        _logger.info("Reading students from %s", self.path)
        students: dict[str, Student] = {}
        try:
            for row_index, row in self._iter_rows():
                self._merge_row_into_students(students, row, row_index)
        except FileNotFoundError as error:
            _logger.error("CSV file not found: %s", self.path)
            raise StudentDataError(f"CSV file not found: {self.path}") from error
        except PermissionError as error:
            _logger.error("Permission denied when reading %s", self.path)
            raise StudentDataError(
                f"Permission denied when reading {self.path}"
            ) from error
        except OSError as error:
            _logger.error("Unable to read %s: %s", self.path, error)
            raise StudentDataError(f"Unable to read {self.path}: {error}") from error

        _logger.info("Loaded %d unique students from %s", len(students), self.path)
        return list(students.values())

    def _iter_rows(self) -> Iterator[tuple[int, dict[str, str]]]:
        """Yield ``(row_index, row_dict)`` pairs from the CSV file.

        Yields:
            Tuples of the 1-based row number and the row as a mapping.

        Raises:
            StudentDataError: If required columns are missing.
        """
        with self.path.open(mode="r", encoding=self.encoding, newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            fieldnames = reader.fieldnames or []
            missing = REQUIRED_COLUMNS - set(fieldnames)
            if missing:
                sorted_missing = ", ".join(sorted(missing))
                raise StudentDataError(
                    f"CSV is missing required columns: {sorted_missing}"
                )
            # start=2 accounts for the header row occupying line 1.
            yield from enumerate(reader, start=2)

    def _merge_row_into_students(
        self,
        students: dict[str, Student],
        row: dict[str, str],
        row_index: int,
    ) -> None:
        """Merge one CSV row into ``students``.

        Args:
            students: The accumulator mapping ``student_id`` to :class:`Student`.
            row: The parsed CSV row.
            row_index: 1-based row number used in error messages.

        Raises:
            StudentDataError: If the row is malformed or the score invalid.
        """
        try:
            student_id = row["student_id"].strip()
            year = int(row["year"])
            credits_value = int(row["credits"])
            score = float(row["score"])
        except (ValueError, KeyError, AttributeError) as error:
            raise StudentDataError(
                f"Malformed row {row_index} in {self.path}: {error}"
            ) from error

        student = students.get(student_id)
        if student is None:
            student = Student(
                student_id=student_id,
                first_name=row["first_name"].strip(),
                last_name=row["last_name"].strip(),
                major=row["major"].strip(),
                year=year,
                grades=[],
            )
            students[student_id] = student

        course = Course(
            code=row["course_code"].strip(),
            name=row["course_name"].strip(),
            credits=credits_value,
        )
        try:
            grade = Grade(course=course, semester=row["semester"].strip(), score=score)
        except InvalidGradeError as error:
            raise StudentDataError(
                f"Invalid grade on row {row_index}: {error}"
            ) from error
        student.add_grade(grade)
