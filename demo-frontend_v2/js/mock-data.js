/**
 * Mock data for the FMMS demo.
 * Field names intentionally mirror the real response schemas in
 * FMMS_API.yaml (VehicleResponse, FaultResponse, RepairOrderResponse, ...)
 * so that flipping DEMO_MODE to false requires no changes to page code.
 */
(function () {
  const now = () => new Date().toISOString();
  const uid = (() => {
    let n = 1000;
    return (prefix) => `${prefix}-${(n++).toString().padStart(4, "0")}`;
  })();

  const DB = {
    vehicles: [
      {
        id: "veh-1025",
        plate_number: "۱۵ ایران ۴۴۲ ص ۶۸",
        vin: "IR1FMMS0001025A1",
        make: "بنز",
        model: "اطلس",
        year: 1401,
        category: "MEDIUM",
        status: "ACTIVE",
        chassis_number: "CH-1025",
        sap_equipment_number: "SAP-EQ-1025",
        created_at: now(),
        updated_at: now(),
      },
      {
        id: "veh-1031",
        plate_number: "۴۲ ایران ۱۱۸ ع ۲۲",
        vin: "IR1FMMS0001031B2",
        make: "ایسوزو",
        model: "NPR",
        year: 1400,
        category: "LIGHT",
        status: "ACTIVE",
        chassis_number: "CH-1031",
        sap_equipment_number: "SAP-EQ-1031",
        created_at: now(),
        updated_at: now(),
      },
      {
        id: "veh-1042",
        plate_number: "۰۹ ایران ۷۷۰ ب ۱۱",
        vin: "IR1FMMS0001042C3",
        make: "هیوندای",
        model: "HD65",
        year: 1399,
        category: "LIGHT",
        status: "UNDER_REPAIR",
        chassis_number: "CH-1042",
        sap_equipment_number: "SAP-EQ-1042",
        created_at: now(),
        updated_at: now(),
      },
      {
        id: "veh-1050",
        plate_number: "۶۶ ایران ۳۳۰ ج ۹۹",
        vin: "IR1FMMS0001050D4",
        make: "بنز",
        model: "اطلس",
        year: 1402,
        category: "MEDIUM",
        status: "ACTIVE",
        chassis_number: "CH-1050",
        sap_equipment_number: "SAP-EQ-1050",
        created_at: now(),
        updated_at: now(),
      },
      {
        id: "veh-1063",
        plate_number: "۲۳ ایران ۵۵۴ د ۷۷",
        vin: "IR1FMMS0001063E5",
        make: "ولوو",
        model: "FMX",
        year: 1401,
        category: "HEAVY",
        status: "SUSPENDED",
        chassis_number: "CH-1063",
        sap_equipment_number: "SAP-EQ-1063",
        created_at: now(),
        updated_at: now(),
      },
    ],

    inspectionTemplates: [
      { id: "tpl-1", sap_code: "IC-001", code_group: "SAFETY", category: "ایمنی", description: "کمربند ایمنی", catalog_type: "CHECKLIST", is_active: true, created_at: now(), updated_at: now() },
      { id: "tpl-2", sap_code: "IC-002", code_group: "LIGHTING", category: "روشنایی", description: "چراغ جلو", catalog_type: "CHECKLIST", is_active: true, created_at: now(), updated_at: now() },
      { id: "tpl-3", sap_code: "IC-003", code_group: "COLD_CHAIN", category: "بار سرد", description: "یخچال", catalog_type: "CHECKLIST", is_active: true, created_at: now(), updated_at: now() },
      { id: "tpl-4", sap_code: "IC-004", code_group: "BRAKES", category: "ترمز", description: "ترمز", catalog_type: "CHECKLIST", is_active: true, created_at: now(), updated_at: now() },
      { id: "tpl-5", sap_code: "IC-005", code_group: "TIRES", category: "لاستیک", description: "فشار باد لاستیک", catalog_type: "CHECKLIST", is_active: true, created_at: now(), updated_at: now() },
    ],

    inspections: [],
    faults: [],

    repairOrders: [
      {
        id: "ro-9001",
        vehicle_id: "veh-1042",
        fault_id: "fault-seed-1",
        status: "WORKSHOP_ASSIGNED",
        created_by_id: "user-manager",
        created_at: now(),
        updated_at: now(),
        activities: [],
        parts: [],
        technician_id: null,
        assigned_at: null,
        sap_order_number: "PM-800213",
        workshop_type: "INTERNAL",
        workshop_id: "central-workshop",
        completed_at: null,
      },
    ],

    materialRequests: [],
    vehicleHandovers: [],
    externalInvoices: [],
    purchaseRequisitions: [],

    repairOrderEvents: [
      {
        repair_order_id: "ro-9001",
        event: "FAULT_CREATED",
        description: "خرابی ثبت شد.",
        created_at: now(),
        created_by_id: null,
      },
      {
        repair_order_id: "ro-9001",
        event: "TRANSPORT_APPROVED",
        description: "تایید ترابری انجام شد.",
        created_at: now(),
        created_by_id: null,
      },
      {
        repair_order_id: "ro-9001",
        event: "WORKSHOP_ASSIGNED",
        description: "تعمیرگاه داخلی تخصیص یافت.",
        created_at: now(),
        created_by_id: null,
      },
    ],

    sapTransactions: [
      { id: "sap-1", object_type: "VEHICLE", object_id: "veh-1042", idempotency_key: "idem-1", status: "SUCCESS", retry_count: 0, max_retries: 3, request_payload: {}, response_payload: {}, sap_document_number: "EQ-100442", error_message: null, created_at: now(), updated_at: now(), completed_at: now() },
      { id: "sap-2", object_type: "REPAIR_ORDER", object_id: "ro-9001", idempotency_key: "idem-2", status: "SUCCESS", retry_count: 0, max_retries: 3, request_payload: {}, response_payload: {}, sap_document_number: "PM-800213", error_message: null, created_at: now(), updated_at: now(), completed_at: now() },
      { id: "sap-3", object_type: "PURCHASE_REQUISITION", object_id: "pr-1", idempotency_key: "idem-3", status: "RETRYING", retry_count: 2, max_retries: 3, request_payload: {}, response_payload: null, sap_document_number: null, error_message: "سرویس SAP در دسترس نیست", created_at: now(), updated_at: now(), completed_at: null },
      { id: "sap-4", object_type: "FAULT", object_id: "fault-seed-1", idempotency_key: "idem-4", status: "FAILED", retry_count: 3, max_retries: 3, request_payload: {}, response_payload: null, sap_document_number: null, error_message: "کد تجهیز نامعتبر", created_at: now(), updated_at: now(), completed_at: null },
    ],
  };

  // Seed one already-open fault so the Distribution & Transport pages aren't
  // empty on first load.
  DB.faults.push({
    id: "fault-seed-1",
    vehicle_id: "veh-1042",
    code: "INSP-FAIL",
    description: "Front light [LIGHTS]",
    severity: "MEDIUM",
    status: "OPEN",
    reported_by_id: "driver-demo",
    reported_at: now(),
    created_at: now(),
    updated_at: now(),
    inspection_id: null,
    assigned_to_id: null,
    sap_notification_number: null,
    created_by: { id: "user-manager", name: "مدیر سیستم", role: "ADMIN" },
    items: [{ id: "item-1", component: "LIGHTS", description: "Front light", severity: "MEDIUM", inspection_item_id: null }],
  });

  DB.faults.push({
    id: "fault-open-1025",
    vehicle_id: "veh-1025",
    code: "INSP-FAIL",
    description: "Tyre and wheel assembly [CHASSIS]",
    severity: "MEDIUM",
    status: "OPEN",
    reported_by_id: "driver-demo",
    reported_at: now(),
    created_at: now(),
    updated_at: now(),
    inspection_id: null,
    assigned_to_id: null,
    sap_notification_number: null,
    created_by: { id: "user-manager", name: "مدیر سیستم", role: "ADMIN" },
    items: [{ id: "item-2", component: "CHASSIS", description: "Tyre and wheel assembly", severity: "MEDIUM", inspection_item_id: null }],
  });

  DB.faults.push({
    id: "fault-closed-1025",
    vehicle_id: "veh-1025",
    code: "F-1025-01",
    description: "تعویض لنت ترمز (تعمیر قبلی)",
    severity: "HIGH",
    status: "CLOSED",
    reported_by_id: "driver-demo",
    reported_at: new Date(Date.now() - 86400000 * 14).toISOString(),
    created_at: new Date(Date.now() - 86400000 * 14).toISOString(),
    updated_at: new Date(Date.now() - 86400000 * 7).toISOString(),
    inspection_id: null,
    assigned_to_id: "tech-1",
    sap_notification_number: "NOTIF-400112",
    items: [{ id: "item-3", component: "ترمز", description: "لنت ترمز فرسوده", severity: "CRITICAL", inspection_item_id: null }],
  });

  DB.repairOrders.push({
    id: "ro-completed-1025",
    vehicle_id: "veh-1025",
    fault_id: "fault-closed-1025",
    status: "WAITING_TRANSPORT_FINAL_APPROVAL",
    created_by_id: "user-manager",
    created_at: new Date(Date.now() - 86400000 * 14).toISOString(),
    updated_at: new Date(Date.now() - 86400000 * 7).toISOString(),
    activities: [{ id: "act-1", description: "تعویض لنت ترمز", labor_hours: "2.5", performed_by_id: "tech-1", performed_at: new Date(Date.now() - 86400000 * 8).toISOString(), notes: null }],
    parts: [{ id: "part-1", material_number: "4500998877", quantity: 2, unit_of_measure: "EA", goods_issue_id: null, posted_at: null }],
    technician_id: "tech-1",
    assigned_at: new Date(Date.now() - 86400000 * 10).toISOString(),
    sap_order_number: "PM-700102",
    workshop_type: "INTERNAL",
    workshop_id: "central-workshop",
    completed_at: new Date(Date.now() - 86400000 * 7).toISOString(),
  });

  DB.materialRequests = [];
  DB.vehicleHandovers = [];
  DB.externalInvoices = [];
  DB.purchaseRequisitions = [];

  const finalApprovalVehicle = DB.vehicles.find((v) => v.id === "veh-1025");
  if (finalApprovalVehicle) {
    finalApprovalVehicle.status = "WAITING_TRANSPORT_FINAL_APPROVAL";
  }

  DB.materialRequests.push({
    id: "mr-demo-1",
    repair_order_id: "ro-9001",
    status: "REQUESTED",
    created_by_id: "tech-demo",
    created_at: now(),
    updated_at: now(),
    items: [
      {
        id: "mri-1",
        material_number: "000000012345",
        quantity: "2",
        unit_of_measure: "EA",
      },
    ],
  });

  const waitingVehicle = DB.vehicles.find((v) => v.id === "veh-1050");
  if (waitingVehicle) {
    waitingVehicle.status = "WAITING_DRIVER_CONFIRMATION";
  }
  DB.repairOrders.push({
    id: "ro-handover-1050",
    vehicle_id: "veh-1050",
    fault_id: "fault-closed-1025",
    status: "WAITING_DRIVER_CONFIRMATION",
    created_by_id: "user-manager",
    created_at: now(),
    updated_at: now(),
    activities: [],
    parts: [],
    technician_id: "tech-1",
    assigned_at: now(),
    sap_order_number: "PM-900050",
    workshop_type: "INTERNAL",
    workshop_id: "central-workshop",
    completed_at: now(),
  });
  DB.vehicleHandovers.push({
    id: "ho-completed-1025",
    repair_order_id: "ro-completed-1025",
    vehicle_id: "veh-1025",
    status: "ACCEPTED",
    created_at: new Date(Date.now() - 86400000 * 7).toISOString(),
    updated_at: new Date(Date.now() - 86400000 * 7).toISOString(),
    comment: "OK",
    driver_id: "driver-demo",
    confirmed_at: new Date(Date.now() - 86400000 * 7).toISOString(),
  });
  DB.vehicleHandovers.push({
    id: "ho-1050",
    repair_order_id: "ro-handover-1050",
    vehicle_id: "veh-1050",
    status: "WAITING_DRIVER_CONFIRMATION",
    created_at: now(),
    updated_at: now(),
    comment: null,
    driver_id: null,
    confirmed_at: null,
  });

  const externalVehicle = DB.vehicles.find((v) => v.id === "veh-1031");
  if (externalVehicle) {
    externalVehicle.status = "WAITING_TRANSPORT_FINAL_APPROVAL";
  }
  DB.faults.push({
    id: "fault-external-1031",
    vehicle_id: "veh-1031",
    code: "F-1031-EXT",
    description: "تعمیر بدنه در تعمیرگاه خارجی",
    severity: "MEDIUM",
    status: "IN_REPAIR",
    reported_by_id: "driver-demo",
    reported_at: now(),
    created_at: now(),
    updated_at: now(),
    inspection_id: null,
    assigned_to_id: "vendor-1",
    sap_notification_number: "NOTIF-400313",
    items: [{ id: "item-ext-1", component: "بدنه", description: "آسیب بدنه", severity: "MEDIUM", inspection_item_id: null }],
  });
  DB.repairOrders.push({
    id: "ro-external-1031",
    vehicle_id: "veh-1031",
    fault_id: "fault-external-1031",
    status: "WAITING_TRANSPORT_FINAL_APPROVAL",
    created_by_id: "user-manager",
    created_at: now(),
    updated_at: now(),
    activities: [{ id: "act-ext-1", description: "تعمیر بدنه توسط پیمانکار", labor_hours: "4", performed_by_id: "vendor-1", performed_at: now(), notes: null }],
    parts: [],
    technician_id: "vendor-1",
    assigned_at: now(),
    sap_order_number: "PM-900103",
    workshop_type: "EXTERNAL",
    workshop_id: "vendor-body-shop",
    completed_at: now(),
  });
  DB.vehicleHandovers.push({
    id: "ho-external-1031",
    repair_order_id: "ro-external-1031",
    vehicle_id: "veh-1031",
    status: "ACCEPTED",
    created_at: now(),
    updated_at: now(),
    comment: "تحویل شد",
    driver_id: "driver-demo",
    confirmed_at: now(),
  });
  DB.externalInvoices.push({
    id: "inv-external-1031",
    repair_order_id: "ro-external-1031",
    amount: "8500000",
    currency: "IRR",
    status: "UPLOADED",
    created_by_id: "driver-demo",
    created_at: now(),
    updated_at: now(),
    vendor_id: "vendor-body-shop",
    document: "INV-1031-001",
  });

  window.FMMS_MOCK_DB = DB;
  window.FMMS_MOCK_UID = uid;
})();
