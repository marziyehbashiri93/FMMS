"""Abstract repository interface for the Driver aggregate."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.driver.domain.entities import Driver, DriverStatus
from apps.driver.domain.value_objects import CustomerNumber


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
    def get_by_customer_number(self, customer_number: CustomerNumber) -> Driver:
        """Retrieve a driver by SAP customer number.

        Args:
            customer_number: The validated SAP ``CustomerNumber`` value object.

        Returns:
            The matching ``Driver`` aggregate.

        Raises:
            DriverNotFoundError: If no driver with this customer number exists.
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
    def list_all(self) -> list[Driver]:
        """Return all drivers, regardless of lifecycle status."""

    @abstractmethod
    def list_by_customer_numbers(self, customer_numbers: set[str]) -> list[Driver]:
        """Return drivers matching the provided SAP customer numbers."""

    @abstractmethod
    def decommission_missing_from_sap(self, seen_customer_numbers: set[str]) -> int:
        """Mark drivers absent from a SAP sync as DECOMMISSIONED."""

    @abstractmethod
    def save(self, driver: Driver) -> Driver:
        """Persist a new or updated driver aggregate.

        Args:
            driver: The ``Driver`` aggregate to save.

        Returns:
            The saved ``Driver`` aggregate.
        """
