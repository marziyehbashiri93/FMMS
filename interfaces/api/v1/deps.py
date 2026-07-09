"""Composition root for REST API v1 services.

This module is the sole API-layer location that imports concrete repositories
and SAP adapters. Views consume only the factories defined here.
"""

from __future__ import annotations

from apps.driver.application.services.assign_driver_to_vehicle_service import (
    AssignDriverToVehicleService,
)
from apps.driver.application.services.get_driver_service import (
    GetDriverService,
    ListDriversService,
)
from apps.driver.application.services.register_driver_service import (
    RegisterDriverService,
)
from apps.driver.application.services.suspend_driver_service import SuspendDriverService
from apps.driver.infrastructure.repositories import DjangoDriverRepository
from apps.fault.application.services.assign_fault_service import AssignFaultService
from apps.fault.application.services.close_fault_service import CloseFaultService
from apps.fault.application.services.get_fault_service import (
    GetFaultService,
    ListFaultsService,
)
from apps.fault.application.services.report_fault_service import ReportFaultService
from apps.fault.infrastructure.repositories import DjangoFaultRepository
from apps.inspection.application.services.add_inspection_item_service import (
    AddInspectionItemService,
)
from apps.inspection.application.services.create_inspection_service import (
    CreateInspectionService,
)
from apps.inspection.application.services.get_inspection_service import (
    GetInspectionService,
    ListInspectionsService,
)
from apps.inspection.application.services.submit_inspection_service import (
    SubmitInspectionService,
)
from apps.inspection.infrastructure.repositories import DjangoInspectionRepository
from apps.integration.infrastructure.repositories import DjangoSAPTransactionRepository
from apps.preventive_maintenance.application.services.complete_pm_work_order_service import (
    CompletePMWorkOrderService,
)
from apps.preventive_maintenance.application.services.create_pm_plan_service import (
    CreatePMPlanService,
)
from apps.preventive_maintenance.application.services.get_pm_service import (
    GetPMPlanService,
    ListPMPlansService,
    ListPMWorkOrdersService,
)
from apps.preventive_maintenance.application.services.trigger_pm_work_order_service import (
    TriggerPMWorkOrderService,
)
from apps.preventive_maintenance.infrastructure.repositories import (
    DjangoPMPlanRepository,
    DjangoPMWorkOrderRepository,
)
from apps.procurement.application.services.add_pr_line_item_service import (
    AddPRLineItemService,
)
from apps.procurement.application.services.create_purchase_requisition_service import (
    CreatePurchaseRequisitionService,
)
from apps.procurement.application.services.get_procurement_service import (
    GetPurchaseOrderService,
    GetPurchaseRequisitionService,
    ListPurchaseRequisitionsService,
)
from apps.procurement.application.services.receive_po_from_sap_service import (
    ReceivePOFromSAPService,
)
from apps.procurement.application.services.submit_pr_to_sap_service import (
    SubmitPRToSAPService,
)
from apps.procurement.infrastructure.repositories import (
    DjangoPurchaseOrderRepository,
    DjangoPurchaseRequisitionRepository,
)
from apps.repair.application.services.add_repair_activity_service import (
    AddRepairActivityService,
    AddRepairPartService,
)
from apps.repair.application.services.assign_repair_order_service import (
    AssignRepairOrderService,
)
from apps.repair.application.services.create_repair_order_service import (
    CreateRepairOrderService,
)
from apps.repair.application.services.get_repair_order_service import (
    GetRepairOrderService,
    ListRepairOrdersService,
)
from apps.repair.application.services.sync_repair_to_sap_service import (
    SyncRepairToSAPService,
)
from apps.repair.application.services.update_repair_status_service import (
    CancelRepairOrderService,
    CompleteRepairOrderService,
    StartRepairService,
)
from apps.repair.infrastructure.repositories import DjangoRepairOrderRepository
from apps.vehicle.application.services.create_vehicle_service import (
    CreateVehicleService,
)
from apps.vehicle.application.services.deactivate_vehicle_service import (
    DeactivateVehicleService,
)
from apps.vehicle.application.services.get_vehicle_service import (
    GetVehicleService,
    ListVehiclesService,
)
from apps.vehicle.application.services.sync_sap_equipment_service import (
    SyncSAPEquipmentService,
)
from apps.vehicle.application.services.update_vehicle_service import (
    UpdateVehicleService,
)
from apps.vehicle.infrastructure.repositories import DjangoVehicleRepository
from infrastructure.sap.adapters.bapi.pm_notification_bapi_adapter import (
    PMNotificationBAPIAdapter,
)
from infrastructure.sap.adapters.bapi.pm_order_bapi_adapter import PMOrderBAPIAdapter
from infrastructure.sap.adapters.bapi.purchase_requisition_bapi_adapter import (
    PurchaseRequisitionBAPIAdapter,
)
from infrastructure.sap.adapters.odata.equipment_odata_adapter import (
    EquipmentODataAdapter,
)
from infrastructure.sap.client.mock.mock_client import MockSAPClient
from infrastructure.sap.config import SAPConfig


