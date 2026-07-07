"""Command-line interface for the Vehicle Rental System."""

from vehicle_rental.modules import Car, Bike, Truck
from vehicle_rental.services.rental_service import RentalService


def _seed_data(service: RentalService) -> None:
    """Populate the rental service with a default set of vehicles."""
    vehicles = [
        Car("C001", "Toyota", "Camry", 2023, 40.0, "standard"),
        Car("C002", "Honda", "CR-V", 2024, 55.0, "suv"),
        Car("C003", "Mercedes", "S-Class", 2025, 120.0, "luxury"),
        Bike("B001", "Schwinn", "Cruiser", 2023, 15.0, "standard"),
        Bike("B002", "Trek", "Mountain", 2024, 25.0, "electric"),
        Truck("T001", "Ford", "F-150", 2023, 70.0, capacity_kg=1500),
        Truck("T002", "Volvo", "VNL", 2025, 120.0, capacity_kg=12000),
    ]
    for vehicle in vehicles:
        service.register_vehicle(vehicle)


def main() -> None:
    """Run the interactive Vehicle Rental System CLI."""
    service = RentalService()
    _seed_data(service)

    while True:
        print("\n=== VEHICLE RENTAL SYSTEM ===")
        print("1. Show available vehicles")
        print("2. Show all vehicles")
        print("3. Rent a vehicle")
        print("4. Return a vehicle")
        print("5. Show active rentals")
        print("6. Exit")

        choice = input("Select an option: ").strip()

        if choice == "1":
            available = service.get_available_vehicles()
            if not available:
                print("No vehicles available at the moment.")
            else:
                for vehicle in available:
                    print(f"  {vehicle}")

        elif choice == "2":
            for vehicle in service.get_all_vehicles():
                print(f"  {vehicle}")

        elif choice == "3":
            vehicle_id = input("Enter vehicle ID: ").strip()
            days_input = input("Enter rental days: ").strip()
            if not days_input.isdigit() or int(days_input) <= 0:
                print("Invalid number of days.")
                continue
            try:
                record = service.rent_vehicle(vehicle_id, int(days_input))
                print(f"Rented {record.vehicle.get_description()} for {record.days} days.")
                print(f"Total cost: ${record.cost:.2f}")
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "4":
            vehicle_id = input("Enter vehicle ID: ").strip()
            overdue_input = input("Enter overdue days (0 if on time): ").strip()
            overdue = int(overdue_input) if overdue_input.isdigit() else 0
            try:
                result = service.return_vehicle(vehicle_id, overdue)
                print(f"Returned {result['vehicle'].get_description()}.")
                print(f"  Rental cost:  ${result['rental_cost']:.2f}")
                print(f"  Late fee:     ${result['late_fee']:.2f}")
                print(f"  Total charge: ${result['total_charge']:.2f}")
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "5":
            rentals = service.get_active_rentals()
            if not rentals:
                print("No active rentals.")
            else:
                for record in rentals:
                    print(f"  {record}")

        elif choice == "6":
            print("Goodbye!")
            break

        else:
            print("Invalid option. Try again.")


if __name__ == "__main__":
    main()
