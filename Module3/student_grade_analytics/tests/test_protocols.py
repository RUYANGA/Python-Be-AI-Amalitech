"""Tests for :mod:`student_analytics.models.protocols`."""

from __future__ import annotations

from student_analytics.models import ReportPayload, Student
from student_analytics.models.protocols import ReportWriter, StudentReader


class MyReader:
    def read(self) -> list[Student]:
        return []


class MyWriter:
    def write(self, payload: ReportPayload) -> None:
        _ = payload


def test_student_reader_protocol_recognises_implementation() -> None:
    assert isinstance(MyReader(), StudentReader)


def test_report_writer_protocol_recognises_implementation() -> None:
    assert isinstance(MyWriter(), ReportWriter)


def test_non_conforming_object_is_not_recognised() -> None:
    class Empty:
        pass

    assert not isinstance(Empty(), StudentReader)
    assert not isinstance(Empty(), ReportWriter)