def _sap_client() -> MockSAPClient:
    """Build the default mock SAP client for API composition.

    Returns:
        A ``MockSAPClient`` when ``SAP_USE_MOCK`` is enabled.

    Raises:
        RuntimeError: If mock mode is disabled for this composition root.
    """
    config = SAPConfig.from_env()
    if not config.use_mock:
        raise RuntimeError(
            "The API v1 composition root currently requires SAP_USE_MOCK=True."
        )
    return MockSAPClient()


def get_vehicle_repository() -> DjangoVehicleRepository:
    """Return the vehicle repository."""
    return DjangoVehicleRepository()


def get_driver_repository() -> DjangoDriverRepository:
    """Return the driver repository."""
    return DjangoDriverRepository()


def get_inspection_repository() -> DjangoInspectionRepository:
    """Return the inspection repository."""
    return DjangoInspectionRepository()


def get_fault_repository() -> DjangoFaultRepository:
    """Return the fault repository."""
    return DjangoFaultRepository()


def get_repair_order_repository() -> DjangoRepairOrderRepository:
    """Return the repair-order repository."""
    return DjangoRepairOrderRepository()


def get_pm_plan_repository() -> DjangoPMPlanRepository:
    """Return the PM-plan repository."""
    return DjangoPMPlanRepository()


def get_pm_work_order_repository() -> DjangoPMWorkOrderRepository:
    """Return the PM-work-order repository."""
    return DjangoPMWorkOrderRepository()


def get_purchase_requisition_repository() -> DjangoPurchaseRequisitionRepository:
    """Return the purchase-requisition repository."""
    return DjangoPurchaseRequisitionRepository()


def get_purchase_order_repository() -> DjangoPurchaseOrderRepository:
    """Return the purchase-order repository."""
    return DjangoPurchaseOrderRepository()


def get_sap_transaction_repository() -> DjangoSAPTransactionRepository:
    """Return the SAP transaction repository."""
    return DjangoSAPTransactionRepository()


def get_create_vehicle_service() -> CreateVehicleService:
    """Return CreateVehicleService."""
    return CreateVehicleService(get_vehicle_repository())


def get_update_vehicle_service() -> UpdateVehicleService:
    """Return UpdateVehicleService."""
    return UpdateVehicleService(get_vehicle_repository())


def get_deactivate_vehicle_service() -> DeactivateVehicleService:
    """Return DeactivateVehicleService."""
    return DeactivateVehicleService(
        get_vehicle_repository(),
        get_repair_order_repository(),
    )


def get_sync_sap_equipment_service() -> SyncSAPEquipmentService:
    """Return SyncSAPEquipmentService."""
    return SyncSAPEquipmentService(
        get_vehicle_repository(),
        EquipmentODataAdapter(_sap_client()),
    )


def get_get_vehicle_service() -> GetVehicleService:
    """Return GetVehicleService."""
    return GetVehicleService(get_vehicle_repository())


def get_list_vehicles_service() -> ListVehiclesService:
    """Return ListVehiclesService."""
    return ListVehiclesService(get_vehicle_repository())


def get_register_driver_service() -> RegisterDriverService:
    """Return RegisterDriverService."""
    return RegisterDriverService(get_driver_repository())


def get_get_driver_service() -> GetDriverService:
    """Return GetDriverService."""
    return GetDriverService(get_driver_repository())


def get_list_drivers_service() -> ListDriversService:
    """Return ListDriversService."""
    return ListDriversService(get_driver_repository())


def get_assign_driver_to_vehicle_service() -> AssignDriverToVehicleService:
    """Return AssignDriverToVehicleService."""
    return AssignDriverToVehicleService(
        get_driver_repository(),
        get_vehicle_repository(),
    )


def get_suspend_driver_service() -> SuspendDriverService:
    """Return SuspendDriverService."""
    return SuspendDriverService(get_driver_repository())


def get_create_inspection_service() -> CreateInspectionService:
    """Return CreateInspectionService."""
    return CreateInspectionService(
        get_inspection_repository(),
        get_vehicle_repository(),
    )


def get_get_inspection_service() -> GetInspectionService:
    """Return GetInspectionService."""
    return GetInspectionService(get_inspection_repository())


def get_list_inspections_service() -> ListInspectionsService:
    """Return ListInspectionsService."""
    return ListInspectionsService(get_inspection_repository())


def get_add_inspection_item_service() -> AddInspectionItemService:
    """Return AddInspectionItemService."""
    return AddInspectionItemService(get_inspection_repository())


def get_submit_inspection_service() -> SubmitInspectionService:
    """Return SubmitInspectionService."""
    return SubmitInspectionService(
        get_inspection_repository(),
        get_fault_repository(),
    )


def get_report_fault_service() -> ReportFaultService:
    """Return ReportFaultService."""
    return ReportFaultService(get_fault_repository(), get_vehicle_repository())


def get_get_fault_service() -> GetFaultService:
    """Return GetFaultService."""
    return GetFaultService(get_fault_repository())


