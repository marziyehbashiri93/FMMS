"""Abstract repository interface for the Vehicle aggregate.

Defines the contract between the Application Service layer and the
Infrastructure layer. Concrete implementations live in
``apps/vehicle/infrastructure/repositories.py``.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from apps.vehicle.domain.entities import Vehicle, VehicleStatus
from apps.vehicle.domain.value_objects import PlateNumber, SAPVehicleNumber


class IVehicleRepository(ABC):
    """Port (interface) for persisting and retrieving Vehicle aggregates.

    All concrete implementations must satisfy this contract. The domain
    and application layers depend only on this abstraction — never on
    Django ORM or any specific storage technology.
    """

    @abstractmethod
    def get_by_id(self, vehicle_id: uuid.UUID) -> Vehicle:
        """Retrieve a vehicle by its unique identifier.

        Args:
            vehicle_id: The UUID of the vehicle to retrieve.

        Returns:
            The matching ``Vehicle`` aggregate.

        Raises:
            VehicleNotFoundError: If no vehicle exists with this ID.
        """

    @abstractmethod
    def get_by_plate(self, plate_number: PlateNumber) -> Vehicle:
        """Retrieve a vehicle by its plate number.

        Args:
            plate_number: The validated ``PlateNumber`` value object.

        Returns:
            The matching ``Vehicle`` aggregate.

        Raises:
            VehicleNotFoundError: If no vehicle exists with this plate number.
        """

    @abstractmethod
    def get_by_vehicle_number(
        self, vehicle_number: SAPVehicleNumber, include_deleted: bool = False
    ) -> Vehicle | None:
        """Retrieve a vehicle by its SAP VehicleNumber, if linked.

        Args:
            vehicle_number: Validated SAP VehicleNumber.

        Returns:
            The matching ``Vehicle`` aggregate, or ``None`` if not linked.
        """

    def list_vehicle_numbers(self) -> set[str]:
        """Return SAP VehicleNumber values stored locally, including soft-deleted rows."""
        return set()

    @abstractmethod
    def list_active(self) -> list[Vehicle]:
        """Return all vehicles with ACTIVE status.

        Returns:
            A list of ``Vehicle`` aggregates. Empty list if none exist.
        """

    @abstractmethod
    def list_by_status(self, status: VehicleStatus) -> list[Vehicle]:
        """Return all vehicles matching a given status.

        Args:
            status: The ``VehicleStatus`` to filter by.

        Returns:
            A list of ``Vehicle`` aggregates. Empty list if none match.
        """

    @abstractmethod
    def exists_by_plate(self, plate_number: PlateNumber) -> bool:
        """Check whether a vehicle with the given plate number already exists.

        Args:
            plate_number: The plate number to check for uniqueness.

        Returns:
            ``True`` if a vehicle with this plate number exists, else ``False``.
        """

    @abstractmethod
    def save(self, vehicle: Vehicle) -> Vehicle:
        """Persist a new or updated vehicle aggregate.

        Args:
            vehicle: The ``Vehicle`` aggregate to save.

        Returns:
            The saved ``Vehicle`` aggregate (may include DB-assigned fields).
        """

    @abstractmethod
    def delete(self, vehicle_id: uuid.UUID) -> None:
        """Soft-delete a vehicle record.

        Args:
            vehicle_id: The UUID of the vehicle to delete.

        Raises:
            VehicleNotFoundError: If no vehicle exists with this ID.
        """

    def decommission_missing_from_sap(self, seen_vehicle_numbers: set[str]) -> int:
        """Soft-delete vehicles whose SAP VehicleNumber is absent from a sync."""
        del seen_vehicle_numbers
        return 0

    def record_driver_assignment_snapshot(
        self,
        *,
        vehicle: Vehicle,
        sync_run_id: uuid.UUID,
        synced_at: datetime,
        request_id: str = "",
    ) -> None:
        """Persist a two-role SAP driver assignment snapshot for one vehicle."""
        del vehicle, sync_run_id, synced_at, request_id
