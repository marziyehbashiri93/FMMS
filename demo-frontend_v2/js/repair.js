/**
 * Page: تایید ترابری (Transport supervisor)
 * Page: تعمیرات — تعمیرگاه (Workshop)
 */
window.FMMS = window.FMMS || {};
FMMS.pages = FMMS.pages || {};

(function (FMMS) {
  let vehiclesById = {};
  let modalInstance = null;
  let timelineModalInstance = null;
  let transportFilter = "pending";
  let transportVehicleId = "";
  let transportToolbarWired = false;

  const TRANSPORT_PENDING = new Set(["CREATED", "APPROVED"]);

  const EVENT_LABELS = {
    FAULT_CREATED: "خرابی ثبت شد",
    DISTRIBUTION_APPROVED: "تایید توزیع",
    TRANSPORT_APPROVED: "تایید ترابری",
    WORKSHOP_ASSIGNED: "تخصیص تعمیرگاه",
    TECHNICIAN_ACCEPTED: "تایید تعمیرکار",
    TECHNICIAN_REJECTED: "رد تعمیرکار",
    REPAIR_REJECTED: "رد تعمیر",
    REPAIR_STARTED: "شروع تعمیر",
    MATERIAL_REQUESTED: "درخواست قطعه",
    MATERIAL_APPROVED: "تایید درخواست قطعه",
    STOCK_ISSUED: "صدور از انبار",
    PURCHASE_REQUIRED: "نیاز به خرید",
    PART_RECEIVED: "دریافت قطعه",
    REPAIR_COMPLETED: "پایان تعمیر",
    WAITING_DRIVER_CONFIRMATION: "منتظر تایید راننده",
    DRIVER_ACCEPTED: "تایید راننده",
    DRIVER_REJECTED: "رد راننده",
    INVOICE_UPLOADED: "ثبت فاکتور",
    INVOICE_APPROVED: "تایید فاکتور",
  };

  const WORKFLOW_STEPS = [
    { key: "FAULT_CREATED", label: "خرابی ثبت شد" },
    { key: "TRANSPORT_APPROVED", label: "تایید ترابری" },
    { key: "WORKSHOP_ASSIGNED", label: "تخصیص تعمیرگاه" },
    { key: "TECHNICIAN_ACCEPTED", label: "تایید تعمیرکار" },
    { key: "REPAIR_STARTED", label: "شروع تعمیر" },
    { key: "MATERIAL_REQUESTED", label: "درخواست قطعه", optional: true },
    { key: "REPAIR_COMPLETED", label: "پایان تعمیر" },
    { key: "DRIVER_ACCEPTED", label: "تایید راننده", alt: ["DRIVER_REJECTED"] },
    { key: "VEHICLE_ACTIVE", label: "فعال‌سازی خودرو", derived: true },
  ];

  /** Last completed checklist step index derived from API repair-order status. */
  const STATUS_STEP_DONE_THROUGH = {
    CREATED: 0,
    APPROVED: 1,
    WORKSHOP_ASSIGNED: 2,
    WAITING_WORKSHOP_CONFIRMATION: 3,
    ASSIGNED: 3,
    IN_PROGRESS: 4,
    WAITING_PARTS: 4,
    WAITING_DRIVER_CONFIRMATION: 6,
    COMPLETED: 6,
    ACCEPTED_BY_DRIVER: 8,
    REJECTED_BY_DRIVER: 7,
    CANCELLED: -1,
  };

  function renderWorkflowChecklist(events, order) {
    const eventSet = new Set((events || []).map((e) => e.event));
    const status = order?.status;
    const doneThrough = STATUS_STEP_DONE_THROUGH[status] ?? -1;
    let currentFound = false;
    return `<div class="workflow-checklist">${WORKFLOW_STEPS.map((step, stepIndex) => {
      const done =
        stepIndex <= doneThrough ||
        eventSet.has(step.key) ||
        (step.alt || []).some((k) => eventSet.has(k)) ||
        (step.key === "VEHICLE_ACTIVE" && status === "ACCEPTED_BY_DRIVER");
      let icon = "○";
      let cls = "pending";
      if (done) {
        icon = "✓";
        cls = "done";
      } else if (!currentFound) {
        const partsPhase = status === "IN_PROGRESS" || status === "WAITING_PARTS";
        if (step.optional && !(partsPhase && step.key === "MATERIAL_REQUESTED")) {
          icon = "○";
          cls = "pending";
        } else {
          icon = "●";
          cls = "current";
          currentFound = true;
        }
      }
      return `<div class="workflow-checklist-item ${cls}"><span class="wf-check-icon">${icon}</span>${FMMS.ui.escapeHtml(step.label)}</div>`;
    }).join("")}</div>`;
  }

  async function ensureVehicles() {
    const res = await FMMS.api.listAllVehicles();
    vehiclesById = Object.fromEntries(res.results.map((v) => [v.id, v]));
  }

  function getModal() {
    if (!modalInstance) modalInstance = new bootstrap.Modal(document.getElementById("repair-action-modal"));
    return modalInstance;
  }

  function openActionModal(title, bodyHtml, onConfirm, confirmLabel) {
    document.getElementById("repair-action-modal-title").textContent = title;
    document.getElementById("repair-action-modal-body").innerHTML = bodyHtml;
    const confirmBtn = document.getElementById("repair-action-modal-confirm");
    const clone = confirmBtn.cloneNode(true);
    confirmBtn.replaceWith(clone);
    clone.textContent = confirmLabel || "ثبت";
    clone.addEventListener("click", async () => {
      clone.disabled = true;
      const prev = clone.textContent;
      clone.textContent = "در حال ثبت…";
      try {
        await onConfirm();
        getModal().hide();
      } catch (err) {
        FMMS.ui.toast(err.message, "error");
      } finally {
        clone.disabled = false;
        clone.textContent = prev;
      }
    });
    getModal().show();
  }

  function getTimelineModal() {
    if (!timelineModalInstance) {
      timelineModalInstance = new bootstrap.Modal(document.getElementById("timeline-modal"));
    }
    return timelineModalInstance;
  }

  async function showTimeline(order) {
    document.getElementById("timeline-modal-title").textContent = "تاریخچه و مراحل تعمیر";
    document.getElementById("timeline-modal-body").innerHTML = `<div class="text-muted">در حال بارگذاری…</div>`;
    getTimelineModal().show();
    try {
      const [events, freshOrder] = await Promise.all([
        FMMS.api.getRepairTimeline(order.id),
        FMMS.api.getRepairOrder(order.id),
      ]);
      const labeled = events.map((e) => ({
        ...e,
        event: EVENT_LABELS[e.event] || e.event,
      }));
      document.getElementById("timeline-modal-body").innerHTML =
        `<div class="mb-3"><div class="modal-section-title">مراحل جریان</div>${renderWorkflowChecklist(events, freshOrder)}</div>` +
        `<div class="modal-section-title">رویدادهای ثبت‌شده</div>${FMMS.ui.renderTimeline(labeled)}`;
    } catch (err) {
      document.getElementById("timeline-modal-body").innerHTML = `<div class="text-danger">${FMMS.ui.escapeHtml(err.message)}</div>`;
    }
  }

  function workshopTypeLabel(type) {
    if (type === "INTERNAL") return "تعمیرگاه داخلی";
    if (type === "EXTERNAL") return "تعمیرگاه خارجی";
    return "—";
  }

  function defaultTechnicianId() {
    return FMMS.session.getTechnicianId() || "00000000-0000-4000-8000-000000000001";
  }

  function pmOrderSection(order) {
    const caps = FMMS.api.capabilities;
    const sapNum = order.sap_order_number
      ? `<div class="mb-2"><strong>شماره PM (SAP):</strong> <span class="mono">${FMMS.ui.escapeHtml(order.sap_order_number)}</span></div>`
      : `<div class="mb-2 text-muted">شماره PM هنوز ثبت نشده است.</div>`;

    const disabledForm = `
      <div class="demo-only-block">
        <div class="small fw-semibold mb-2">ثبت دستی PM Order</div>
        <div class="row g-2 opacity-50">
          <div class="col-md-6"><input class="form-control" disabled placeholder="شماره PM Order" /></div>
          <div class="col-md-6"><input class="form-control" disabled placeholder="وضعیت" /></div>
          <div class="col-12"><input class="form-control" disabled placeholder="توضیحات" /></div>
          <div class="col-md-6"><input class="form-control" type="date" disabled /></div>
        </div>
        <div class="demo-only-msg">ثبت PM Order در API فعلی موجود نیست.</div>
      </div>`;

    const syncBlock = caps.pmOrderSyncSap
      ? `<button type="button" class="btn btn-fmms-outline btn-sm mt-2" data-action="sync-sap" ${order.sap_order_number ? "disabled" : ""}>همگام‌سازی PM با SAP</button>`
      : "";

    return `<div class="mt-3 pt-3 border-top">${sapNum}${disabledForm}${syncBlock}</div>`;
  }

  // ---------------------------------------------------------------------
  // Transport supervisor
  // ---------------------------------------------------------------------
  function vehicleIsInactive(vehicle) {
    if (!vehicle) return false;
    return ["INACTIVE", "OUT_OF_SERVICE", "SUSPENDED"].includes(vehicle.status);
  }

  function distributionDecisionLabel(fault, vehicle) {
    if (!fault) return "—";
    if (fault.status === "CLOSED") return "خودرو قابل استفاده است";
    if (fault.status === "OPEN" && vehicleIsInactive(vehicle)) return "خودرو غیرقابل استفاده است";
    if (fault.status === "OPEN") return "در انتظار تصمیم توزیع";
    return "—";
  }

  function renderFaultItemsTable(items) {
    const caps = FMMS.api.capabilities;
    if (caps.severityScope === "fault" || !items?.length) return "";
    const rows = items.map(
      (item) => `<tr>
        <td>${FMMS.ui.escapeHtml(item.component)}</td>
        <td>${FMMS.ui.escapeHtml(item.description)}</td>
        <td>${FMMS.ui.badge(item.severity)}</td>
        <td class="mono">${FMMS.ui.escapeHtml(item.inspection_item_id || "—")}</td>
      </tr>`
    );
    return (
      `<div class="modal-section"><div class="modal-section-title">آیتم‌های خرابی (بازرسی)</div>` +
      FMMS.ui.renderTable(["قطعه", "توضیح", "شدت", "آیتم بازرسی"], rows) +
      `</div>`
    );
  }

  function hideDetailModal() {
    bootstrap.Modal.getInstance(document.getElementById("detail-modal"))?.hide();
  }

  async function showTransportDetail(order) {
    FMMS.ui.openDetailModalLoading("جزئیات دستور تعمیر");
    try {
      await ensureVehicles();
      const [fullOrder, fault] = await Promise.all([
        FMMS.api.getRepairOrder(order.id),
        order.fault_id ? FMMS.api.getFault(order.fault_id).catch(() => null) : Promise.resolve(null),
      ]);

      let vehicle = vehiclesById[fullOrder.vehicle_id];
      if (!vehicle) {
        try {
          vehicle = await FMMS.api.getVehicle(fullOrder.vehicle_id);
          vehiclesById[vehicle.id] = vehicle;
        } catch (_) {
          vehicle = null;
        }
      }

      const distributionLabel = distributionDecisionLabel(fault, vehicle);
      const reporterValue = fault?.created_by
        ? FMMS.ui.createdByLabel(fault.created_by)
        : fault?.reported_by_id
          ? `<span class="mono">${FMMS.ui.escapeHtml(fault.reported_by_id)}</span>`
          : "—";

      const orderRows = [
        ["شناسه دستور تعمیر", `<span class="mono">${FMMS.ui.escapeHtml(fullOrder.id)}</span>`],
        ["وضعیت دستور", FMMS.ui.badge(fullOrder.status)],
        ["نوع تعمیرگاه", fullOrder.workshop_type ? workshopTypeLabel(fullOrder.workshop_type) : "—"],
        ["زمان ایجاد", FMMS.ui.formatDateTime(fullOrder.created_at)],
        ["آخرین بروزرسانی", FMMS.ui.formatDateTime(fullOrder.updated_at)],
        ["شماره PM (SAP)", fullOrder.sap_order_number ? `<span class="mono">${FMMS.ui.escapeHtml(fullOrder.sap_order_number)}</span>` : "—"],
      ];

      const vehicleRows = [
        ["خودرو", vehicle ? FMMS.ui.vehicleLabel(vehicle) : `<span class="mono">${fullOrder.vehicle_id}</span>`],
        ["پلاک", vehicle ? `<span class="mono">${FMMS.ui.escapeHtml(vehicle.plate_number)}</span>` : "—"],
        ["وضعیت خودرو", vehicle ? FMMS.ui.badge(vehicle.status) : "—"],
        ["شماره تجهیز SAP", vehicle?.sap_equipment_number ? `<span class="mono">${FMMS.ui.escapeHtml(vehicle.sap_equipment_number)}</span>` : "—"],
      ];

      const faultRows = fault
        ? [
            ["شناسه خرابی", `<span class="mono">${FMMS.ui.escapeHtml(fault.id)}</span>`],
            ["کد خرابی", `<span class="mono">${FMMS.ui.escapeHtml(fault.code)}</span>`],
            ["توضیح خرابی", FMMS.ui.escapeHtml(fault.description)],
            ["وضعیت خرابی", FMMS.ui.badge(fault.status)],
            ["شدت", FMMS.ui.badge(fault.severity)],
            ["ثبت‌کننده", reporterValue],
            ["زمان ثبت خرابی", FMMS.ui.formatDateTime(fault.reported_at || fault.created_at)],
            ["تصمیم توزیع", distributionLabel],
            ["شناسه بازرسی", fault.inspection_id ? `<span class="mono">${fault.inspection_id}</span>` : "—"],
          ]
        : [["خرابی مرتبط", `<span class="text-muted">اطلاعات خرابی در دسترس نیست.</span>`]];

      let actionBar = "";
      if (fullOrder.status === "CREATED") {
        actionBar = `<div class="transport-detail-actions">
          <p class="small text-muted mb-2">پس از بررسی جزئیات، تایید ترابری را ثبت کنید.</p>
          <button type="button" class="btn btn-fmms-success btn-sm" id="transport-detail-approve">تایید ترابری</button>
        </div>`;
      } else if (fullOrder.status === "APPROVED") {
        actionBar = `<div class="transport-detail-actions">
          <p class="small text-muted mb-2">دستور تایید شده — نوع تعمیرگاه را انتخاب کنید.</p>
          <button type="button" class="btn btn-fmms-success btn-sm" id="transport-detail-assign">تخصیص تعمیرگاه</button>
        </div>`;
      }

      let body =
        `<div class="modal-section"><div class="modal-section-title">خودرو</div>${FMMS.ui.renderDl(vehicleRows)}</div>` +
        `<div class="modal-section"><div class="modal-section-title">خرابی و توزیع</div>${FMMS.ui.renderDl(faultRows)}</div>` +
        `<div class="modal-section"><div class="modal-section-title">دستور تعمیر</div>${FMMS.ui.renderDl(orderRows)}</div>` +
        renderFaultItemsTable(fault?.items) +
        (FMMS.api.capabilities.repairTimeline
          ? `<div class="modal-section"><div class="modal-section-title">تاریخچه مراحل</div><div id="transport-detail-timeline" class="text-muted">در حال بارگذاری…</div></div>`
          : "") +
        actionBar;

      const titlePlate = vehicle?.plate_number || fullOrder.id.slice(0, 8);
      FMMS.ui.openDetailModal(`بررسی تایید ترابری · ${titlePlate}`, body);

      document.getElementById("transport-detail-approve")?.addEventListener("click", async (e) => {
        const btn = e.currentTarget;
        btn.disabled = true;
        const prev = btn.textContent;
        btn.textContent = "در حال تایید…";
        try {
          await FMMS.api.approveRepair(fullOrder.id);
          FMMS.ui.toast("تعمیر تایید شد.");
          hideDetailModal();
          renderTransport("repairs");
        } catch (err) {
          FMMS.ui.toast(err.message, "error");
          btn.disabled = false;
          btn.textContent = prev;
        }
      });

      document.getElementById("transport-detail-assign")?.addEventListener("click", () => {
        hideDetailModal();
        assignWorkshop(fullOrder);
      });

      if (FMMS.api.capabilities.repairTimeline) {
        try {
          const events = await FMMS.api.getRepairTimeline(fullOrder.id);
          const labeled = events.map((e) => ({
            ...e,
            event: EVENT_LABELS[e.event] || e.event,
          }));
          const host = document.getElementById("transport-detail-timeline");
          if (host) host.innerHTML = FMMS.ui.renderTimeline(labeled);
        } catch (_) {
          const host = document.getElementById("transport-detail-timeline");
          if (host) host.textContent = "بارگذاری تاریخچه ممکن نشد.";
        }
      }
    } catch (err) {
      FMMS.ui.openDetailModal("جزئیات دستور تعمیر", `<div class="text-danger">${FMMS.ui.escapeHtml(err.message)}</div>`);
      FMMS.ui.toast(err.message, "error");
    }
  }

  async function approve(order, btn) {
    btn.disabled = true;
    const prev = btn.textContent;
    btn.textContent = "در حال تایید…";
    try {
      await FMMS.api.approveRepair(order.id);
      FMMS.ui.toast("تعمیر تایید شد.");
      renderTransport("repairs");
    } catch (err) {
      FMMS.ui.toast(err.message, "error");
      btn.disabled = false;
      btn.textContent = prev;
    }
  }

  function assignWorkshop(order) {
    openActionModal(
      "تخصیص نوع تعمیرگاه",
      `<div class="mb-3">
         <div class="form-label mb-2">نوع تعمیرگاه:</div>
         <label class="d-block mb-2"><input type="radio" name="workshop-type" value="INTERNAL" checked /> داخلی</label>
         <label class="d-block"><input type="radio" name="workshop-type" value="EXTERNAL" /> خارجی</label>
       </div>
       <div class="mb-2">
         <label class="form-label">شناسه تعمیرگاه (اختیاری)</label>
         <input class="form-control mono" id="workshop-id-input" placeholder="مثلاً central-workshop" />
       </div>`,
      async () => {
        const type = document.querySelector('input[name="workshop-type"]:checked')?.value || "INTERNAL";
        const workshopId = document.getElementById("workshop-id-input").value.trim() || undefined;
        await FMMS.api.assignWorkshop(order.id, type, workshopId);
        FMMS.ui.toast("تعمیرگاه تخصیص یافت.");
        renderTransport("repairs");
      }
    );
  }

  function transportActions(order) {
    const parts = [`<button type="button" class="btn btn-fmms-outline btn-sm" data-action="detail">مشاهده جزئیات</button>`];
    if (order.status === "CREATED") {
      parts.push(`<button type="button" class="btn btn-fmms-success btn-sm" data-action="approve">تایید ترابری</button>`);
    }
    if (order.status === "APPROVED") {
      parts.push(`<button type="button" class="btn btn-fmms-success btn-sm" data-action="assign-workshop">تخصیص تعمیرگاه</button>`);
    }
    if (order.status === "COMPLETED") {
      return `<div class="d-flex flex-wrap gap-1 align-items-center">${parts.join("")}<span class="reviewed-notice">تکمیل شده</span></div>`;
    }
    if (order.status === "CANCELLED") {
      return `<div class="d-flex flex-wrap gap-1 align-items-center">${parts.join("")}<span class="reviewed-notice">لغو شده</span></div>`;
    }
    if (parts.length === 1) {
      parts.push(`<span class="reviewed-notice">این مرحله قبلاً انجام شده است.</span>`);
    }
    return `<div class="d-flex flex-wrap gap-1">${parts.join("")}</div>`;
  }

  function transportRow(order) {
    const v = vehiclesById[order.vehicle_id];
    return `<tr data-id="${order.id}">
      <td>${FMMS.ui.vehicleLabel(v)}</td>
      <td class="mono">${order.id}</td>
      <td>${FMMS.ui.badge(order.status)}</td>
      <td>${order.workshop_type ? workshopTypeLabel(order.workshop_type) : "—"}</td>
      <td>${transportActions(order)}</td>
    </tr>`;
  }

  async function loadTransportOrders() {
    if (transportFilter === "vehicle" && transportVehicleId) {
      const page = FMMS.api.asPage(await FMMS.api.listRepairOrders(transportVehicleId));
      return { orders: page.results, totalCount: page.results.length, pendingAfterDistribution: false };
    }

    if (transportFilter === "all") {
      const res = await FMMS.api.listAllRepairOrders();
      return { orders: res.results, totalCount: res.results.length, pendingAfterDistribution: false };
    }

    const res = await FMMS.api.listRepairOrdersAfterDistribution();
    const orders = res.results.filter((r) => TRANSPORT_PENDING.has(r.status));
    return {
      orders,
      totalCount: res.results.length,
      pendingAfterDistribution: orders.length > 0,
    };
  }

  function transportEmptyState(totalCount, pendingAfterDistribution) {
    if (transportFilter === "pending" && totalCount > 0 && !pendingAfterDistribution) {
      return `<tr><td colspan="5"><div class="empty-state">
        <div class="title">دستور تعمیر این خرابی قبلاً تکمیل شده است</div>
        <div>${totalCount} دستور تعمیر پس از توزیع وجود دارد، اما هیچ‌کدام در وضعیت «CREATED» یا «APPROVED» نیست. برای جریان جدید، یک بازرسی تازه ثبت کنید.</div>
      </div></td></tr>`;
    }
    if (transportFilter === "pending" && totalCount > 0) {
      return `<tr><td colspan="5"><div class="empty-state">
        <div class="title">دستوری در انتظار تایید ترابری نیست</div>
        <div>${totalCount} دستور تعمیر پس از توزیع وجود دارد؛ برای مشاهده همه، فیلتر «همه دستورات تعمیر» را انتخاب کنید.</div>
      </div></td></tr>`;
    }
    return `<tr><td colspan="5"><div class="empty-state">
      <div class="title">دستور تعمیری یافت نشد</div>
      <div>پس از «تصمیم توزیع» روی خرابی باز، دستور تعمیر مرتبط (وضعیت CREATED) این‌جا نمایش داده می‌شود.</div>
    </div></td></tr>`;
  }

  function wireTransportToolbar() {
    if (transportToolbarWired) return;
    const vehicleWrap = document.getElementById("transport-vehicle-filter-wrap");
    const vehicleSelect = document.getElementById("transport-vehicle-filter");
    if (!vehicleWrap || !vehicleSelect) return;

    document.querySelectorAll(".transport-filter-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".transport-filter-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        transportFilter = btn.dataset.transportFilter;
        vehicleWrap.style.display = transportFilter === "vehicle" ? "flex" : "none";
        renderTransport("repairs");
      });
    });

    vehicleSelect.addEventListener("change", () => {
      transportVehicleId = vehicleSelect.value;
      if (transportFilter === "vehicle") renderTransport("repairs");
    });

    transportToolbarWired = true;
  }

  async function populateTransportVehicleFilter() {
    const select = document.getElementById("transport-vehicle-filter");
    if (!select) return;

    const vehicles = Object.values(vehiclesById).sort((a, b) =>
      (a.plate_number || "").localeCompare(b.plate_number || "", "fa")
    );
    select.innerHTML = vehicles.length
      ? vehicles
          .map(
            (v) =>
              `<option value="${v.id}">${FMMS.ui.escapeHtml(v.plate_number)} — ${FMMS.ui.vehicleLabel(v)}</option>`
          )
          .join("")
      : `<option value="">—</option>`;
    if (vehicles.length) transportVehicleId = vehicles[0].id;
  }

  async function renderTransport(view) {
    const activeView = view || "repairs";
    const tbody = document.getElementById("transport-tbody");
    if (activeView === "repairs" && tbody) {
      wireTransportToolbar();
      tbody.innerHTML = `<tr><td colspan="5">در حال بارگذاری…</td></tr>`;
      try {
        await ensureVehicles();
        await populateTransportVehicleFilter();
        const { orders, totalCount, pendingAfterDistribution } = await loadTransportOrders();

        tbody.innerHTML = orders.length ? orders.map(transportRow).join("") : transportEmptyState(totalCount, pendingAfterDistribution);

        tbody.querySelectorAll("tr[data-id]").forEach((tr) => {
          const order = orders.find((r) => r.id === tr.dataset.id);
          tr.querySelector('[data-action="detail"]')?.addEventListener("click", () => showTransportDetail(order));
          tr.querySelector('[data-action="approve"]')?.addEventListener("click", (e) => approve(order, e.currentTarget));
          tr.querySelector('[data-action="assign-workshop"]')?.addEventListener("click", () => assignWorkshop(order));
        });
      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5">${FMMS.ui.escapeHtml(err.message)}</td></tr>`;
        FMMS.ui.toast(err.message, "error");
      }
    }
    if (activeView === "materials") {
      await renderTransportMaterialRequests();
    }
    if (activeView === "invoices") {
      await renderTransportExternalInvoices();
    }
  }

  // ---------------------------------------------------------------------
  // Transport — material requests & invoices
  // ---------------------------------------------------------------------
  async function renderTransportMaterialRequests() {
    const host = document.getElementById("transport-material-requests");
    if (!host) return;
    if (!FMMS.api.capabilities.materialRequest) {
      host.innerHTML = `<div class="demo-only-msg">API درخواست قطعه در این نسخه موجود نیست.</div>`;
      return;
    }
    try {
      const page = FMMS.api.asPage(await FMMS.api.listMaterialRequests());
      const pending = page.results.filter((mr) => mr.status === "REQUESTED");
      if (!pending.length) {
        host.innerHTML = `<div class="empty-state"><div class="title">درخواست قطعه‌ای در انتظار تایید نیست</div></div>`;
        return;
      }
      host.innerHTML = pending
        .map(
          (mr) => `<div class="card-fmms p-3 mb-2" data-mr-id="${mr.id}">
            <div class="d-flex flex-wrap justify-content-between gap-2 align-items-start">
              <div>
                <div class="fw-semibold mb-1">درخواست قطعه ${FMMS.ui.badge(mr.status)}</div>
                <div class="small text-muted mono mb-2">Repair: ${FMMS.ui.escapeHtml(mr.repair_order_id)}</div>
                <ul class="mb-0 small">${(mr.items || [])
                  .map(
                    (item) =>
                      `<li><span class="mono">${FMMS.ui.escapeHtml(item.material_number)}</span> — ${FMMS.ui.escapeHtml(item.quantity)} ${FMMS.ui.escapeHtml(item.unit_of_measure)}</li>`
                  )
                  .join("")}</ul>
                <div class="material-flow-hint mt-2 small text-muted">درخواست قطعه ← بررسی ترابری ← موجودی انبار ← تحویل قطعه</div>
              </div>
              <div class="d-flex flex-wrap gap-1">
                <button type="button" class="btn btn-fmms-success btn-sm" data-action="approve-mr">تایید</button>
                <button type="button" class="btn btn-fmms-danger btn-sm" data-action="reject-mr">رد</button>
              </div>
            </div>
          </div>`
        )
        .join("");
      host.querySelectorAll("[data-mr-id]").forEach((card) => {
        const id = card.dataset.mrId;
        card.querySelector('[data-action="approve-mr"]')?.addEventListener("click", async (e) => {
          e.currentTarget.disabled = true;
          try {
            const result = await FMMS.api.approveMaterialRequest(id);
            const msg =
              result.status === "PURCHASE_REQUIRED"
                ? "موجودی کافی نیست — درخواست خرید ثبت شد."
                : "قطعه از انبار صادر شد.";
            FMMS.ui.toast(msg);
            renderTransport("materials");
          } catch (err) {
            FMMS.ui.toast(err.message, "error");
            e.currentTarget.disabled = false;
          }
        });
        card.querySelector('[data-action="reject-mr"]')?.addEventListener("click", async (e) => {
          e.currentTarget.disabled = true;
          try {
            await FMMS.api.rejectMaterialRequest(id);
            FMMS.ui.toast("درخواست قطعه رد شد.");
            renderTransport("materials");
          } catch (err) {
            FMMS.ui.toast(err.message, "error");
            e.currentTarget.disabled = false;
          }
        });
      });
    } catch (err) {
      host.innerHTML = `<div class="text-danger">${FMMS.ui.escapeHtml(err.message)}</div>`;
    }
  }

  async function renderTransportExternalInvoices() {
    const host = document.getElementById("transport-external-invoices");
    if (!host) return;
    if (!FMMS.api.capabilities.externalInvoice) {
      host.innerHTML = `<div class="demo-only-msg">API فاکتور خارجی در این نسخه موجود نیست.</div>`;
      return;
    }
    try {
      const page = FMMS.api.asPage(await FMMS.api.listExternalInvoices());
      const pending = page.results.filter((inv) => inv.status === "UPLOADED");
      if (!pending.length) {
        host.innerHTML = `<div class="empty-state"><div class="title">فاکتور تاییدنشده‌ای وجود ندارد</div></div>`;
        return;
      }
      host.innerHTML = pending
        .map(
          (inv) => `<div class="d-flex flex-wrap justify-content-between gap-2 align-items-center mb-2 p-2 border rounded" data-inv-id="${inv.id}">
            <div>
              <div>${FMMS.ui.badge(inv.status)} مبلغ: <span class="mono">${FMMS.ui.escapeHtml(inv.amount)} ${FMMS.ui.escapeHtml(inv.currency)}</span></div>
              <div class="small text-muted mono">Repair: ${FMMS.ui.escapeHtml(inv.repair_order_id)}</div>
            </div>
            <button type="button" class="btn btn-fmms-success btn-sm" data-action="approve-inv">تایید فاکتور</button>
          </div>`
        )
        .join("");
      host.querySelectorAll("[data-inv-id]").forEach((row) => {
        row.querySelector('[data-action="approve-inv"]')?.addEventListener("click", async (e) => {
          e.currentTarget.disabled = true;
          try {
            await FMMS.api.approveExternalInvoice(row.dataset.invId);
            FMMS.ui.toast("فاکتور تایید شد.");
            renderTransport("invoices");
          } catch (err) {
            FMMS.ui.toast(err.message, "error");
            e.currentTarget.disabled = false;
          }
        });
      });
    } catch (err) {
      host.innerHTML = `<div class="text-danger">${FMMS.ui.escapeHtml(err.message)}</div>`;
    }
  }

  // ---------------------------------------------------------------------
  // Workshop
  // ---------------------------------------------------------------------
  async function acceptRepair(order, btn) {
    btn.disabled = true;
    try {
      await FMMS.api.acceptRepair(order.id);
      FMMS.ui.toast("تعمیر پذیرفته شد.");
      renderWorkshop("orders");
    } catch (err) {
      FMMS.ui.toast(err.message, "error");
      btn.disabled = false;
    }
  }

  async function rejectRepair(order, btn) {
    btn.disabled = true;
    try {
      await FMMS.api.rejectRepair(order.id);
      FMMS.ui.toast("تعمیر رد شد — خودرو آماده فعال‌سازی است.");
      renderWorkshop("orders");
    } catch (err) {
      FMMS.ui.toast(err.message, "error");
      btn.disabled = false;
    }
  }

  async function start(order, btn) {
    btn.disabled = true;
    const prev = btn.textContent;
    btn.textContent = "در حال شروع…";
    try {
      const fresh = await FMMS.api.getRepairOrder(order.id);
      if (!canShowStartRepair(fresh)) {
        FMMS.ui.toast(
          fresh.status === "IN_PROGRESS"
            ? "تعمیر قبلاً آغاز شده است."
            : "وضعیت دستور تعمیر تغییر کرده است.",
          "error"
        );
        renderWorkshop("orders");
        return;
      }
      await FMMS.api.startRepair(fresh.id);
      FMMS.ui.toast("تعمیر آغاز شد.");
      renderWorkshop("orders");
    } catch (err) {
      FMMS.ui.toast(err.message, "error");
      btn.disabled = false;
      btn.textContent = prev;
    }
  }

  function addActivity(order) {
    openActionModal(
      "ثبت فعالیت تعمیر",
      `<div class="mb-2"><label class="form-label">شرح فعالیت</label>
        <input class="form-control" id="activity-desc" placeholder="مثلاً بررسی و تعویض کمپرسور یخچال" /></div>
       <div><label class="form-label">ساعت کار</label>
        <input class="form-control" id="activity-hours" type="number" step="0.5" value="1" /></div>`,
      async () => {
        const description = document.getElementById("activity-desc").value.trim();
        if (!description) throw new FMMS.ApiError("شرح فعالیت الزامی است.", 400);
        await FMMS.api.addRepairActivity(order.id, {
          description,
          labor_hours: document.getElementById("activity-hours").value || "1",
          performed_by_id: defaultTechnicianId(),
          performed_at: new Date().toISOString(),
        });
        FMMS.ui.toast("فعالیت تعمیر ثبت شد.");
        renderWorkshop("orders");
      }
    );
  }

  function requestMaterial(order) {
    if (!FMMS.api.capabilities.materialRequest) {
      FMMS.ui.toast("API درخواست قطعه در نسخه فعلی موجود نیست.", "error");
      return;
    }
    openActionModal(
      "درخواست قطعه",
      `<div class="material-flow-hint small text-muted mb-3">درخواست قطعه ← بررسی ترابری ← موجودی انبار ← تحویل قطعه<br/>یا: عدم موجودی ← ثبت سفارش خرید ← دریافت قطعه</div>
       <div class="mb-2"><label class="form-label">کد قطعه (Material Number)</label>
        <input class="form-control mono" id="mr-material" placeholder="مثلاً 000000012345" /></div>
       <div class="row g-2">
         <div class="col-6"><label class="form-label">تعداد</label>
           <input class="form-control" id="mr-qty" type="number" min="1" value="1" /></div>
         <div class="col-6"><label class="form-label">واحد</label>
           <input class="form-control" id="mr-unit" value="EA" /></div>
       </div>`,
      async () => {
        const material = document.getElementById("mr-material").value.trim();
        const quantity = document.getElementById("mr-qty").value.trim() || "1";
        const unit = document.getElementById("mr-unit").value.trim() || "EA";
        if (!material) throw new FMMS.ApiError("کد قطعه الزامی است.", 400);
        await FMMS.api.createMaterialRequest(order.id, [
          { material_number: material, quantity, unit_of_measure: unit },
        ]);
        FMMS.ui.toast("درخواست قطعه ثبت شد.");
        renderWorkshop("orders");
      },
      "ثبت درخواست"
    );
  }

  function uploadInvoice(order) {
    if (!FMMS.api.capabilities.externalInvoice) {
      FMMS.ui.toast("API فاکتور خارجی در نسخه فعلی موجود نیست.", "error");
      return;
    }
    openActionModal(
      "ثبت فاکتور تعمیرگاه خارجی",
      `<div class="small text-muted mb-3">ارسال به تعمیرگاه خارجی ← تعمیر ← تحویل خودرو ← ثبت فاکتور ← تایید ترابری</div>
       <div class="mb-2"><label class="form-label">مبلغ</label>
         <input class="form-control mono" id="inv-amount" placeholder="500000.00" /></div>
       <div class="mb-2"><label class="form-label">ارز</label>
         <input class="form-control" id="inv-currency" value="IRR" maxlength="3" /></div>
       <div class="mb-2"><label class="form-label">شناسه فروشنده (اختیاری)</label>
         <input class="form-control" id="inv-vendor" /></div>
       <div class="mb-2"><label class="form-label">مرجع سند (اختیاری)</label>
         <input class="form-control" id="inv-document" placeholder="URL یا شماره سند" /></div>`,
      async () => {
        const amount = document.getElementById("inv-amount").value.trim();
        const currency = document.getElementById("inv-currency").value.trim() || "IRR";
        if (!amount) throw new FMMS.ApiError("مبلغ الزامی است.", 400);
        await FMMS.api.uploadExternalInvoice(order.id, {
          amount,
          currency,
          vendor_id: document.getElementById("inv-vendor").value.trim() || null,
          document: document.getElementById("inv-document").value.trim() || null,
        });
        FMMS.ui.toast("فاکتور ثبت شد.");
        renderWorkshop("orders");
      },
      "ثبت فاکتور"
    );
  }

  const ALREADY_COMPLETED_STATUSES = new Set([
    "WAITING_DRIVER_CONFIRMATION",
    "ACCEPTED_BY_DRIVER",
    "CANCELLED",
  ]);
  const ALREADY_COMPLETED_MESSAGE = "این تعمیر قبلاً تکمیل شده و منتظر تایید راننده است.";

  async function complete(order, btn) {
    if (btn.disabled) return;
    btn.disabled = true;
    const prev = btn.textContent;
    btn.textContent = "در حال اتمام…";
    try {
      const fresh = await FMMS.api.getRepairOrder(order.id);
      if (ALREADY_COMPLETED_STATUSES.has(fresh.status)) {
        FMMS.ui.toast(ALREADY_COMPLETED_MESSAGE, "error");
        renderWorkshop("orders");
        return;
      }
      if (fresh.status !== "IN_PROGRESS") {
        FMMS.ui.toast("وضعیت دستور تعمیر برای اتمام تعمیر مناسب نیست.", "error");
        renderWorkshop("orders");
        return;
      }
      await FMMS.api.completeRepair(fresh.id);
      FMMS.ui.toast("تعمیر فنی پایان یافت. منتظر تایید راننده.");
      renderWorkshop("orders");
    } catch (err) {
      FMMS.ui.toast(err.message, "error");
      btn.disabled = false;
      btn.textContent = prev;
    }
  }

  async function countMaterialRequests(repairOrderId) {
    try {
      const page = FMMS.api.asPage(await FMMS.api.listMaterialRequests());
      return page.results.filter((mr) => mr.repair_order_id === repairOrderId).length;
    } catch (_) {
      return 0;
    }
  }

  const WORKSHOP_START_STATUSES = new Set([
    "WORKSHOP_ASSIGNED",
    "ASSIGNED",
    "WAITING_WORKSHOP_CONFIRMATION",
  ]);

  async function enrichWorkshopOrders(orders) {
    return Promise.all(
      orders.map(async (order) => {
        const fresh = await FMMS.api.getRepairOrder(order.id);
        const materialRequestCount = await countMaterialRequests(fresh.id);
        return { ...fresh, materialRequestCount };
      })
    );
  }

  function canShowStartRepair(order) {
    return WORKSHOP_START_STATUSES.has(order.status);
  }

  function workshopActions(order) {
    const actions = [];
    const isInternal = order.workshop_type === "INTERNAL";
    const isExternal = order.workshop_type === "EXTERNAL";

    if (order.status === "WORKSHOP_ASSIGNED" && isInternal) {
      actions.push(
        `<button class="btn btn-fmms-success btn-sm" data-action="accept">تایید تعمیر</button>`,
        `<button class="btn btn-fmms-danger btn-sm" data-action="reject">رد تعمیر</button>`
      );
    }
    if (order.status === "WORKSHOP_ASSIGNED" && isExternal && canShowStartRepair(order)) {
      actions.push(`<button class="btn btn-fmms-primary btn-sm" data-action="start">شروع تعمیر خارجی</button>`);
    }
    if (order.status === "WAITING_WORKSHOP_CONFIRMATION" && isInternal && canShowStartRepair(order)) {
      actions.push(`<button class="btn btn-fmms-primary btn-sm" data-action="start">شروع تعمیر</button>`);
    }
    if (order.status === "ASSIGNED" && canShowStartRepair(order)) {
      actions.push(`<button class="btn btn-fmms-primary btn-sm" data-action="start">شروع تعمیر</button>`);
    }
    if (order.status === "IN_PROGRESS") {
      actions.push(`<span class="reviewed-notice workshop-in-progress-notice">تعمیر در حال انجام است</span>`);
      actions.push(
        `<button class="btn btn-fmms-outline btn-sm" data-action="request-material">درخواست قطعه</button>`,
        `<button class="btn btn-fmms-outline btn-sm" data-action="activity">ثبت فعالیت</button>`,
        `<button class="btn btn-fmms-success btn-sm" data-action="complete">اتمام تعمیر</button>`
      );
    }
    if (
      (order.status === "WAITING_DRIVER_CONFIRMATION" || order.status === "ACCEPTED_BY_DRIVER") &&
      isExternal
    ) {
      actions.push(`<button class="btn btn-fmms-outline btn-sm" data-action="invoice">ثبت فاکتور</button>`);
    }
    if (order.status === "WAITING_DRIVER_CONFIRMATION") {
      actions.push(`<span class="reviewed-notice">منتظر تایید راننده</span>`);
    }
    if (order.status === "ACCEPTED_BY_DRIVER") {
      actions.push(`<span class="reviewed-notice">تایید راننده — خودرو فعال</span>`);
    }
    if (order.status === "CANCELLED") {
      return `<div class="alert-fmms alert-fmms-warn mb-0 py-2 px-3"><strong>تعمیر رد شد</strong><div class="small">خودرو آماده فعال‌سازی است</div></div>`;
    }
    if (order.status === "REJECTED_BY_DRIVER") {
      return `<span class="reviewed-notice">رد راننده — دستور جدید ایجاد شد</span>`;
    }
    actions.push(`<button class="btn btn-fmms-outline btn-sm" data-action="timeline">تاریخچه</button>`);
    return actions.join(" ");
  }

  function workshopRow(order) {
    const v = vehiclesById[order.vehicle_id];
    const mrCount = order.materialRequestCount ?? 0;
    return `<tr data-id="${order.id}">
      <td>${FMMS.ui.vehicleLabel(v)}</td>
      <td class="mono">${order.sap_order_number || order.id}</td>
      <td>${order.workshop_type ? workshopTypeLabel(order.workshop_type) : "—"}</td>
      <td>${FMMS.ui.badge(order.status)}</td>
      <td>${mrCount ? `<span class="mono">${mrCount}</span> مورد` : "—"}</td>
      <td class="workshop-actions-cell">${workshopActions(order)}</td>
    </tr>`;
  }

  async function renderWorkshopMaterialsList() {
    const host = document.getElementById("workshop-material-requests");
    if (!host) return;
    if (!FMMS.api.capabilities.materialRequest) {
      host.innerHTML = `<div class="demo-only-msg">API درخواست قطعه در این نسخه موجود نیست.</div>`;
      return;
    }
    host.innerHTML = `<div class="text-muted">در حال بارگذاری…</div>`;
    try {
      await ensureVehicles();
      const page = FMMS.api.asPage(await FMMS.api.listMaterialRequests());
      if (!page.results.length) {
        host.innerHTML = `<div class="empty-state"><div class="title">درخواست قطعه‌ای ثبت نشده است</div><div>از «دستورات تعمیر» می‌توانید درخواست قطعه ثبت کنید.</div></div>`;
        return;
      }
      host.innerHTML = page.results
        .map((mr) => `<div class="card-fmms p-3 mb-2">
            <div class="d-flex flex-wrap justify-content-between gap-2 align-items-start">
              <div>
                <div class="fw-semibold mb-1">درخواست قطعه ${FMMS.ui.badge(mr.status)}</div>
                <div class="small text-muted mb-1">دستور تعمیر: <span class="mono">${FMMS.ui.escapeHtml(mr.repair_order_id)}</span></div>
                <ul class="mb-0 small">${(mr.items || [])
                  .map(
                    (item) =>
                      `<li><span class="mono">${FMMS.ui.escapeHtml(item.material_number)}</span> — ${FMMS.ui.escapeHtml(item.quantity)} ${FMMS.ui.escapeHtml(item.unit_of_measure)}</li>`
                  )
                  .join("")}</ul>
              </div>
              <button type="button" class="btn btn-fmms-outline btn-sm" data-action="goto-orders">مشاهده دستور</button>
            </div>
          </div>`)
        .join("");
      host.querySelectorAll('[data-action="goto-orders"]').forEach((btn) => {
        btn.addEventListener("click", () => FMMS.shell.navigate("workshop-orders"));
      });
    } catch (err) {
      host.innerHTML = `<div class="text-danger">${FMMS.ui.escapeHtml(err.message)}</div>`;
    }
  }

  async function renderWorkshopHistoryList() {
    const host = document.getElementById("workshop-history-list");
    if (!host) return;
    host.innerHTML = `<div class="text-muted">در حال بارگذاری…</div>`;
    try {
      await ensureVehicles();
      const res = await FMMS.api.listAllRepairOrders();
      const orders = res.results
        .slice()
        .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
      if (!orders.length) {
        host.innerHTML = `<div class="empty-state"><div class="title">تاریخچه‌ای یافت نشد</div></div>`;
        return;
      }
      host.innerHTML = `<div class="table-fmms-wrap"><table class="table-fmms"><thead><tr>
        <th>خودرو</th><th>دستور تعمیر</th><th>وضعیت</th><th>آخرین به‌روزرسانی</th><th>عملیات</th>
      </tr></thead><tbody>${orders
        .map((order) => {
          const v = vehiclesById[order.vehicle_id];
          return `<tr data-id="${order.id}">
            <td>${FMMS.ui.vehicleLabel(v)}</td>
            <td class="mono">${FMMS.ui.escapeHtml(order.id)}</td>
            <td>${FMMS.ui.badge(order.status)}</td>
            <td>${FMMS.ui.formatDateTime(order.updated_at)}</td>
            <td><button type="button" class="btn btn-fmms-outline btn-sm" data-action="timeline">تاریخچه</button></td>
          </tr>`;
        })
        .join("")}</tbody></table></div>`;
      host.querySelectorAll("tr[data-id]").forEach((tr) => {
        const order = orders.find((r) => r.id === tr.dataset.id);
        tr.querySelector('[data-action="timeline"]')?.addEventListener("click", () => showTimeline(order));
      });
    } catch (err) {
      host.innerHTML = `<div class="text-danger">${FMMS.ui.escapeHtml(err.message)}</div>`;
    }
  }

  async function renderWorkshop(view) {
    const activeView = view || "orders";
    if (activeView === "orders") {
      const tbody = document.getElementById("workshop-tbody");
      if (!tbody) return;
      tbody.innerHTML = `<tr><td colspan="6">در حال بارگذاری…</td></tr>`;
      try {
        await ensureVehicles();
        const res = await FMMS.api.listAllRepairOrders();
        const filtered = res.results.filter((r) =>
          [
            "WORKSHOP_ASSIGNED",
            "WAITING_WORKSHOP_CONFIRMATION",
            "ASSIGNED",
            "IN_PROGRESS",
            "WAITING_PARTS",
            "WAITING_DRIVER_CONFIRMATION",
            "ACCEPTED_BY_DRIVER",
            "REJECTED_BY_DRIVER",
            "CANCELLED",
          ].includes(r.status)
        );
        const relevant = await enrichWorkshopOrders(filtered);

        tbody.innerHTML = relevant.length
          ? relevant.map(workshopRow).join("")
          : `<tr><td colspan="6"><div class="empty-state"><div class="title">کاری در تعمیرگاه در جریان نیست</div></div></td></tr>`;

        FMMS.shell.refreshWorkshopWizard?.(relevant);

        tbody.querySelectorAll("tr[data-id]").forEach((tr) => {
          const order = relevant.find((r) => r.id === tr.dataset.id);
          tr.querySelector('[data-action="accept"]')?.addEventListener("click", (e) => acceptRepair(order, e.currentTarget));
          tr.querySelector('[data-action="reject"]')?.addEventListener("click", (e) => rejectRepair(order, e.currentTarget));
          tr.querySelector('[data-action="start"]')?.addEventListener("click", (e) => start(order, e.currentTarget));
          tr.querySelector('[data-action="request-material"]')?.addEventListener("click", () => requestMaterial(order));
          tr.querySelector('[data-action="activity"]')?.addEventListener("click", () => addActivity(order));
          tr.querySelector('[data-action="complete"]')?.addEventListener("click", (e) => complete(order, e.currentTarget));
          tr.querySelector('[data-action="invoice"]')?.addEventListener("click", () => uploadInvoice(order));
          tr.querySelector('[data-action="timeline"]')?.addEventListener("click", () => showTimeline(order));
        });
      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6">${FMMS.ui.escapeHtml(err.message)}</td></tr>`;
        FMMS.ui.toast(err.message, "error");
      }
    }
    if (activeView === "materials") {
      await renderWorkshopMaterialsList();
    }
    if (activeView === "history") {
      await renderWorkshopHistoryList();
    }
  }

  FMMS.pages.repair = { renderTransport, renderWorkshop };
})(window.FMMS);
