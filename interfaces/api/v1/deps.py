"""Composition root for REST API v1 services.

This module is the sole API-layer location that imports concrete repositories
and SAP adapters. Views consume only the factories defined here.
"""

from __future__ import annotations

from apps.authentication.infrastructure.user_profile_reader import (
    DjangoUserProfileReader,
)
from apps.driver.application.services.get_driver_service import (
    GetDriverService,
    ListDriversService,
)
from apps.driver.infrastructure.repositories import DjangoDriverRepository
from apps.fault.application.services.assign_fault_service import AssignFaultService
from apps.fault.application.services.close_fault_service import CloseFaultService
from apps.fault.application.services.get_fault_service import (
    GetFaultService,
    ListFaultsService,
)
from apps.fault.application.services.report_fault_service import ReportFaultService
from apps.fault.infrastructure.repositories import DjangoFaultRepository
from apps.handover.application.services.handover_service import (
    ConfirmVehicleHandoverService,
    CreateVehicleHandoverService,
    ListVehicleHandoversService,
)
from apps.handover.infrastructure.repositories import DjangoVehicleHandoverRepository
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
from apps.inspection.application.services.sync_inspection_templates_from_sap_service import (
    ListInspectionTemplatesService,
    SyncInspectionTemplatesFromSAPService,
)
from apps.inspection.infrastructure.repositories import DjangoInspectionRepository
from apps.inspection.infrastructure.template_repositories import (
    DjangoInspectionTemplateRepository,
)
from apps.integration.application.services.retry_failed_sap_transactions_service import (
    RetryFailedSAPTransactionsService,
)
from apps.integration.application.services.run_sap_sync_service import RunSAPSyncService
from apps.integration.infrastructure.repositories import DjangoSAPTransactionRepository
from apps.material.application.services.material_request_service import (
    ApproveMaterialRequestService,
    CreateMaterialRequestService,
    ListMaterialRequestsService,
    RejectMaterialRequestService,
)
from apps.material.infrastructure.inventory_adapter import (
    StubInventoryAvailabilityAdapter,
)
from apps.material.infrastructure.repositories import (
    DjangoInventoryTransactionRepository,
    DjangoMaterialRequestRepository,
)
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
from apps.preventive_maintenance.application.services.trigger_overdue_pm_work_orders_service import (
    TriggerOverduePMWorkOrdersService,
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
from apps.repair.application.services.approve_repair_order_service import (
    AcceptRepairOrderService,
    ApproveRepairOrderService,
    AssignWorkshopService,
    RejectRepairOrderService,
)
from apps.repair.application.services.assign_repair_order_service import (
    AssignRepairOrderService,
)
from apps.repair.application.services.create_repair_order_service import (
    CreateRepairOrderService,
)
from apps.repair.application.services.external_invoice_service import (
    ApproveExternalInvoiceService,
    ListExternalInvoicesService,
    UploadExternalInvoiceService,
)
from apps.repair.application.services.get_repair_order_service import (
    GetRepairOrderService,
    ListRepairOrdersService,
)
from apps.repair.application.services.repair_order_timeline_service import (
    GetRepairOrderTimelineService,
    RecordRepairOrderEventService,
)
from apps.repair.application.services.sync_repair_to_sap_service import (
    SyncRepairToSAPService,
)
from apps.repair.application.services.transport_handover_decision_service import (
    ApproveTransportHandoverService,
    RejectTransportHandoverService,
)
from apps.repair.application.services.update_repair_status_service import (
    CancelRepairOrderService,
    CompleteRepairOrderService,
    StartRepairService,
)
from apps.repair.infrastructure.event_repositories import (
    DjangoRepairOrderEventRepository,
)
from apps.repair.infrastructure.invoice_repositories import (
    DjangoExternalRepairInvoiceRepository,
)
from apps.repair.infrastructure.repositories import DjangoRepairOrderRepository
from apps.vehicle.application.services.change_vehicle_status_service import (
    ChangeVehicleStatusService,
)
from apps.vehicle.application.services.get_vehicle_service import (
    GetVehicleService,
    ListVehiclesService,
)
from apps.vehicle.application.services.record_odometer_service import (
    ListVehicleOdometerHistoryService,
    RecordVehicleOdometerService,
)
from apps.vehicle.application.services.sync_vehicles_from_sap_service import (
    SyncVehiclesFromSAPService,
)
from apps.vehicle.infrastructure.repositories import DjangoVehicleRepository
from infrastructure.sap.adapters.bapi.pm_notification_bapi_adapter import (
    PMNotificationBAPIAdapter,
)
from infrastructure.sap.adapters.bapi.pm_order_bapi_adapter import PMOrderBAPIAdapter
from infrastructure.sap.adapters.bapi.purchase_requisition_bapi_adapter import (
    PurchaseRequisitionBAPIAdapter,
)
from infrastructure.sap.adapters.odata.object_part_catalog_odata_adapter import (
    ObjectPartCatalogODataAdapter,
)
from infrastructure.sap.adapters.odata.vehicle_driver_odata_adapter import (
    VehicleDriverODataAdapter,
)
from infrastructure.sap.client.mock.mock_client import MockSAPClient
from infrastructure.sap.client.odata_client import SAPODataClient
from infrastructure.sap.config import SAPConfig
from infrastructure.sap.transaction.sap_transaction_manager import SAPTransactionManager


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


def _sap_odata_client() -> MockSAPClient | SAPODataClient:
    """Build the SAP OData client used for read integrations."""
    config = SAPConfig.from_env()
    if config.use_mock:
        return MockSAPClient()
    return SAPODataClient(
        base_url=config.base_url,
        username=config.username,
        password=config.password,
        client_code=config.client,
        timeout_seconds=config.timeout_seconds,
        verify_ssl=config.verify_ssl,
    )


def _vehicle_driver_adapter() -> VehicleDriverODataAdapter:
    """Return the configured SAP vehicle-driver adapter."""
    config = SAPConfig.from_env()
    return VehicleDriverODataAdapter(
        _sap_odata_client(),
        service=config.vehicle_driver_service,
        entity_set=config.vehicle_driver_entity_set,
    )


def get_vehicle_repository() -> DjangoVehicleRepository:
    """Return the vehicle repository."""
    return DjangoVehicleRepository()


def get_driver_repository() -> DjangoDriverRepository:
    """Return the driver repository."""
    return DjangoDriverRepository()


def get_inspection_repository() -> DjangoInspectionRepository:
    """Return the inspection repository."""
    return DjangoInspectionRepository()


def get_inspection_template_repository() -> DjangoInspectionTemplateRepository:
    """Return the inspection template repository."""
    return DjangoInspectionTemplateRepository()


def get_fault_repository() -> DjangoFaultRepository:
    """Return the fault repository."""
    return DjangoFaultRepository()


def get_material_request_repository() -> DjangoMaterialRequestRepository:
    """Return the material request repository."""
    return DjangoMaterialRequestRepository()


def get_inventory_transaction_repository() -> DjangoInventoryTransactionRepository:
    """Return the inventory transaction repository."""
    return DjangoInventoryTransactionRepository()


def get_vehicle_handover_repository() -> DjangoVehicleHandoverRepository:
    """Return the vehicle handover repository."""
    return DjangoVehicleHandoverRepository()


def get_repair_order_repository() -> DjangoRepairOrderRepository:
    """Return the repair-order repository."""
    return DjangoRepairOrderRepository()


def get_external_invoice_repository() -> DjangoExternalRepairInvoiceRepository:
    """Return external invoice repository."""
    return DjangoExternalRepairInvoiceRepository()


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


def get_sap_transaction_manager() -> SAPTransactionManager:
    """Return the sole SAP write gateway (composition-root wiring)."""
    return SAPTransactionManager(repository=get_sap_transaction_repository())


def get_user_profile_reader() -> DjangoUserProfileReader:
    """Return the FMMS user profile reader."""
    return DjangoUserProfileReader()


def get_change_vehicle_status_service() -> ChangeVehicleStatusService:
    """Return ChangeVehicleStatusService."""
    return ChangeVehicleStatusService(
        get_vehicle_repository(),
        get_repair_order_repository(),
        get_fault_repository(),
    )


def get_sync_vehicles_from_sap_service() -> SyncVehiclesFromSAPService:
    """Return SyncVehiclesFromSAPService for bulk vehicle-driver import."""
    return SyncVehiclesFromSAPService(
        get_vehicle_repository(),
        _vehicle_driver_adapter(),
        get_driver_repository(),
    )


def get_record_vehicle_odometer_service() -> RecordVehicleOdometerService:
    """Return RecordVehicleOdometerService."""
    return RecordVehicleOdometerService(get_vehicle_repository())


def get_list_vehicle_odometer_history_service() -> ListVehicleOdometerHistoryService:
    """Return ListVehicleOdometerHistoryService."""
    return ListVehicleOdometerHistoryService(get_vehicle_repository())


def get_get_vehicle_service() -> GetVehicleService:
    """Return GetVehicleService."""
    return GetVehicleService(get_vehicle_repository())


def get_list_vehicles_service() -> ListVehiclesService:
    """Return ListVehiclesService."""
    return ListVehiclesService(get_vehicle_repository())


def get_get_driver_service() -> GetDriverService:
    """Return GetDriverService."""
    return GetDriverService(get_driver_repository())


def get_list_drivers_service() -> ListDriversService:
    """Return ListDriversService."""
    return ListDriversService(get_driver_repository())


def get_create_inspection_service() -> CreateInspectionService:
    """Return CreateInspectionService."""
    return CreateInspectionService(
        get_inspection_repository(),
        get_vehicle_repository(),
    )


def get_get_inspection_service() -> GetInspectionService:
    """Return GetInspectionService."""
    return GetInspectionService(
        get_inspection_repository(),
        get_fault_repository(),
        get_driver_repository(),
    )


def get_list_inspections_service() -> ListInspectionsService:
    """Return ListInspectionsService."""
    return ListInspectionsService(
        get_inspection_repository(),
        get_fault_repository(),
        get_driver_repository(),
    )


def get_add_inspection_item_service() -> AddInspectionItemService:
    """Return AddInspectionItemService."""
    return AddInspectionItemService(get_inspection_repository())


def get_submit_inspection_service() -> SubmitInspectionService:
    """Return SubmitInspectionService."""
    return SubmitInspectionService(
        get_inspection_repository(),
        get_fault_repository(),
        get_repair_order_repository(),
    )


def get_list_inspection_templates_service() -> ListInspectionTemplatesService:
    """Return ListInspectionTemplatesService."""
    return ListInspectionTemplatesService(get_inspection_template_repository())


def get_sync_inspection_templates_from_sap_service() -> (
    SyncInspectionTemplatesFromSAPService
):
    """Return SyncInspectionTemplatesFromSAPService."""
    config = SAPConfig.from_env()
    return SyncInspectionTemplatesFromSAPService(
        get_inspection_template_repository(),
        ObjectPartCatalogODataAdapter(
            _sap_odata_client(),
            service=config.object_part_catalog_service,
            entity_set=config.object_part_catalog_entity_set,
        ),
    )


def get_run_sap_sync_service() -> RunSAPSyncService:
    """Return the global SAP read-sync orchestration service."""
    return RunSAPSyncService(
        get_sync_vehicles_from_sap_service(),
        get_sync_inspection_templates_from_sap_service(),
    )


def get_report_fault_service() -> ReportFaultService:
    """Return ReportFaultService."""
    return ReportFaultService(
        get_fault_repository(),
        get_vehicle_repository(),
        get_repair_order_repository(),
        get_user_profile_reader(),
    )


def get_get_fault_service() -> GetFaultService:
    """Return GetFaultService."""
    return GetFaultService(get_fault_repository(), get_user_profile_reader())


def get_list_faults_service() -> ListFaultsService:
    """Return ListFaultsService."""
    return ListFaultsService(get_fault_repository(), get_user_profile_reader())


def get_assign_fault_service() -> AssignFaultService:
    """Return AssignFaultService."""
    return AssignFaultService(get_fault_repository())


def get_close_fault_service() -> CloseFaultService:
    """Return CloseFaultService."""
    return CloseFaultService(
        get_fault_repository(),
        get_repair_order_repository(),
        get_record_repair_order_event_service(),
    )


def get_repair_order_event_repository() -> DjangoRepairOrderEventRepository:
    """Return the repair-order event repository."""
    return DjangoRepairOrderEventRepository()


def get_record_repair_order_event_service() -> RecordRepairOrderEventService:
    """Return RecordRepairOrderEventService."""
    return RecordRepairOrderEventService(get_repair_order_event_repository())


def get_get_repair_order_timeline_service() -> GetRepairOrderTimelineService:
    """Return GetRepairOrderTimelineService."""
    return GetRepairOrderTimelineService(
        get_repair_order_repository(),
        get_repair_order_event_repository(),
    )


def get_create_repair_order_service() -> CreateRepairOrderService:
    """Return CreateRepairOrderService."""
    return CreateRepairOrderService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_fault_repository(),
        get_record_repair_order_event_service(),
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


def get_approve_repair_order_service() -> ApproveRepairOrderService:
    """Return ApproveRepairOrderService."""
    return ApproveRepairOrderService(
        get_repair_order_repository(),
        get_record_repair_order_event_service(),
    )


def get_assign_workshop_service() -> AssignWorkshopService:
    """Return AssignWorkshopService."""
    return AssignWorkshopService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_create_vehicle_handover_service(),
        get_record_repair_order_event_service(),
    )


