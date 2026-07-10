/**
 * FMMS Demo Frontend — workflow state and API orchestration.
 * Driver / Distribution / Transport pages keep separate persisted state.
 */
(function (global) {
  "use strict";

  var SESSION_KEY = "fmms_user_session";
  var DRIVER_KEY = "fmms_driver_context";
  var DISTRIBUTION_KEY = "fmms_distribution_context";
  var TRANSPORT_KEY = "fmms_transport_context";
  var META_KEY = "fmms_workflow_meta";

  var PAGES = {
    driver: "driver",
    distribution: "distribution",
    transport: "transport",
  };

  var STAGES = [
    { id: "login", label: "ورود" },
    { id: "vehicle", label: "انتخاب خودرو" },
    { id: "inspection", label: "ثبت بازرسی" },
    { id: "fault", label: "ثبت خرابی" },
    { id: "distribution", label: "بررسی واحد توزیع" },
    { id: "transport_approve", label: "تایید ترابری" },
    { id: "workshop", label: "انتخاب تعمیرگاه" },
  ];

  var listeners = [];

  function notify() {
    listeners.forEach(function (fn) {
      try {
        fn(getState());
      } catch (err) {
        /* ignore */
      }
    });
  }

  function loadJson(key, fallback) {
    try {
      var raw = sessionStorage.getItem(key);
      if (!raw) return fallback;
      return JSON.parse(raw);
    } catch (err) {
      return fallback;
    }
  }

  function saveJson(key, value) {
    sessionStorage.setItem(key, JSON.stringify(value));
  }

  function defaultDriverContext() {
    return {
      vehicles: [],
      templates: [],
      selectedVehicleId: "",
      checklist: [],
      inspectionId: "",
      inspection: null,
      inspectionResult: null,
      message: "",
      error: "",
    };
  }

  function defaultDistributionContext() {
    return {
      openFaults: [],
      selectedFaultId: "",
      selectedFault: null,
      vehicles: [],
      message: "",
      error: "",
    };
  }

  function defaultTransportContext() {
    return {
      vehicleId: "",
      repairOrder: null,
      vehicles: [],
      workshopType: "",
      message: "",
      error: "",
    };
  }

  function defaultMeta() {
    return {
      page: PAGES.driver,
      stage: "vehicle",
    };
  }

  function getDriverContext() {
    return loadJson(DRIVER_KEY, defaultDriverContext());
  }

  function setDriverContext(patch) {
    var ctx = Object.assign(getDriverContext(), patch || {});
    saveJson(DRIVER_KEY, ctx);
    return ctx;
  }

  function getDistributionContext() {
    return loadJson(DISTRIBUTION_KEY, defaultDistributionContext());
  }

  function setDistributionContext(patch) {
    var ctx = Object.assign(getDistributionContext(), patch || {});
    saveJson(DISTRIBUTION_KEY, ctx);
    return ctx;
  }

  function getTransportContext() {
    return loadJson(TRANSPORT_KEY, defaultTransportContext());
  }

  function setTransportContext(patch) {
    var ctx = Object.assign(getTransportContext(), patch || {});
    saveJson(TRANSPORT_KEY, ctx);
    return ctx;
  }

  function getMeta() {
    return loadJson(META_KEY, defaultMeta());
  }

  function setMeta(patch) {
    var meta = Object.assign(getMeta(), patch || {});
    saveJson(META_KEY, meta);
    return meta;
  }

  function clearWorkflowStorage() {
    sessionStorage.removeItem(DRIVER_KEY);
    sessionStorage.removeItem(DISTRIBUTION_KEY);
    sessionStorage.removeItem(TRANSPORT_KEY);
    sessionStorage.removeItem(META_KEY);
  }

  function getSession() {
    return loadJson(SESSION_KEY, null);
  }

  function setSession(session) {
    if (session) saveJson(SESSION_KEY, session);
    else sessionStorage.removeItem(SESSION_KEY);
  }

  function getState() {
    return {
      session: getSession(),
      authenticated: Boolean(global.FMMSApi.getToken()),
      stages: STAGES,
      pages: PAGES,
      page: getMeta().page,
      stage: getMeta().stage,
      driver: getDriverContext(),
      distribution: getDistributionContext(),
      transport: getTransportContext(),
    };
  }

  function onChange(fn) {
    listeners.push(fn);
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function buildChecklistFromTemplates(templates) {
    return templates.map(function (t) {
      return {
        templateId: t.id,
        category: t.category,
        description: t.description,
        result: "PASS",
        notes: "",
      };
    });
  }

  function deriveStage() {
    var driver = getDriverContext();
    var distribution = getDistributionContext();
    var transport = getTransportContext();
    var meta = getMeta();

    if (transport.repairOrder && transport.repairOrder.workshop_type) {
      return "workshop";
    }
    if (transport.repairOrder && transport.repairOrder.status === "APPROVED") {
      return "workshop";
    }
    if (meta.page === PAGES.transport || transport.vehicleId) {
      return "transport_approve";
    }
    if (meta.page === PAGES.distribution || distribution.openFaults.length) {
      return "distribution";
    }
    if (driver.inspectionResult === "FAIL") {
      return "fault";
    }
    if (driver.inspectionResult === "PASS") {
      return "inspection";
    }
    if (driver.inspectionId) {
      return "inspection";
    }
    if (driver.selectedVehicleId) {
      return "inspection";
    }
    return "vehicle";
  }

  function syncStage() {
    setMeta({ stage: deriveStage() });
  }

  function setDriverError(message) {
    setDriverContext({ error: message || "" });
    notify();
  }

  function clearDriverError() {
    setDriverContext({ error: "" });
    notify();
  }

  function setDistributionError(message) {
    setDistributionContext({ error: message || "" });
    notify();
  }

  function clearDistributionError() {
    setDistributionContext({ error: "" });
    notify();
  }

  function setTransportError(message) {
    setTransportContext({ error: message || "" });
    notify();
  }

  function clearTransportError() {
    setTransportContext({ error: "" });
    notify();
  }

  async function login(email, password) {
    await global.FMMSApi.login(email, password);
    setSession({ email: email, loggedInAt: nowIso() });
    clearWorkflowStorage();
    setMeta({ page: PAGES.driver, stage: "vehicle" });
    notify();
    return getState();
  }

  function logout() {
    global.FMMSApi.clearTokens();
    setSession(null);
    clearWorkflowStorage();
    notify();
  }

  function goToPage(page) {
    if (!PAGES[page]) return;
    setMeta({ page: page });
    syncStage();
    notify();
  }

  async function loadDriverData() {
    var vehiclesPage = await global.FMMSApi.listVehicles({ status: "ACTIVE" });
    var templatesPage = await global.FMMSApi.listInspectionTemplates();
    var vehicles = global.FMMSApi.pageResults(vehiclesPage);
    var templates = global.FMMSApi.pageResults(templatesPage);
    var ctx = getDriverContext();
    var selectedVehicleId = ctx.selectedVehicleId || (vehicles[0] && vehicles[0].id) || "";
    var checklist =
      ctx.checklist && ctx.checklist.length
        ? ctx.checklist
        : buildChecklistFromTemplates(templates);
    setDriverContext({
      vehicles: vehicles,
      templates: templates,
      selectedVehicleId: selectedVehicleId,
      checklist: checklist,
      error: "",
    });
    syncStage();
    notify();
    return getDriverContext();
  }

  function selectVehicle(vehicleId) {
    setDriverContext({
      selectedVehicleId: vehicleId,
      inspectionId: "",
      inspection: null,
      inspectionResult: null,
      message: "خودرو انتخاب شد",
      error: "",
    });
    syncStage();
    notify();
  }

  function setChecklistItem(index, patch) {
    var ctx = getDriverContext();
    var checklist = ctx.checklist.slice();
    if (!checklist[index]) return;
    checklist[index] = Object.assign({}, checklist[index], patch || {});
    setDriverContext({ checklist: checklist });
    notify();
  }

  async function createInspection(form) {
    var ctx = getDriverContext();
    var vehicleId = ctx.selectedVehicleId;
    if (!vehicleId) {
      throw new Error("ابتدا خودرو را انتخاب کنید");
    }
    if (!ctx.checklist.length) {
      throw new Error("چک‌لیست بازرسی خالی است — ابتدا قالب‌ها را از سرویس بارگذاری کنید");
    }

    var items = ctx.checklist.map(function (item) {
      return {
        category: item.category,
        description: item.description,
        result: item.result,
        notes: item.result === "FAIL" ? item.notes || "" : null,
      };
    });

    var created = await global.FMMSApi.createInspection({
      vehicle_id: vehicleId,
      inspection_type: (form && form.inspection_type) || "PRE_TRIP",
      odometer_value: Number((form && form.odometer_value) || 0),
      odometer_unit: "KM",
      inspected_at: nowIso(),
      items: items,
    });

    setDriverContext({
      inspectionId: created.id,
      inspection: created,
      inspectionResult: null,
      message: "بازرسی ایجاد شد. برای ثبت نهایی، ارسال بازرسی را بزنید.",
      error: "",
    });
    syncStage();
    notify();
    return created;
  }

  async function submitDriverInspection() {
    var ctx = getDriverContext();
    if (!ctx.inspectionId) {
      throw new Error("ابتدا بازرسی را ایجاد کنید");
    }

    var submitted = await global.FMMSApi.submitInspection(ctx.inspectionId);
    var hasFailures = Boolean(submitted.has_failures);

    if (!hasFailures) {
      setDriverContext({
        inspection: submitted,
        inspectionResult: "PASS",
        message: "خودرو سالم است و امکان خروج دارد.",
        error: "",
      });
      setMeta({ stage: "inspection" });
      notify();
      return submitted;
    }

    setDriverContext({
      inspection: submitted,
      inspectionResult: "FAIL",
      message: "خرابی ثبت شد و درخواست تعمیر ایجاد شد.",
      error: "",
    });
    setMeta({ stage: "fault" });
    notify();
    return submitted;
  }

  async function loadDistributionFaults() {
    var faults = global.FMMSApi.pageResults(await global.FMMSApi.listOpenFaults());
    var openFaults = faults.filter(function (fault) {
      return fault.status === "OPEN";
    });
    var vehiclesPage = await global.FMMSApi.listVehicles();
    var vehicles = global.FMMSApi.pageResults(vehiclesPage);
    var ctx = getDistributionContext();
    var selectedFaultId = ctx.selectedFaultId || (openFaults[0] && openFaults[0].id) || "";
    var selectedFault =
      openFaults.find(function (f) {
        return f.id === selectedFaultId;
      }) ||
      openFaults[0] ||
      null;

    setDistributionContext({
      openFaults: openFaults,
      selectedFaultId: selectedFaultId,
      selectedFault: selectedFault,
      vehicles: vehicles,
      message: openFaults.length
        ? "فهرست خرابی‌های باز بارگذاری شد."
        : "خرابی بازی یافت نشد.",
      error: "",
    });
    setMeta({ page: PAGES.distribution, stage: "distribution" });
    notify();
    return openFaults;
  }

  function selectDistributionFault(faultId) {
    var ctx = getDistributionContext();
    var fault =
      ctx.openFaults.find(function (f) {
        return f.id === faultId;
      }) || null;
    setDistributionContext({
      selectedFaultId: faultId,
      selectedFault: fault,
      error: "",
    });
    notify();
  }

  async function closeFaultAsUsable() {
    var ctx = getDistributionContext();
    var faultId = ctx.selectedFaultId;
    if (!faultId) throw new Error("ابتدا یک خرابی را انتخاب کنید");

    await global.FMMSApi.closeFault(faultId);
    setDistributionContext({
      openFaults: [],
      selectedFault: null,
      selectedFaultId: "",
      message: "خرابی بسته شد و خودرو قابل استفاده است.",
      error: "",
    });
    setMeta({ stage: "distribution" });
    notify();
  }

  async function deactivateVehicleForRepair() {
    var ctx = getDistributionContext();
    var fault = ctx.selectedFault;
    if (!fault) throw new Error("ابتدا یک خرابی را انتخاب کنید");

    var vehicleId = fault.vehicle_id;
    await global.FMMSApi.deactivateVehicle(vehicleId);

    setDistributionContext({
      message: "خودرو از حالت فعال خارج شد و وارد فرآیند تعمیر شد.",
      error: "",
    });
    setTransportContext({
      vehicleId: vehicleId,
      repairOrder: null,
      vehicles: ctx.vehicles,
      message: "",
      error: "",
    });
    setMeta({ page: PAGES.transport, stage: "transport_approve" });
    notify();
    return vehicleId;
  }

  async function loadTransportRepairOrder() {
    var ctx = getTransportContext();
    var vehicleId = ctx.vehicleId;
    if (!vehicleId) {
      throw new Error("شناسه خودرو برای بارگذاری دستور تعمیر مشخص نیست");
    }

    var orders = global.FMMSApi.pageResults(
      await global.FMMSApi.listRepairOrders(vehicleId)
    );
    var order =
      orders.find(function (o) {
        return ctx.repairOrder && o.id === ctx.repairOrder.id;
      }) ||
      orders.find(function (o) {
        return o.status === "CREATED";
      }) ||
      orders[0];

    if (!order) {
      throw new Error("دستور تعمیر برای این خودرو یافت نشد");
    }

    var vehicles = ctx.vehicles.length
      ? ctx.vehicles
      : global.FMMSApi.pageResults(await global.FMMSApi.listVehicles());

    setTransportContext({
      repairOrder: order,
      vehicles: vehicles,
      message: "دستور تعمیر بارگذاری شد.",
      error: "",
    });
    setMeta({ page: PAGES.transport, stage: "transport_approve" });
    notify();
    return order;
  }

  async function approveRepair() {
    var ctx = getTransportContext();
    var order = ctx.repairOrder || (await loadTransportRepairOrder());
    var result = await global.FMMSApi.approveRepairOrder(order.id);

    setTransportContext({
      repairOrder: Object.assign({}, order, {
        id: result.id,
        status: result.status,
      }),
      message: result.message || "دستور تعمیر توسط واحد ترابری تأیید شد.",
      error: "",
    });
    setMeta({ stage: "workshop" });
    notify();
    return result;
  }

  async function assignWorkshop(workshopType) {
    var ctx = getTransportContext();
    var order = ctx.repairOrder || (await loadTransportRepairOrder());
    var result = await global.FMMSApi.assignWorkshop(order.id, workshopType);

    setTransportContext({
      repairOrder: Object.assign({}, order, {
        id: result.id,
        status: result.status,
        workshop_type: result.workshop_type,
      }),
      workshopType: workshopType,
      message: result.message || "نوع تعمیرگاه با موفقیت انتخاب شد.",
      error: "",
    });
    setMeta({ stage: "workshop" });
    notify();
    return result;
  }

  global.FMMSWorkflow = {
    PAGES: PAGES,
    STAGES: STAGES,
    getState: getState,
    onChange: onChange,
    login: login,
    logout: logout,
    goToPage: goToPage,
    loadDriverData: loadDriverData,
    selectVehicle: selectVehicle,
    setChecklistItem: setChecklistItem,
    createInspection: createInspection,
    submitDriverInspection: submitDriverInspection,
    loadDistributionFaults: loadDistributionFaults,
    selectDistributionFault: selectDistributionFault,
    closeFaultAsUsable: closeFaultAsUsable,
    deactivateVehicleForRepair: deactivateVehicleForRepair,
    loadTransportRepairOrder: loadTransportRepairOrder,
    approveRepair: approveRepair,
    assignWorkshop: assignWorkshop,
    setDriverError: setDriverError,
    clearDriverError: clearDriverError,
    setDistributionError: setDistributionError,
    clearDistributionError: clearDistributionError,
    setTransportError: setTransportError,
    clearTransportError: clearTransportError,
  };
})(window);
