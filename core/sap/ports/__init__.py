"""SAP Port Interfaces (Abstractions).

These ABCs define the business contract between FMMS application services
and the SAP system. They contain no HTTP details, no OData URLs, and no
BAPI function names. All technology-specific details live in the infrastructure
adapters that implement these ports.

Application services import from this package only.
Infrastructure adapters implement these ABCs.
"""

from core.sap.ports.equipment_port import ISAPEquipmentPort
from core.sap.ports.fault_catalog_port import ISAPFaultCatalogPort
from core.sap.ports.goods_issue_port import ISAPGoodsIssuePort
from core.sap.ports.goods_receipt_port import ISAPGoodsReceiptPort
from core.sap.ports.inventory_port import ISAPInventoryPort
from core.sap.ports.material_port import ISAPMaterialPort
from core.sap.ports.object_part_catalog_port import ISAPObjectPartCatalogPort
from core.sap.ports.pm_notification_port import ISAPPMNotificationPort
from core.sap.ports.pm_order_port import ISAPPMOrderPort
from core.sap.ports.purchase_order_port import ISAPPurchaseOrderPort
from core.sap.ports.purchase_requisition_port import ISAPPurchaseRequisitionPort
from core.sap.ports.sap_transaction_manager_port import ISAPTransactionManager
from core.sap.ports.service_po_port import ISAPServicePOPort

__all__ = [
    "ISAPEquipmentPort",
    "ISAPFaultCatalogPort",
    "ISAPObjectPartCatalogPort",
    "ISAPMaterialPort",
    "ISAPInventoryPort",
    "ISAPPMNotificationPort",
    "ISAPPMOrderPort",
    "ISAPPurchaseRequisitionPort",
    "ISAPPurchaseOrderPort",
    "ISAPGoodsReceiptPort",
    "ISAPGoodsIssuePort",
    "ISAPServicePOPort",
    "ISAPTransactionManager",
]
