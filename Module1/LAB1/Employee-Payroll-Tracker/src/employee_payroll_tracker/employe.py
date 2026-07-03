"""Employee module defining the base Employee class and role-specific subclasses.

Supports full-time, contract, and intern employee types with
encapsulated attributes and property validation.
"""

from abc import ABC, abstractmethod

from src.employee_payroll_tracker import get_logger
from src.employee_payroll_tracker import (
    validate_non_negative_number,
    validate_positive_number,
)

logger = get_logger(__name__)


class Employee(ABC):
    """Abstract base class for all employee types.

    Provides common attributes (emp_id, name, salary) with property
    validation and enforces a contract for salary calculation.
    """

    def __init__(self, emp_id: int, name: str, salary: float) -> None:
        self.emp_id = emp_id
        self.name = name
        self._salary = 0.0
        self.salary = salary
        logger.info(
            "Created %s employee: %s (ID: %d)", self.employee_type(), name, emp_id
        )

    @property
    def salary(self) -> float:
        """Return the employee's base salary."""
        return self._salary

    @salary.setter
    def salary(self, value: float) -> None:
        """Set the employee's base salary, validating it is positive."""
        try:
            validate_positive_number(value, "Salary")
        except ValueError:
            logger.warning(
                "Rejected invalid salary %.2f for %s (ID: %d)",
                value,
                self.name,
                self.emp_id,
            )
            raise
        self._salary = value

    @abstractmethod
    def employee_type(self) -> str:
        """Return a human-readable label for the employee role."""
        ...

    def __str__(self) -> str:
        return f"{self.name} (ID: {self.emp_id})"


class FullTimeEmployee(Employee):
    """Full-time employee with a fixed monthly salary and optional bonus."""

    def __init__(
        self, emp_id: int, name: str, base_salary: float, bonus: float = 0.0
    ) -> None:
        self._bonus = 0.0
        super().__init__(emp_id, name, base_salary)
        self.bonus = bonus

    @property
    def bonus(self) -> float:
        """Return the employee's bonus amount."""
        return self._bonus

    @bonus.setter
    def bonus(self, value: float) -> None:
        """Set the bonus, ensuring it is non-negative."""
        try:
            validate_non_negative_number(value, "Bonus")
        except ValueError:
            logger.warning(
                "Rejected negative bonus %.2f for %s (ID: %d)",
                value,
                self.name,
                self.emp_id,
            )
            raise
        self._bonus = value

    def employee_type(self) -> str:
        return "Full-Time"


class ContractEmployee(Employee):
    """Contract employee paid at an hourly rate for hours worked."""

    def __init__(
        self, emp_id: int, name: str, hourly_rate: float, hours_worked: float
    ) -> None:
        self._hours_worked = 0.0
        super().__init__(emp_id, name, hourly_rate)
        self.hours_worked = hours_worked

    @property
    def hourly_rate(self) -> float:
        """Return the hourly rate (stored as the base salary)."""
        return self.salary

    @hourly_rate.setter
    def hourly_rate(self, value: float) -> None:
        """Set the hourly rate, delegating to the salary setter."""
        try:
            validate_positive_number(value, "Hourly rate")
        except ValueError:
            logger.warning(
                "Rejected invalid hourly rate %.2f for %s (ID: %d)",
                value,
                self.name,
                self.emp_id,
            )
            raise
        self.salary = value

    @property
    def hours_worked(self) -> float:
        """Return the number of hours worked this period."""
        return self._hours_worked

    @hours_worked.setter
    def hours_worked(self, value: float) -> None:
        """Set hours worked, capped at 744 (max in a 31-day month)."""
        if value < 0:
            logger.warning(
                "Rejected negative hours %.2f for %s (ID: %d)",
                value,
                self.name,
                self.emp_id,
            )
            raise ValueError("Hours worked cannot be negative.")
        if value > 744:
            logger.warning(
                "Rejected hours %.2f (exceeds 744) for %s (ID: %d)",
                value,
                self.name,
                self.emp_id,
            )
            raise ValueError("Hours worked cannot exceed 744 in a month.")
        self._hours_worked = value

    def employee_type(self) -> str:
        return "Contract"


class Intern(Employee):
    """Intern who receives a fixed stipend."""

    def __init__(self, emp_id: int, name: str, stipend: float) -> None:
        super().__init__(emp_id, name, stipend)

    @property
    def stipend(self) -> float:
        """Return the intern's stipend."""
        return self.salary

    @stipend.setter
    def stipend(self, value: float) -> None:
        """Set the stipend, ensuring it is positive."""
        validate_positive_number(value, "Stipend")
        self.salary = value

    def employee_type(self) -> str:
        return "Intern"
