"""Payroll module for salary computation, taxation, and payslip generation.

Computes pay using type-specific logic (full-time, contract, intern),
applies a flat tax rate, and formats results as printable payslips.

Functions:
    calculate_salary: Computes gross pay based on employee type.
    apply_tax: Deducts a flat tax rate from gross salary.
    generate_payslip: Creates a formatted text payslip for an employee.
    process_payroll: Processes a list of employees and returns payslips.
"""

from typing import Dict, List

from src.employee_payroll_tracker.employe import (
    ContractEmployee,
    FullTimeEmployee,
    Intern,
)
from src.employee_payroll_tracker.logger import get_logger
from src.employee_payroll_tracker.util import validate_non_negative_number

logger = get_logger(__name__)

TAX_RATE = 0.20


def calculate_salary(employee) -> float:
    """Calculate the total gross salary for an employee.

    Computes pay based on employee type:
        - Full-time: base salary + bonus
        - Contract:  hourly rate x hours worked
        - Intern:    fixed stipend

    Args:
        employee: An Employee instance (or subclass).

    Returns:
        The computed gross salary.
    """
    if isinstance(employee, FullTimeEmployee):
        gross = employee.salary + employee.bonus
        logger.debug(
            "Calculated salary for %s (ID: %d): base=%.2f + bonus=%.2f = %.2f",
            employee.name,
            employee.emp_id,
            employee.salary,
            employee.bonus,
            gross,
        )
    elif isinstance(employee, ContractEmployee):
        gross = employee.hourly_rate * employee.hours_worked
        logger.debug(
            "Calculated salary for %s (ID: %d): rate=%.2f x hours=%.2f = %.2f",
            employee.name,
            employee.emp_id,
            employee.hourly_rate,
            employee.hours_worked,
            gross,
        )
    elif isinstance(employee, Intern):
        gross = employee.salary
        logger.debug(
            "Calculated salary for %s (ID: %d): stipend=%.2f",
            employee.name,
            employee.emp_id,
            gross,
        )
    else:
        gross = employee.salary
        logger.debug(
            "Calculated salary for %s (ID: %d): %.2f",
            employee.name,
            employee.emp_id,
            gross,
        )
    return gross


def apply_tax(gross_salary: float, tax_rate: float = TAX_RATE) -> float:
    """Apply a flat tax rate and return the net (after-tax) salary.

    Args:
        gross_salary: Total salary before tax.
        tax_rate: Tax rate as a decimal (default 0.20).

    Returns:
        Net salary after tax deduction.
    """
    try:
        validate_non_negative_number(gross_salary, "Gross salary")
    except ValueError:
        logger.error("Rejected negative gross salary: %.2f", gross_salary)
        raise
    if not 0 <= tax_rate <= 1:
        logger.error("Rejected invalid tax rate: %.2f", tax_rate)
        raise ValueError("Tax rate must be between 0 and 1.")
    net = round(gross_salary * (1 - tax_rate), 2)
    tax_amount = round(gross_salary - net, 2)
    logger.info(
        "Applied tax: gross=%.2f, tax=%.2f (%.0f%%), net=%.2f",
        gross_salary,
        tax_amount,
        tax_rate * 100,
        net,
    )
    return net


def generate_payslip(employee, gross: float = 0.0, net: float = 0.0) -> str:
    """Generate a formatted payslip string for an employee.

    When ``gross`` and ``net`` are both provided (non-zero) they are
    used directly; otherwise they are computed from the employee.

    Args:
        employee: An Employee instance.
        gross: Pre-computed gross salary (optional).
        net: Pre-computed net salary (optional).

    Returns:
        A multi-line string containing the complete payslip.
    """
    if not gross or not net:
        gross = calculate_salary(employee)
        net = apply_tax(gross)

    tax_amount = round(gross - net, 2)

    logger.info(
        "Generated payslip for %s (ID: %d) — gross=%.2f, net=%.2f",
        employee.name,
        employee.emp_id,
        gross,
        net,
    )

    lines = [
        "=" * 54,
        f"         PAYSLIP — {employee.employee_type().upper()}",
        "=" * 54,
        f"  Employee  :  {employee.name}",
        f"  ID        :  {employee.emp_id}",
        f"  Type      :  {employee.employee_type()}",
        "-" * 54,
        f"  Gross Pay :  ${gross:>9.2f}",
        f"  Tax (20%) :  ${tax_amount:>9.2f}",
        "-" * 54,
        f"  Net Pay   :  ${net:>9.2f}",
        "=" * 54,
    ]
    return "\n".join(lines)


def process_payroll(employees: List) -> Dict[int, dict]:
    """Process payroll for a list of employees.

    Builds a dictionary mapping each employee ID to their computed
    payroll data including gross salary, tax, net pay, and formatted
    payslip.

    Args:
        employees: A list of Employee instances.

    Returns:
        A dictionary of ``{emp_id: {"name": str, "gross": float,
        "net": float, "payslip": str}}``.
    """
    if not employees:
        logger.warning("process_payroll called with empty employee list")
        return {}

    payroll_data: Dict[int, dict] = {}
    i = 0
    while i < len(employees):
        emp = employees[i]
        gross = calculate_salary(emp)
        net = apply_tax(gross)
        payslip = generate_payslip(emp, gross, net)
        payroll_data[emp.emp_id] = {
            "name": emp.name,
            "gross": gross,
            "net": net,
            "payslip": payslip,
        }
        i += 1

    logger.info("Payroll complete — %d employee(s) processed", len(payroll_data))
    return payroll_data
