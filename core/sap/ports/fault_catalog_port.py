"""SAP Fault Catalog Port — abstract contract for defect code access.

SAP maintains the authoritative catalog of defect codes used when recording
faults against fleet vehicles. FMMS reads these codes to populate inspection
and fault reporting forms.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.fault_catalog import SAPDefectCodeDTO


class ISAPFaultCatalogPort(ABC):
    """Business contract for reading defect codes from SAP's fault catalog.

    All transport and encoding details are the responsibility of the implementing
    adapter. This port exposes only business-meaningful operations.
    """

    @abstractmethod
    def list_defect_codes(self) -> list[SAPDefectCodeDTO]:
        """Retrieve defect codes.

        Returns:
            A list of ``SAPDefectCodeDTO`` objects. May be empty.

        Raises:
            SAPIntegrationError: If SAP returns an error response.
        """

    @abstractmethod
    def get_defect_code(
        self,
        code: str,
        code_group: str,
    ) -> SAPDefectCodeDTO:
        """Retrieve a single defect code from the SAP catalog.

        Args:
            code: The defect code identifier.
            code_group: SAP code group the code belongs to.

        Returns:
            A populated ``SAPDefectCodeDTO``.

        Raises:
            SAPIntegrationError: If SAP returns an error or the code is not found.
        """