def get_accept_repair_order_service() -> AcceptRepairOrderService:
    """Return AcceptRepairOrderService."""
    return AcceptRepairOrderService(
        get_repair_order_repository(),
        get_record_repair_order_event_service(),
    )


def get_reject_repair_order_service() -> RejectRepairOrderService:
    """Return RejectRepairOrderService."""
    return RejectRepairOrderService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_record_repair_order_event_service(),
    )


def get_approve_transport_handover_service() -> ApproveTransportHandoverService:
    """Return ApproveTransportHandoverService."""
    return ApproveTransportHandoverService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_fault_repository(),
        get_record_repair_order_event_service(),
    )


def get_reject_transport_handover_service() -> RejectTransportHandoverService:
    """Return RejectTransportHandoverService."""
    return RejectTransportHandoverService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_record_repair_order_event_service(),
    )


def get_create_material_request_service() -> CreateMaterialRequestService:
    """Return CreateMaterialRequestService."""
    return CreateMaterialRequestService(
        get_material_request_repository(),
        get_repair_order_repository(),
        get_record_repair_order_event_service(),
    )


def get_list_material_requests_service() -> ListMaterialRequestsService:
    """Return ListMaterialRequestsService."""
    return ListMaterialRequestsService(get_material_request_repository())


def get_approve_material_request_service() -> ApproveMaterialRequestService:
    """Return ApproveMaterialRequestService."""
    return ApproveMaterialRequestService(
        get_material_request_repository(),
        StubInventoryAvailabilityAdapter(),
        get_inventory_transaction_repository(),
        get_create_purchase_requisition_service(),
        get_add_pr_line_item_service(),
        get_record_repair_order_event_service(),
    )


