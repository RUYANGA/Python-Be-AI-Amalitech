"""Structural protocols enabling dependency inversion.

Every component that reads external data or writes reports depends on a
:class:`~typing.Protocol` defined here rather than a concrete class. This
makes the analyzer trivial to unit test with in-memory fakes and simple to
extend with new formats (Parquet, XML, SQL, …) without modifying existing
code — a direct application of the Open/Closed Principle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from student_analytics.models import ReportPayload, Student


@runtime_checkable
class StudentReader(Protocol):
    """Reads a collection of :class:`~student_analytics.models.Student`."""

    def read(self) -> list[Student]:
        """Return every student available from the underlying source."""
        ...


@runtime_checkable
class ReportWriter(Protocol):
    """Persists a :class:`~student_analytics.models.ReportPayload`."""

    def write(self, payload: ReportPayload) -> None:
        """Persist ``payload`` to the underlying destination."""
        ...
