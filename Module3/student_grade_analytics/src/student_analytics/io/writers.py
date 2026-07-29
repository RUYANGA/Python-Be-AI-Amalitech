"""JSON implementation of the :class:`ReportWriter` protocol.

The writer uses the standard-library :mod:`json` module with pretty-printing
enabled. Target directories are created automatically so that the caller
does not need to ensure the output directory exists beforehand.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Final

from student_analytics.exceptions import ReportWriteError
from student_analytics.logger import get_logger

if TYPE_CHECKING:
    from student_analytics.models import ReportPayload

_logger = get_logger("writers")


class JSONReportWriter:
    """Persist a :class:`ReportPayload` as pretty-printed JSON."""

    def __init__(self, path: Path | str, *, indent: int = 2, encoding: str = "utf-8") -> None:
        """Initialise the writer.

        Args:
            path: Destination path for the JSON report.
            indent: Number of spaces used for indentation in the output file.
            encoding: Text encoding to use when writing the file.
        """
        self.path: Final[Path] = Path(path)
        self.indent: Final[int] = indent
        self.encoding: Final[str] = encoding
        _logger.debug("JSONReportWriter created for %s", self.path)

    def write(self, payload: ReportPayload) -> None:
        """Serialise ``payload`` to :attr:`path`.

        Args:
            payload: The typed report payload to persist.

        Raises:
            ReportWriteError: If the destination cannot be written to.
        """
        _logger.info("Writing JSON report to %s", self.path)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open(mode="w", encoding=self.encoding) as json_file:
                json.dump(payload, json_file, indent=self.indent, sort_keys=False)
        except PermissionError as error:
            _logger.error("Permission denied when writing %s", self.path)
            raise ReportWriteError(f"Permission denied when writing {self.path}") from error
        except OSError as error:
            _logger.error("Unable to write %s: %s", self.path, error)
            raise ReportWriteError(f"Unable to write {self.path}: {error}") from error
        _logger.info("Report successfully written to %s", self.path)
