"""Pricing utilities for calculating rental costs and late fees."""

from vehicle_rental.core import Vehicle


def calculate_rental_cost(vehicle: Vehicle, days: int) -> float:
    """Calculate the total rental cost by delegating to the vehicle's own method.

    Args:
        vehicle: The vehicle being rented.
        days: Number of rental days.

    Returns:
        Total rental cost.
    """
    return vehicle.calculate_rental_cost(days)


def calculate_late_fee(
    vehicle: Vehicle, overdue_days: int, late_multiplier: float = 1.5
) -> float:
    """Calculate a late fee for overdue returns.

    Fee = daily_rate × overdue_days × late_multiplier.

    Args:
        vehicle: The overdue vehicle.
        overdue_days: Number of days the return is late.
        late_multiplier: Multiplier applied to the daily rate (default 1.5).

    Returns:
        Late fee amount, or 0.0 if not overdue.
    """
    if overdue_days <= 0:
        return 0.0
    daily = vehicle.daily_rate
    return round(daily * overdue_days * late_multiplier, 2)
