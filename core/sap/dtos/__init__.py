"""SAP Data Transfer Objects.

These DTOs represent the data contract between FMMS and SAP.
They are pure Python dataclasses — no ORM, no domain entities, no HTTP details.
Mapping between domain entities and these DTOs happens exclusively inside adapters.
"""

from core.sap.dtos.equipment import SAPEquipmentDTO
from core.sap.dtos.fault_catalog import SAPDefectCodeDTO
from core.sap.dtos.goods_issue import (
    GILineItemRequest,
    PostGoodsIssueRequest,
    SAPGoodsIssueDTO,
)
from core.sap.dtos.goods_receipt import (
    GRLineItemRequest,
    PostGoodsReceiptRequest,
    SAPGoodsReceiptDTO,
)
from core.sap.dtos.inventory import SAPStockDTO
from core.sap.dtos.material import SAPMaterialDTO
from core.sap.dtos.object_part_catalog import SAPObjectPartDTO
from core.sap.dtos.pm_notification import (
    CreatePMNotificationRequest,
    SAPNotificationDTO,
)
from core.sap.dtos.pm_order import CreatePMOrderRequest, SAPPMOrderDTO
from core.sap.dtos.purchase_order import (
    CreatePORequest,
    POLineItemRequest,
    SAPPurchaseOrderDTO,
)
from core.sap.dtos.purchase_requisition import (
    CreatePRRequest,
    PRLineItemRequest,
    SAPPRLineItemDTO,
    SAPPurchaseRequisitionDTO,
)
from core.sap.dtos.service_po import (
    CreateServicePORequest,
    SAPServicePODTO,
    ServiceLineItemRequest,
)

__all__ = [
    "SAPEquipmentDTO",
    "SAPDefectCodeDTO",
    "SAPObjectPartDTO",
    "SAPMaterialDTO",
    "SAPStockDTO",
    "CreatePMNotificationRequest",
    "SAPNotificationDTO",
    "CreatePMOrderRequest",
    "SAPPMOrderDTO",
    "PRLineItemRequest",
    "CreatePRRequest",
    "SAPPRLineItemDTO",
    "SAPPurchaseRequisitionDTO",
    "POLineItemRequest",
    "CreatePORequest",
    "SAPPurchaseOrderDTO",
    "GRLineItemRequest",
    "PostGoodsReceiptRequest",
    "SAPGoodsReceiptDTO",
    "GILineItemRequest",
    "PostGoodsIssueRequest",
    "SAPGoodsIssueDTO",
    "ServiceLineItemRequest",
    "CreateServicePORequest",
    "SAPServicePODTO",
]
