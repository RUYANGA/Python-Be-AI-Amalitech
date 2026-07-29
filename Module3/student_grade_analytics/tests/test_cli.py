"""Tests for :mod:`student_analytics.cli`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from student_analytics.cli import build_parser, main


def test_build_parser_returns_parser() -> None:
    parser = build_parser()
    assert parser.prog == "student-analytics"


def test_main_end_to_end(valid_csv_path: Path, tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    exit_code = main(
        [
            "--input",
            str(valid_csv_path),
            "--output",
            str(output),
            "--top",
            "2",
            "--window",
            "2",
            "--verbose",
        ]
    )
    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["total_students"] == 3
    assert len(payload["top_performers"]) == 2


def test_main_returns_one_on_analytics_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    output = tmp_path / "report.json"
    exit_code = main(["--input", str(missing), "--output", str(output)])
    assert exit_code == 1
    assert not output.exists()


def test_main_reports_bad_arguments(tmp_path: Path) -> None:
    # Missing required --input flag -> argparse exits with code 2.
    with pytest.raises(SystemExit) as excinfo:
        main(["--output", str(tmp_path / "out.json")])
    assert excinfo.value.code == 2


def test_main_defaults_used_when_optional_args_missing(
    valid_csv_path: Path, tmp_path: Path
) -> None:
    output = tmp_path / "report.json"
    exit_code = main(["--input", str(valid_csv_path), "--output", str(output)])
    assert exit_code == 0
    assert output.exists()