def get_reject_material_request_service() -> RejectMaterialRequestService:
    """Return RejectMaterialRequestService."""
    return RejectMaterialRequestService(
        get_material_request_repository(),
        get_record_repair_order_event_service(),
    )


def get_create_vehicle_handover_service() -> CreateVehicleHandoverService:
    """Return CreateVehicleHandoverService."""
    return CreateVehicleHandoverService(get_vehicle_handover_repository())


def get_list_vehicle_handovers_service() -> ListVehicleHandoversService:
    """Return ListVehicleHandoversService."""
    return ListVehicleHandoversService(get_vehicle_handover_repository())


def get_confirm_vehicle_handover_service() -> ConfirmVehicleHandoverService:
    """Return ConfirmVehicleHandoverService."""
    return ConfirmVehicleHandoverService(
        get_vehicle_handover_repository(),
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_record_repair_order_event_service(),
        get_external_invoice_repository(),
    )


def get_start_repair_service() -> StartRepairService:
    """Return StartRepairService."""
    return StartRepairService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_record_repair_order_event_service(),
    )


def get_complete_repair_order_service() -> CompleteRepairOrderService:
    """Return CompleteRepairOrderService."""
    return CompleteRepairOrderService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_material_request_repository(),
        get_create_vehicle_handover_service(),
        get_record_repair_order_event_service(),
    )


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
        get_sap_transaction_manager(),
        PMOrderBAPIAdapter(_sap_client()),
    )