def get_list_faults_service() -> ListFaultsService:
    """Return ListFaultsService."""
    return ListFaultsService(get_fault_repository())


def get_assign_fault_service() -> AssignFaultService:
    """Return AssignFaultService."""
    return AssignFaultService(get_fault_repository())


def get_close_fault_service() -> CloseFaultService:
    """Return CloseFaultService."""
    return CloseFaultService(get_fault_repository())


def get_create_repair_order_service() -> CreateRepairOrderService:
    """Return CreateRepairOrderService."""
    return CreateRepairOrderService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_fault_repository(),
    )


def get_get_repair_order_service() -> GetRepairOrderService:
    """Return GetRepairOrderService."""
    return GetRepairOrderService(get_repair_order_repository())


def get_list_repair_orders_service() -> ListRepairOrdersService:
    """Return ListRepairOrdersService."""
    return ListRepairOrdersService(get_repair_order_repository())


def get_assign_repair_order_service() -> AssignRepairOrderService:
    """Return AssignRepairOrderService."""
    return AssignRepairOrderService(get_repair_order_repository())


def get_start_repair_service() -> StartRepairService:
    """Return StartRepairService."""
    return StartRepairService(get_repair_order_repository())


def get_complete_repair_order_service() -> CompleteRepairOrderService:
    """Return CompleteRepairOrderService."""
    return CompleteRepairOrderService(get_repair_order_repository())


def get_cancel_repair_order_service() -> CancelRepairOrderService:
    """Return CancelRepairOrderService."""
    return CancelRepairOrderService(get_repair_order_repository())


def get_add_repair_activity_service() -> AddRepairActivityService:
    """Return AddRepairActivityService."""
    return AddRepairActivityService(get_repair_order_repository())


def get_add_repair_part_service() -> AddRepairPartService:
    """Return AddRepairPartService."""
    return AddRepairPartService(get_repair_order_repository())


def get_sync_repair_to_sap_service() -> SyncRepairToSAPService:
    """Return SyncRepairToSAPService."""
    return SyncRepairToSAPService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        PMOrderBAPIAdapter(_sap_client()),
    )


def get_create_pm_plan_service() -> CreatePMPlanService:
    """Return CreatePMPlanService."""
    return CreatePMPlanService(get_pm_plan_repository(), get_vehicle_repository())


def get_get_pm_plan_service() -> GetPMPlanService:
    """Return GetPMPlanService."""
    return GetPMPlanService(get_pm_plan_repository())


def get_list_pm_plans_service() -> ListPMPlansService:
    """Return ListPMPlansService."""
    return ListPMPlansService(get_pm_plan_repository())


def get_list_pm_work_orders_service() -> ListPMWorkOrdersService:
    """Return ListPMWorkOrdersService."""
    return ListPMWorkOrdersService(get_pm_work_order_repository())


def get_trigger_pm_work_order_service() -> TriggerPMWorkOrderService:
    """Return TriggerPMWorkOrderService."""
    return TriggerPMWorkOrderService(
        get_pm_plan_repository(),
        get_pm_work_order_repository(),
        get_vehicle_repository(),
        PMNotificationBAPIAdapter(_sap_client()),
    )


def get_complete_pm_work_order_service() -> CompletePMWorkOrderService:
    """Return CompletePMWorkOrderService."""
    return CompletePMWorkOrderService(get_pm_work_order_repository())


def get_create_purchase_requisition_service() -> CreatePurchaseRequisitionService:
    """Return CreatePurchaseRequisitionService."""
    return CreatePurchaseRequisitionService(
        get_purchase_requisition_repository(),
        get_repair_order_repository(),
    )


def get_get_purchase_requisition_service() -> GetPurchaseRequisitionService:
    """Return GetPurchaseRequisitionService."""
    return GetPurchaseRequisitionService(get_purchase_requisition_repository())


def get_list_purchase_requisitions_service() -> ListPurchaseRequisitionsService:
    """Return ListPurchaseRequisitionsService."""
    return ListPurchaseRequisitionsService(get_purchase_requisition_repository())


def get_add_pr_line_item_service() -> AddPRLineItemService:
    """Return AddPRLineItemService."""
    return AddPRLineItemService(get_purchase_requisition_repository())


def get_submit_pr_to_sap_service() -> SubmitPRToSAPService:
    """Return SubmitPRToSAPService."""
    return SubmitPRToSAPService(
        get_purchase_requisition_repository(),
        get_sap_transaction_repository(),
        PurchaseRequisitionBAPIAdapter(_sap_client()),
    )


def get_get_purchase_order_service() -> GetPurchaseOrderService:
    """Return GetPurchaseOrderService."""
    return GetPurchaseOrderService(get_purchase_order_repository())


def get_receive_po_from_sap_service() -> ReceivePOFromSAPService:
    """Return ReceivePOFromSAPService."""
    return ReceivePOFromSAPService(
        get_purchase_requisition_repository(),
        get_purchase_order_repository(),
    )
