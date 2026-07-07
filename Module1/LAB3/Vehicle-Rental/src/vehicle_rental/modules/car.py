"""Car model with type-based pricing multipliers."""

from vehicle_rental.core import Vehicle


class Car(Vehicle):
    """A car vehicle with a specific car type affecting its rental cost.

    Supported types: standard (×1.0), suv (×1.3), luxury (×1.8).
    """

    VALID_TYPES = ("standard", "suv", "luxury")

    def __init__(self, vehicle_id: str, make: str, model: str, year: int,
                 daily_rate: float, car_type: str = "standard"):
        """Initialise a car.

        Args:
            vehicle_id: Unique identifier.
            make: Manufacturer name.
            model: Model name.
            year: Manufacturing year.
            daily_rate: Base daily rental rate.
            car_type: One of 'standard', 'suv', or 'luxury'.

        Raises:
            ValueError: If car_type is not recognised.
        """
        super().__init__(vehicle_id, make, model, year, daily_rate)
        if car_type.lower() not in self.VALID_TYPES:
            raise ValueError(f"Invalid car type: {car_type}. Valid: {self.VALID_TYPES}")
        self._car_type = car_type.lower()

    @property
    def car_type(self) -> str:
        """Return the car type classification."""
        return self._car_type

    def _type_multiplier(self) -> float:
        """Return the pricing multiplier for the current car type."""
        multipliers = {"standard": 1.0, "suv": 1.3, "luxury": 1.8}
        return multipliers[self._car_type]

    def calculate_rental_cost(self, days: int) -> float:
        """Calculate rental cost as daily_rate × days × type multiplier.

        Args:
            days: Number of rental days.

        Returns:
            Total rounded cost.

        Raises:
            ValueError: If days is not positive.
        """
        if days <= 0:
            raise ValueError("Rental days must be positive")
        base = self._daily_rate * days * self._type_multiplier()
        return round(base, 2)

    def get_description(self) -> str:
        """Return a formatted description e.g. 'Suv Car — 2024 Honda CR-V'."""
        return (
            f"{self._car_type.capitalize()} Car — {self._year} {self._make} {self._model}"
        )