def get_upload_external_invoice_service() -> UploadExternalInvoiceService:
    """Return UploadExternalInvoiceService."""
    return UploadExternalInvoiceService(
        get_external_invoice_repository(),
        get_repair_order_repository(),
        get_record_repair_order_event_service(),
    )


def get_list_external_invoices_service() -> ListExternalInvoicesService:
    """Return ListExternalInvoicesService."""
    return ListExternalInvoicesService(get_external_invoice_repository())


def get_approve_external_invoice_service() -> ApproveExternalInvoiceService:
    """Return ApproveExternalInvoiceService."""
    return ApproveExternalInvoiceService(
        get_external_invoice_repository(),
        get_repair_order_repository(),
        get_fault_repository(),
        get_vehicle_repository(),
        get_record_repair_order_event_service(),
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
        get_sap_transaction_manager(),
        PMNotificationBAPIAdapter(_sap_client()),
    )


def get_trigger_overdue_pm_work_orders_service() -> TriggerOverduePMWorkOrdersService:
    """Return TriggerOverduePMWorkOrdersService."""
    return TriggerOverduePMWorkOrdersService(
        get_pm_plan_repository(),
        get_trigger_pm_work_order_service(),
    )


def get_retry_failed_sap_transactions_service() -> RetryFailedSAPTransactionsService:
    """Return RetryFailedSAPTransactionsService."""
    client = _sap_client()
    return RetryFailedSAPTransactionsService(
        get_sap_transaction_manager(),
        PurchaseRequisitionBAPIAdapter(client),
        PMOrderBAPIAdapter(client),
        PMNotificationBAPIAdapter(client),
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
        get_sap_transaction_manager(),
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
