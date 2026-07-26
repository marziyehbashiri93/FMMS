"""Query-side service for driver dashboard summary cards."""

from __future__ import annotations

from apps.driver.application.dto.driver_dto import DriverSummaryDTO
from apps.driver.application.interfaces.driver_summary_reader import (
    IDriverSummaryReader,
)


class GetDriverSummaryService:
    """Build summary values required by the driver dashboard."""

    def __init__(self, summary_reader: IDriverSummaryReader | None = None) -> None:
        if summary_reader is None:
            from apps.driver.infrastructure.summary_readers import (
                DjangoDriverSummaryReader,
            )

            summary_reader = DjangoDriverSummaryReader()
        self._summary_reader = summary_reader

    def execute(self) -> DriverSummaryDTO:
        """Return driver dashboard summary values.

        Returns:
            ``DriverSummaryDTO`` with active, decommissioned, and assigned
            driver counts plus the latest successful vehicles SAP sync time.
        """
        return self._summary_reader.get_summary()
