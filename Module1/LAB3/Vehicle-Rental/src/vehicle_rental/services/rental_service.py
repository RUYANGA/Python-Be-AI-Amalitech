"""Core rental service managing vehicle registration, rentals, and returns."""

from typing import Optional
from vehicle_rental.core import Vehicle
from vehicle_rental.services.pricing import calculate_rental_cost, calculate_late_fee


class RentalRecord:
    """A record of an active rental."""

    def __init__(self, vehicle: Vehicle, days: int, cost: float):
        """Initialise a rental record.

        Args:
            vehicle: The rented vehicle.
            days: Number of rental days.
            cost: Total rental cost.
        """
        self.vehicle = vehicle
        self.days = days
        self.cost = cost

    def __repr__(self) -> str:
        return (
            f"RentalRecord({self.vehicle.vehicle_id}, {self.days}d, ${self.cost:.2f})"
        )


class RentalService:
    """Manages the fleet of vehicles and processes rentals and returns."""

    def __init__(self):
        """Initialise an empty rental service."""
        self._vehicles: dict[str, Vehicle] = {}
        self._active_rentals: dict[str, RentalRecord] = {}

    def register_vehicle(self, vehicle: Vehicle) -> None:
        """Add a vehicle to the fleet.

        Args:
            vehicle: The vehicle to register.

        Raises:
            ValueError: If a vehicle with the same ID already exists.
        """
        if vehicle.vehicle_id in self._vehicles:
            raise ValueError(f"Vehicle {vehicle.vehicle_id} already registered")
        self._vehicles[vehicle.vehicle_id] = vehicle

    def get_vehicle(self, vehicle_id: str) -> Optional[Vehicle]:
        """Look up a vehicle by its ID.

        Args:
            vehicle_id: The unique vehicle identifier.

        Returns:
            The vehicle if found, otherwise None.
        """
        return self._vehicles.get(vehicle_id)

    def get_all_vehicles(self) -> list[Vehicle]:
        """Return a list of all registered vehicles."""
        return list(self._vehicles.values())

    def get_available_vehicles(self) -> list[Vehicle]:
        """Return a list of vehicles currently available for rent."""
        return [vehicle for vehicle in self._vehicles.values() if vehicle.is_available]

    def rent_vehicle(self, vehicle_id: str, days: int) -> RentalRecord:
        """Rent a vehicle for a specified number of days.

        Args:
            vehicle_id: The unique identifier of the vehicle.
            days: Number of rental days.

        Returns:
            A RentalRecord for the transaction.

        Raises:
            ValueError: If the vehicle is not found, already rented,
                        or days is not positive.
        """
        vehicle = self._vehicles.get(vehicle_id)
        if vehicle is None:
            raise ValueError(f"Vehicle {vehicle_id} not found")
        if not vehicle.is_available:
            raise ValueError(f"Vehicle {vehicle_id} is already rented")
        if days <= 0:
            raise ValueError("Rental days must be positive")

        cost = calculate_rental_cost(vehicle, days)
        vehicle.is_available = False
        record = RentalRecord(vehicle, days, cost)
        self._active_rentals[vehicle_id] = record
        return record

    def return_vehicle(self, vehicle_id: str, overdue_days: int = 0) -> dict:
        """Return a rented vehicle and calculate any late fees.

        Args:
            vehicle_id: The unique identifier of the vehicle.
            overdue_days: Number of days the return is late (default 0).

        Returns:
            Dictionary with keys: vehicle, rental_days, rental_cost,
            overdue_days, late_fee, total_charge.

        Raises:
            ValueError: If the vehicle is not found or not currently rented.
        """
        vehicle = self._vehicles.get(vehicle_id)
        if vehicle is None:
            raise ValueError(f"Vehicle {vehicle_id} not found")
        if vehicle.is_available:
            raise ValueError(f"Vehicle {vehicle_id} is not currently rented")

        record = self._active_rentals.pop(vehicle_id)
        vehicle.is_available = True

        late_fee = calculate_late_fee(vehicle, overdue_days)
        total_charge = record.cost + late_fee

        return {
            "vehicle": vehicle,
            "rental_days": record.days,
            "rental_cost": record.cost,
            "overdue_days": overdue_days,
            "late_fee": late_fee,
            "total_charge": total_charge,
        }

    def get_active_rentals(self) -> list[RentalRecord]:
        """Return a list of all currently active rental records."""
        return list(self._active_rentals.values())
