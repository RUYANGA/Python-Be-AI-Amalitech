"""Bike model with type-based pricing multipliers."""

from vehicle_rental.core import Vehicle


class Bike(Vehicle):
    """A bike vehicle with a specific bike type affecting its rental cost.

    Supported types: standard (×1.0), electric (×1.4).
    """

    VALID_TYPES = ("standard", "electric")
    TYPE_MULTIPLIERS: dict[str, float] = {"standard": 1.0, "electric": 1.4}

    def __init__(
        self,
        vehicle_id: str,
        make: str,
        model: str,
        year: int,
        daily_rate: float,
        bike_type: str = "standard",
    ):
        """Initialise a bike.

        Args:
            vehicle_id: Unique identifier.
            make: Manufacturer name.
            model: Model name.
            year: Manufacturing year.
            daily_rate: Base daily rental rate.
            bike_type: One of 'standard' or 'electric'.

        Raises:
            ValueError: If bike_type is not recognised.
        """
        super().__init__(vehicle_id, make, model, year, daily_rate)
        if bike_type.lower() not in self.VALID_TYPES:
            raise ValueError(
                f"Invalid bike type: {bike_type}. Valid: {self.VALID_TYPES}"
            )
        self._bike_type = bike_type.lower()

    @property
    def bike_type(self) -> str:
        """Return the bike type classification."""
        return self._bike_type

    def _type_multiplier(self) -> float:
        """Return the pricing multiplier for the current bike type."""
        return self.TYPE_MULTIPLIERS[self._bike_type]

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
        """Return a formatted description e.g. 'Electric Bike — 2024 Trek Mountain'."""
        return f"{self._bike_type.capitalize()} Bike — {self._year} {self._make} {self._model}"
