"""Abstract base class defining the contract for all vehicle types."""

from abc import ABC, abstractmethod


class Vehicle(ABC):
    """Abstract base class for all vehicles in the rental system.

    Each vehicle has an identifier, make, model, year, daily rental rate,
    and availability state. Subclasses must implement pricing and description.
    """

    def __init__(self, vehicle_id: str, make: str, model: str, year: int, daily_rate: float):
        """Initialise a vehicle.

        Args:
            vehicle_id: Unique identifier for the vehicle.
            make: Manufacturer name.
            model: Model name.
            year: Manufacturing year.
            daily_rate: Base daily rental rate in dollars.
        """
        self._vehicle_id = vehicle_id
        self._make = make
        self._model = model
        self._year = year
        self._daily_rate = daily_rate
        self._is_available = True

    @property
    def vehicle_id(self) -> str:
        """Return the unique vehicle identifier."""
        return self._vehicle_id

    @property
    def make(self) -> str:
        """Return the vehicle manufacturer."""
        return self._make

    @property
    def model(self) -> str:
        """Return the vehicle model name."""
        return self._model

    @property
    def year(self) -> int:
        """Return the manufacturing year."""
        return self._year

    @property
    def daily_rate(self) -> float:
        """Return the base daily rental rate."""
        return self._daily_rate

    @daily_rate.setter
    def daily_rate(self, value: float) -> None:
        """Set the base daily rental rate. Must be positive."""
        if value <= 0:
            raise ValueError("Daily rate must be positive")
        self._daily_rate = value

    @property
    def is_available(self) -> bool:
        """Return whether the vehicle is currently available for rent."""
        return self._is_available

    @is_available.setter
    def is_available(self, value: bool) -> None:
        """Set the availability state of the vehicle."""
        self._is_available = value

    @abstractmethod
    def calculate_rental_cost(self, days: int) -> float:
        """Calculate the total rental cost for a given number of days.

        Args:
            days: Number of rental days.

        Returns:
            Total cost rounded to two decimal places.
        """

    @abstractmethod
    def get_description(self) -> str:
        """Return a human-readable description of the vehicle."""

    def to_dict(self) -> dict:
        """Serialise the vehicle to a dictionary."""
        return {
            "vehicle_id": self._vehicle_id,
            "make": self._make,
            "model": self._model,
            "year": self._year,
            "daily_rate": self._daily_rate,
            "is_available": self._is_available,
            "type": self.__class__.__name__,
        }

    def __str__(self) -> str:
        status = "Available" if self._is_available else "Rented"
        return (
            f"[{self.__class__.__name__}] {self._vehicle_id}: "
            f"{self._year} {self._make} {self._model} "
            f"(${self._daily_rate:.2f}/day) - {status}"
        )
