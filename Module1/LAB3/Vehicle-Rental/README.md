# Vehicle Rental System

A Python CLI application for managing vehicle rentals. Supports **Car**, **Bike**, and **Truck** rentals with type-based pricing multipliers and late-fee calculation.

## Features

- Register and manage a fleet of vehicles
- Rent vehicles by ID for a specified number of days
- Return vehicles with optional overdue-day late fees
- View available, all, or actively rented vehicles
- Vehicle-specific pricing multipliers:
  - **Car**: standard (×1.0), suv (×1.3), luxury (×1.8)
  - **Bike**: standard (×1.0), electric (×1.4)
  - **Truck**: based on cargo capacity (×1.0 – ×2.0)

## Project Structure

```
.
├── pyproject.toml
├── README.md
├── src/
│   └── vehicle_rental/
│       ├── __init__.py
│       ├── main.py                  # CLI entry point
│       ├── core/
│       │   ├── __init__.py
│       │   └── vehicle.py           # Abstract Vehicle base class
│       ├── modules/
│       │   ├── __init__.py
│       │   ├── car.py
│       │   ├── bike.py
│       │   └── truck.py
│       └── services/
│           ├── __init__.py
│           ├── pricing.py           # Pricing utilities
│           └── rental_service.py    # Core rental logic
└── tests/
    └── __init__.py
```

## Setup

Requires Python ≥3.12.

```bash
cd Vehicle-Rental
pip install -e .
```

Or run directly without installation:

```bash
cd Vehicle-Rental/src
python3 -m vehicle_rental.main
```

## Usage

Run the CLI:

```bash
python3 -m vehicle_rental.main
```

### Sample Session

```
=== VEHICLE RENTAL SYSTEM ===
1. Show available vehicles
2. Show all vehicles
3. Rent a vehicle
4. Return a vehicle
5. Show active rentals
6. Exit
Select an option: 1

  [Car] C001: 2023 Toyota Camry ($40.00/day) - Available
  [Car] C002: 2024 Honda CR-V ($55.00/day) - Available
  [Car] C003: 2025 Mercedes S-Class ($120.00/day) - Available
  [Bike] B001: 2023 Schwinn Cruiser ($15.00/day) - Available
  [Bike] B002: 2024 Trek Mountain ($25.00/day) - Available
  [Truck] T001: 2023 Ford F-150 ($70.00/day) - Available
  [Truck] T002: 2025 Volvo VNL ($120.00/day) - Available
```

#### Renting a vehicle

```
Select an option: 3
Enter vehicle ID: C001
Enter rental days: 3
Rented Standard Car — 2023 Toyota Camry for 3 days.
Total cost: $120.00
```

#### Viewing active rentals

```
Select an option: 5
  RentalRecord(C001, 3d, $120.00)
```

#### Returning a vehicle (with late fee)

```
Select an option: 4
Enter vehicle ID: C001
Enter overdue days (0 if on time): 2
Returned Standard Car — 2023 Toyota Camry.
  Rental cost:  $120.00
  Late fee:     $120.00
  Total charge: $240.00
```

## Running Tests

```bash
cd Vehicle-Rental/src
python3 -c "
from vehicle_rental.modules import Car, Bike, Truck
from vehicle_rental.services.rental_service import RentalService

# Create vehicles
c = Car('C001', 'Toyota', 'Camry', 2023, 40.0, 'standard')
b = Bike('B001', 'Schwinn', 'Cruiser', 2023, 15.0, 'standard')
t = Truck('T001', 'Ford', 'F-150', 2023, 70.0, capacity_kg=1500)

# Test rental cost
assert c.calculate_rental_cost(3) == 120.0
assert b.calculate_rental_cost(2) == 30.0
assert t.calculate_rental_cost(5) == 350.0

# Test full workflow
svc = RentalService()
svc.register_vehicle(c)
svc.register_vehicle(b)
record = svc.rent_vehicle('C001', 3)
result = svc.return_vehicle('C001', 2)
assert result['total_charge'] == 240.0
print('All tests passed!')
"
```
