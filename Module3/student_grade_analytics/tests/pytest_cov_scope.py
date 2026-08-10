"""Scope pytest-cov to the modules exercised by the selected test files.

pytest-cov starts measuring coverage while the initial conftests load, using
the ``--cov`` source taken straight from the command line. When only a single
test file is selected, measuring the whole package would drag the total below
the 100% coverage gate. This plugin rewrites the coverage source (before
pytest-cov consumes it) to the modules the selected test files actually
exercise, so a per-file run can still satisfy the 100% requirement. Running
the whole suite leaves the package-wide source untouched.

The plugin deliberately lives outside ``student_analytics`` so that importing
it does not import the whole package ahead of coverage starting.
"""

from pathlib import Path
from typing import Any, Final

import pytest

TEST_MODULE_MAP: Final[dict[str, tuple[str, ...]]] = {
    "test_aggregators.py": ("student_analytics.analytics.aggregators",),
    "test_analyzer.py": (
        "student_analytics.analytics.analyzer",
        "student_analytics.analytics.builder",
        "student_analytics.analytics.metrics",
    ),
    "test_builder.py": (
        "student_analytics.analytics.builder",
        "student_analytics.analytics.metrics",
    ),
    "test_cli.py": ("student_analytics.cli",),
    "test_exceptions.py": ("student_analytics.exceptions",),
    "test_logger.py": ("student_analytics.logger",),
    "test_metrics.py": ("student_analytics.analytics.metrics",),
    "test_models.py": ("student_analytics.models.models",),
    "test_protocols.py": ("student_analytics.models.protocols",),
    "test_readers.py": ("student_analytics.io.readers",),
    "test_rolling_average.py": ("student_analytics.analytics.rolling_average",),
    "test_statistics.py": ("student_analytics.analytics.statistics",),
    "test_writers.py": ("student_analytics.io.writers",),
}


def _modules_for_test_files(args: list[str]) -> list[str]:
    """Return the package modules exercised by the test files in ``args``.

    Args:
        args: Command line arguments passed to pytest, which include the
            selected test file paths.

    Returns:
        The list of ``student_analytics`` modules the selected test files
        cover, or an empty list when no mapped test file is present.
    """
    names = {Path(arg).name.split("::", 1)[0] for arg in args}
    return [module for name in names for module in TEST_MODULE_MAP.get(name, ())]


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_load_initial_conftests(
    early_config: Any,
    parser: Any,
    args: list[str],
) -> Any:
    """Point coverage at the modules under test before pytest-cov reads them.

    The pre-yield block runs ahead of pytest-cov's own ``tryfirst``
    implementation (tryfirst wrappers execute before every non-wrapper), so
    the coverage source is rewritten while pytest-cov can still pick it up.

    Args:
        early_config: The early pytest configuration.
        parser: The command line parser (unused here).
        args: Command line arguments, including the selected test files.

    Returns:
        A generator that yields control back to the remaining hook chain.
    """
    del parser
    modules = _modules_for_test_files(args)
    if modules:
        early_config.known_args_namespace.cov_source = modules
    yield
