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
    FAULT_CREATED: "ثبت خرابی",
    DISTRIBUTION_APPROVED: "تایید توزیع",
    TRANSPORT_APPROVED: "تایید ترابری",
    WORKSHOP_ASSIGNED: "انتخاب تعمیرگاه",
    REPAIR_STARTED: "شروع تعمیر",
    REPAIR_COMPLETED: "اتمام تعمیر",
  };

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
    document.getElementById("timeline-modal-title").textContent = "تاریخچه تعمیر";
    document.getElementById("timeline-modal-body").innerHTML = `<div class="text-muted">در حال بارگذاری…</div>`;
    getTimelineModal().show();
    try {
      const events = await FMMS.api.getRepairTimeline(order.id);
      const labeled = events.map((e) => ({
        ...e,
        event: EVENT_LABELS[e.event] || e.event,
      }));
      document.getElementById("timeline-modal-body").innerHTML = FMMS.ui.renderTimeline(labeled);
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
  async function approve(order, btn) {
    btn.disabled = true;
    const prev = btn.textContent;
    btn.textContent = "در حال تایید…";
    try {
      await FMMS.api.approveRepair(order.id);
      FMMS.ui.toast("تعمیر تایید شد.");
      renderTransport();
    } catch (err) {
      FMMS.ui.toast(err.message, "error");
      btn.disabled = false;
      btn.textContent = prev;
    }
  }

  function assignWorkshop(order) {
    openActionModal(
      "تخصیص نوع تعمیرگاه",
      `<label class="form-label">نوع تعمیرگاه</label>
       <select class="form-control" id="workshop-type-select">
         <option value="INTERNAL">تعمیرگاه داخلی</option>
         <option value="EXTERNAL">تعمیرگاه خارجی</option>
       </select>`,
      async () => {
        const type = document.getElementById("workshop-type-select").value;
        await FMMS.api.assignWorkshop(order.id, type);
        FMMS.ui.toast("تعمیرگاه تخصیص یافت.");
        renderTransport();
      }
    );
  }

  function transportActions(order) {
    if (order.status === "CREATED") {
      return `<button class="btn btn-fmms-success btn-sm" data-action="approve">تایید ترابری</button>`;
    }
    if (order.status === "APPROVED") {
      return `<button class="btn btn-fmms-success btn-sm" data-action="assign-workshop">تخصیص تعمیرگاه</button>`;
    }
    if (order.status === "COMPLETED") {
      return `<span class="reviewed-notice">این تعمیر تکمیل شده است.</span>`;
    }
    if (order.status === "CANCELLED") {
      return `<span class="reviewed-notice">این تعمیر لغو شده است.</span>`;
    }
    return `<span class="reviewed-notice">این مرحله قبلاً انجام شده است.</span>`;
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
        renderTransport();
      });
    });

    vehicleSelect.addEventListener("change", () => {
      transportVehicleId = vehicleSelect.value;
      if (transportFilter === "vehicle") renderTransport();
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

  async function renderTransport() {
    const tbody = document.getElementById("transport-tbody");
    if (!tbody) return;

    wireTransportToolbar();
    tbody.innerHTML = `<tr><td colspan="5">در حال بارگذاری…</td></tr>`;
    try {
      await ensureVehicles();
      await populateTransportVehicleFilter();
      const { orders, totalCount, pendingAfterDistribution } = await loadTransportOrders();

      tbody.innerHTML = orders.length ? orders.map(transportRow).join("") : transportEmptyState(totalCount, pendingAfterDistribution);

      tbody.querySelectorAll("tr[data-id]").forEach((tr) => {
        const order = orders.find((r) => r.id === tr.dataset.id);
        tr.querySelector('[data-action="approve"]')?.addEventListener("click", (e) => approve(order, e.currentTarget));
        tr.querySelector('[data-action="assign-workshop"]')?.addEventListener("click", () => assignWorkshop(order));
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5">${FMMS.ui.escapeHtml(err.message)}</td></tr>`;
      FMMS.ui.toast(err.message, "error");
    }
  }

  // ---------------------------------------------------------------------
  // Workshop
  // ---------------------------------------------------------------------
  function assignTechnician(order) {
    const preset = defaultTechnicianId();
    openActionModal(
      "تخصیص تعمیرکار",
      `<p class="small text-muted mb-2">پس از تخصیص تعمیرگاه، ابتدا باید تعمیرکار به دستور تعمیر اختصاص داده شود.</p>
       <label class="form-label">شناسه تعمیرکار (UUID)</label>
       <input class="form-control mono ltr-field" id="technician-id-input" value="${FMMS.ui.escapeHtml(preset)}" />`,
      async () => {
        const technicianId = document.getElementById("technician-id-input").value.trim();
        if (!technicianId) throw new FMMS.ApiError("شناسه تعمیرکار الزامی است.", 400);
        await FMMS.api.assignTechnician(order.id, technicianId);
        FMMS.session.setTechnicianId(technicianId);
        FMMS.ui.toast("تعمیرکار تخصیص یافت.");
        renderWorkshop();
      }
    );
  }

  async function start(order, btn) {
    btn.disabled = true;
    const prev = btn.textContent;
    btn.textContent = "در حال شروع…";
    try {
      await FMMS.api.startRepair(order.id);
      FMMS.ui.toast("تعمیر آغاز شد.");
      renderWorkshop();
    } catch (err) {
      FMMS.ui.toast(err.message, "error");
      btn.disabled = false;
      btn.textContent = prev;
    }
  }

  async function activateVehicle(order, btn) {
    btn.disabled = true;
    const prev = btn.textContent;
    btn.textContent = "در حال فعال‌سازی…";
    try {
      await FMMS.api.activateVehicle(order.vehicle_id);
      FMMS.ui.toast("خودرو فعال شد.");
      renderWorkshop();
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
        renderWorkshop();
      }
    );
  }

  function addPart(order) {
    openActionModal(
      "ثبت مصرف قطعه",
      `<p class="small text-muted mb-3">قطعه‌ای که از <strong>انبار موجود</strong> روی این دستور تعمیر مصرف شده است.</p>
       <div class="mb-2"><label class="form-label">کد قطعه (Material Number)</label>
        <input class="form-control mono" id="part-material" placeholder="مثلاً 4500123456" /></div>
       <div class="row g-2">
         <div class="col-6"><label class="form-label">تعداد مصرف</label>
           <input class="form-control" id="part-qty" type="number" min="1" value="1" /></div>
         <div class="col-6"><label class="form-label">واحد</label>
           <input class="form-control" id="part-unit" value="EA" /></div>
       </div>`,
      async () => {
        const material = document.getElementById("part-material").value.trim();
        if (!material) throw new FMMS.ApiError("کد قطعه الزامی است.", 400);
        await FMMS.api.addRepairPart(order.id, {
          material_number: material,
          quantity: Number(document.getElementById("part-qty").value || 1),
          unit_of_measure: document.getElementById("part-unit").value.trim() || "EA",
        });
        FMMS.ui.toast("مصرف قطعه از انبار ثبت شد.");
        renderWorkshop();
      },
      "ثبت مصرف"
    );
  }

  function addPurchaseRequisition(order) {
    if (!FMMS.api.capabilities.purchaseRequisition) {
      FMMS.ui.toast("API ثبت درخواست خرید قطعه در نسخه فعلی موجود نیست.", "error");
      return;
    }
    openActionModal(
      "درخواست خرید قطعه",
      `<p class="small text-muted mb-3">برای قطعه‌ای که در انبار <strong>موجود نیست</strong> و باید از طریق فرآیند خرید تامین شود — جدا از مصرف انبار.</p>
       <div class="mb-2"><label class="form-label">کد قطعه</label>
         <input class="form-control mono" id="pr-material" placeholder="کد ماده" /></div>
       <div class="mb-2"><label class="form-label">نام / توضیح قطعه</label>
         <input class="form-control" id="pr-desc" placeholder="توضیح قطعه" /></div>
       <div class="row g-2 mb-2">
         <div class="col-4"><label class="form-label">تعداد</label>
           <input class="form-control" id="pr-qty" value="1" /></div>
         <div class="col-4"><label class="form-label">واحد</label>
           <input class="form-control" id="pr-unit" value="EA" /></div>
         <div class="col-4"><label class="form-label">وضعیت PR</label>
           <input class="form-control" value="پیش‌نویس" disabled /></div>
       </div>`,
      async () => {
        const material = document.getElementById("pr-material").value.trim();
        const description = document.getElementById("pr-desc").value.trim();
        const quantity = document.getElementById("pr-qty").value.trim();
        const unit = document.getElementById("pr-unit").value.trim() || "EA";
        if (!material || !description || !quantity) {
          throw new FMMS.ApiError("کد قطعه، توضیح و تعداد الزامی است.", 400);
        }
        const pr = await FMMS.api.createPurchaseRequisition(order.id);
        await FMMS.api.addPurchaseRequisitionLineItem(pr.id, {
          material_number: material,
          description,
          quantity,
          unit_of_measure: unit,
        });
        FMMS.ui.toast("درخواست خرید قطعه ثبت شد.");
        renderWorkshop();
      },
      "ثبت درخواست خرید"
    );
  }

  function syncSapPm(order) {
    openActionModal(
      "همگام‌سازی PM با SAP",
      `<div class="mb-2"><label class="form-label">نوع سفارش (order_type)</label>
        <input class="form-control" id="sap-order-type" value="PM01" maxlength="10" /></div>
       <div class="mb-2"><label class="form-label">توضیحات</label>
        <input class="form-control" id="sap-desc" placeholder="توضیح PM" /></div>
       <div class="mb-2"><label class="form-label">تاریخ شروع برنامه‌ریزی‌شده</label>
        <input class="form-control" id="sap-planned" type="datetime-local" /></div>`,
      async () => {
        const order_type = document.getElementById("sap-order-type").value.trim();
        const description = document.getElementById("sap-desc").value.trim();
        const plannedRaw = document.getElementById("sap-planned").value;
        if (!order_type || !description || !plannedRaw) {
          throw new FMMS.ApiError("نوع سفارش، توضیح و تاریخ الزامی است.", 400);
        }
        await FMMS.api.syncRepairSap(order.id, {
          order_type,
          description,
          planned_start: new Date(plannedRaw).toISOString(),
        });
        FMMS.ui.toast("همگام‌سازی PM با SAP انجام شد.");
        renderWorkshop();
      },
      "همگام‌سازی"
    );
  }

  function showWorkshopOps(order) {
    const body = `<div class="small text-muted mb-2">دستور تعمیر: <span class="mono">${FMMS.ui.escapeHtml(order.id)}</span></div>${pmOrderSection(order)}`;
    FMMS.ui.openDetailModal("عملیات تعمیرگاه / PM", body);
    setTimeout(() => {
      document.querySelector("#detail-modal-body [data-action='sync-sap']")?.addEventListener("click", () => {
        bootstrap.Modal.getInstance(document.getElementById("detail-modal"))?.hide();
        syncSapPm(order);
      });
    }, 0);
  }

  async function complete(order, btn) {
    btn.disabled = true;
    const prev = btn.textContent;
    btn.textContent = "در حال اتمام…";
    try {
      await FMMS.api.completeRepair(order.id);
      FMMS.ui.toast("تعمیر پایان یافت.");
      renderWorkshop();
    } catch (err) {
      FMMS.ui.toast(err.message, "error");
      btn.disabled = false;
      btn.textContent = prev;
    }
  }

  async function countPurchaseLineItems(repairOrderId) {
    try {
      const page = FMMS.api.asPage(await FMMS.api.listPurchaseRequisitions(repairOrderId));
      return page.results.reduce((sum, pr) => sum + (pr.line_items?.length || 0), 0);
    } catch (_) {
      return 0;
    }
  }

  async function enrichWorkshopOrders(orders) {
    return Promise.all(
      orders.map(async (order) => ({
        ...order,
        purchaseLineCount: await countPurchaseLineItems(order.id),
      }))
    );
  }

  function workshopActions(order) {
    const actions = [];
    if (order.status === "WORKSHOP_ASSIGNED") {
      actions.push(`<button class="btn btn-fmms-primary btn-sm" data-action="start">شروع تعمیر</button>`);
    }
    if (order.status === "ASSIGNED") {
      actions.push(`<button class="btn btn-fmms-primary btn-sm" data-action="start">شروع تعمیر</button>`);
    }
    if (order.status === "IN_PROGRESS") {
      actions.push(
        `<button class="btn btn-fmms-danger btn-sm" data-action="buy-part">درخواست خرید قطعه</button>`,
        `<button class="btn btn-fmms-outline btn-sm" data-action="use-part">ثبت مصرف قطعه</button>`,
        `<button class="btn btn-fmms-success btn-sm" data-action="complete">اتمام تعمیر</button>`
      );
    }
    if (order.status === "COMPLETED") {
      const v = vehiclesById[order.vehicle_id];
      if (v && v.status !== "ACTIVE" && FMMS.api.capabilities.vehicleActivate) {
        actions.push(`<button class="btn btn-fmms-success btn-sm" data-action="activate">فعال‌سازی خودرو</button>`);
      }
      if (!actions.length) {
        return `<span class="reviewed-notice">این تعمیر تکمیل شده است.</span>`;
      }
    }
    if (order.status === "CANCELLED") {
      return `<span class="reviewed-notice">این تعمیر لغو شده است.</span>`;
    }
    actions.push(`<button class="btn btn-fmms-outline btn-sm" data-action="timeline">تاریخچه</button>`);
    return actions.join("");
  }

  function workshopRow(order) {
    const v = vehiclesById[order.vehicle_id];
    const activityCount = order.activities?.length || 0;
    const partCount = order.parts?.length || 0;
    const purchaseCount = order.purchaseLineCount ?? 0;
    return `<tr data-id="${order.id}">
      <td>${FMMS.ui.vehicleLabel(v)}</td>
      <td class="mono">${order.sap_order_number || order.id}</td>
      <td>${order.workshop_type ? workshopTypeLabel(order.workshop_type) : "—"}</td>
      <td>${FMMS.ui.badge(order.status)}</td>
      <td>${activityCount || "—"}</td>
      <td>${partCount ? `<span class="mono">${partCount}</span> مورد` : "—"}</td>
      <td>${purchaseCount ? `<span class="mono">${purchaseCount}</span> قلم` : "—"}</td>
      <td class="workshop-actions-cell">${workshopActions(order)}</td>
    </tr>`;
  }

  async function renderWorkshop() {
    const tbody = document.getElementById("workshop-tbody");
    tbody.innerHTML = `<tr><td colspan="8">در حال بارگذاری…</td></tr>`;
    try {
      await ensureVehicles();
      const res = await FMMS.api.listAllRepairOrders();
      const filtered = res.results.filter(
        (r) =>
          r.status === "WORKSHOP_ASSIGNED" ||
          r.status === "ASSIGNED" ||
          r.status === "IN_PROGRESS" ||
          r.status === "COMPLETED" ||
          r.status === "CANCELLED"
      );
      const relevant = await enrichWorkshopOrders(filtered);

      tbody.innerHTML = relevant.length
        ? relevant.map(workshopRow).join("")
        : `<tr><td colspan="8"><div class="empty-state"><div class="title">کاری در تعمیرگاه در جریان نیست</div></div></td></tr>`;

      tbody.querySelectorAll("tr[data-id]").forEach((tr) => {
        const order = relevant.find((r) => r.id === tr.dataset.id);
        tr.querySelector('[data-action="start"]')?.addEventListener("click", (e) => start(order, e.currentTarget));
        tr.querySelector('[data-action="buy-part"]')?.addEventListener("click", () => addPurchaseRequisition(order));
        tr.querySelector('[data-action="use-part"]')?.addEventListener("click", () => addPart(order));
        tr.querySelector('[data-action="complete"]')?.addEventListener("click", (e) => complete(order, e.currentTarget));
        tr.querySelector('[data-action="activate"]')?.addEventListener("click", (e) => activateVehicle(order, e.currentTarget));
        tr.querySelector('[data-action="timeline"]')?.addEventListener("click", () => showTimeline(order));
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="8">${FMMS.ui.escapeHtml(err.message)}</td></tr>`;
      FMMS.ui.toast(err.message, "error");
    }
  }

  FMMS.pages.repair = { renderTransport, renderWorkshop };
})(window.FMMS);
