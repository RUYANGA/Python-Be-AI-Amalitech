"""Utility functions for the Employee Payroll Tracker.

Provides helpers for currency formatting and input validation.
"""


def format_currency(amount: float) -> str:
    """Format a numeric amount as a USD currency string.

    Args:
        amount: The numeric value to format.

    Returns:
        A string like ``$1,234.56``.
    """
    return f"${amount:,.2f}"


def validate_positive_number(value: float, field_name: str = "Value") -> None:
    """Raise ``ValueError`` if *value* is not positive.

    Args:
        value: The number to check.
        field_name: Name used in the error message for context.

    Raises:
        ValueError: If ``value <= 0``.
    """
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")


def validate_non_negative_number(value: float, field_name: str = "Value") -> None:
    """Raise ``ValueError`` if *value* is negative.

    Args:
        value: The number to check.
        field_name: Name used in the error message for context.

    Raises:
        ValueError: If ``value < 0``.
    """
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative.")
