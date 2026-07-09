"""Truck model with cargo-capacity-based pricing multipliers."""

from vehicle_rental.core import Vehicle


class Truck(Vehicle):
    """A truck vehicle whose rental cost is scaled by cargo capacity.

    Multiplier tiers:
        - ≤2000 kg   → ×1.0
        - ≤5000 kg   → ×1.3
        - ≤10000 kg  → ×1.6
        - >10000 kg  → ×2.0
    """

    def __init__(
        self,
        vehicle_id: str,
        make: str,
        model: str,
        year: int,
        daily_rate: float,
        capacity_kg: float = 1000,
    ):
        """Initialise a truck.

        Args:
            vehicle_id: Unique identifier.
            make: Manufacturer name.
            model: Model name.
            year: Manufacturing year.
            daily_rate: Base daily rental rate.
            capacity_kg: Maximum cargo capacity in kilograms.

        Raises:
            ValueError: If capacity_kg is not positive.
        """
        super().__init__(vehicle_id, make, model, year, daily_rate)
        if capacity_kg <= 0:
            raise ValueError("Cargo capacity must be positive")
        self._cargo_capacity_kg = float(capacity_kg)

    @property
    def cargo_capacity_kg(self) -> float:
        """Return the cargo capacity in kilograms."""
        return self._cargo_capacity_kg

    def _cargo_multiplier(self) -> float:
        """Return the pricing multiplier based on cargo capacity tier."""
        if self._cargo_capacity_kg <= 2000:
            return 1.0
        elif self._cargo_capacity_kg <= 5000:
            return 1.3
        elif self._cargo_capacity_kg <= 10000:
            return 1.6
        return 2.0

    def calculate_rental_cost(self, days: int) -> float:
        """Calculate rental cost as daily_rate × days × cargo multiplier.

        Args:
            days: Number of rental days.

        Returns:
            Total rounded cost.

        Raises:
            ValueError: If days is not positive.
        """
        if days <= 0:
            raise ValueError("Rental days must be positive")
        base = self._daily_rate * days * self._cargo_multiplier()
        return round(base, 2)

    def get_description(self) -> str:
        """Return a formatted description e.g. 'Truck (12000kg capacity) — 2025 Volvo VNL'."""
        return (
            f"Truck ({self._cargo_capacity_kg}kg capacity) — "
            f"{self._year} {self._make} {self._model}"
        )
