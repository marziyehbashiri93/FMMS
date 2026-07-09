"""Abstract repository interface for the Driver aggregate."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.value_objects import LicenseNumber


class IDriverRepository(ABC):
    """Port (interface) for persisting and retrieving Driver aggregates."""

    @abstractmethod
    def get_by_id(self, driver_id: uuid.UUID) -> Driver:
        """Retrieve a driver by its unique identifier.

        Args:
            driver_id: The UUID of the driver.

        Returns:
            The matching ``Driver`` aggregate.

        Raises:
            DriverNotFoundError: If no driver exists with this ID.
        """

    @abstractmethod
    def get_by_license(self, license_number: LicenseNumber) -> Driver:
        """Retrieve a driver by their license number.

        Args:
            license_number: The validated ``LicenseNumber`` value object.

        Returns:
            The matching ``Driver`` aggregate.

        Raises:
            DriverNotFoundError: If no driver with this license number exists.
        """

    @abstractmethod
    def get_by_vehicle(self, vehicle_id: uuid.UUID) -> Driver | None:
        """Retrieve the driver currently assigned to a vehicle.

        Args:
            vehicle_id: The UUID of the assigned vehicle.

        Returns:
            The assigned ``Driver`` aggregate, or ``None`` if unassigned.
        """

    @abstractmethod
    def list_by_status(self, status: DriverStatus) -> list[Driver]:
        """Return all drivers matching a given status.

        Args:
            status: The ``DriverStatus`` to filter by.

        Returns:
            A list of ``Driver`` aggregates.
        """

    @abstractmethod
    def exists_by_license(self, license_number: LicenseNumber) -> bool:
        """Check whether a driver with the given license number exists.

        Args:
            license_number: The license number to check.

        Returns:
            ``True`` if a driver with this license number exists.
        """

    @abstractmethod
    def save(self, driver: Driver) -> Driver:
        """Persist a new or updated driver aggregate.

        Args:
            driver: The ``Driver`` aggregate to save.

        Returns:
            The saved ``Driver`` aggregate.
        """

    @abstractmethod
    def delete(self, driver_id: uuid.UUID) -> None:
        """Soft-delete a driver record.

        Args:
            driver_id: The UUID of the driver to delete.

        Raises:
            DriverNotFoundError: If no driver exists with this ID.
        """
