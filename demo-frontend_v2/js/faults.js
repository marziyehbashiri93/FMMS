/**
 * Page: خرابی‌ها (full fault list)
 * Page: تایید توزیع (Distribution supervisor decision)
 */
window.FMMS = window.FMMS || {};
FMMS.pages = FMMS.pages || {};

(function (FMMS) {
  let vehiclesById = {};
  let detailWired = false;
  let toolbarWired = false;
  let currentFilter = "open";
  let filterVehicleId = "";

  const DISTRIBUTION_ACTIONABLE = new Set(["OPEN"]);

  async function ensureVehicles() {
    const res = await FMMS.api.listAllVehicles();
    vehiclesById = Object.fromEntries(res.results.map((v) => [v.id, v]));
  }

  function vehicleIsInactive(vehicle) {
    if (!vehicle) return false;
    return ["INACTIVE", "OUT_OF_SERVICE", "SUSPENDED"].includes(vehicle.status);
  }

  function getDistributionDecision(fault, vehicle) {
    if (fault.status === "CLOSED") {
      return { reviewed: true, decision: "خودرو قابل استفاده است" };
    }
    if (fault.status === "OPEN" && vehicleIsInactive(vehicle)) {
      return { reviewed: true, decision: "خودرو غیرقابل استفاده است" };
    }
    return { reviewed: false };
  }

  function distributionReviewedCell(fault, decision, vehicle) {
    const reviewer = FMMS.session.roleLabel(FMMS.session.getRole());
    const vehicleStatus = vehicle ? FMMS.ui.badge(vehicle.status) : "—";
    return `<div class="distribution-reviewed">
      <div class="distribution-reviewed-title">${FMMS.ui.escapeHtml(fault.description)}</div>
      <div class="distribution-reviewed-row"><span>وضعیت:</span> بررسی شد</div>
      <div class="distribution-reviewed-row"><span>تصمیم:</span> ${FMMS.ui.escapeHtml(decision)}</div>
      <div class="distribution-reviewed-row"><span>وضعیت خودرو:</span> ${vehicleStatus}</div>
      <div class="distribution-reviewed-row"><span>ثبت‌کننده:</span> ${FMMS.ui.escapeHtml(reviewer)}</div>
    </div>`;
  }

  function distributionActionsCell(fault, vehicle) {
    const state = getDistributionDecision(fault, vehicle);
    if (state.reviewed) {
      return distributionReviewedCell(fault, state.decision, vehicle);
    }
    if (!DISTRIBUTION_ACTIONABLE.has(fault.status)) {
      return `<span class="reviewed-notice">این خرابی قبلاً بررسی شده است.</span>`;
    }
    const groupId = `dist-actions-${fault.id}`;
    return `<div class="d-flex gap-2" id="${groupId}">
      <button class="btn btn-fmms-success btn-sm" data-action="usable">خودرو قابل استفاده است</button>
      <button class="btn btn-fmms-danger btn-sm" data-action="unusable">خودرو غیرقابل استفاده است</button>
    </div>`;
  }

  async function loadDistributionFaults() {
    const res = await FMMS.api.listFaultsFiltered("all");
    return res.results
      .filter((f) => f.status === "OPEN" || f.status === "CLOSED")
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  }


  function faultRow(f) {
    const reporter = f.created_by ? FMMS.ui.createdByLabel(f.created_by) : "—";
    return `<tr data-fault-id="${f.id}">
      <td>${FMMS.ui.vehicleLabel(vehiclesById[f.vehicle_id])}</td>
      <td class="mono">${FMMS.ui.escapeHtml(f.code)}</td>
      <td>${FMMS.ui.escapeHtml(f.description)}</td>
      <td>${FMMS.ui.badge(f.severity)}</td>
      <td>${FMMS.ui.badge(f.status)}</td>
      <td>${FMMS.ui.escapeHtml(reporter)}</td>
      <td><button type="button" class="btn btn-fmms-outline btn-sm" data-action="detail">مشاهده جزئیات</button></td>
    </tr>`;
  }

  async function findRepairOrderForFault(fault) {
    try {
      const page = FMMS.api.asPage(await FMMS.api.listRepairOrders(fault.vehicle_id));
      return page.results.find((ro) => ro.fault_id === fault.id) || null;
    } catch (_) {
      return null;
    }
  }

  function renderItemSeverityTable(items) {
    const caps = FMMS.api.capabilities;
    if (caps.severityScope === "fault") return "";
    const rows = (items || []).map(
      (item) => `<tr>
        <td>${FMMS.ui.escapeHtml(item.component)}</td>
        <td>${FMMS.ui.escapeHtml(item.description)}</td>
        <td>${FMMS.ui.badge(item.severity)}</td>
        <td class="mono">${FMMS.ui.escapeHtml(item.inspection_item_id || "—")}</td>
      </tr>`
    );
    return (
      `<h6 class="mt-3 mb-2">آیتم‌های خرابی</h6>` +
      FMMS.ui.renderTable(["قطعه / component", "توضیح", "شدت آیتم", "شناسه آیتم بازرسی"], rows)
    );
  }

  async function showFaultDetail(faultId) {
    FMMS.ui.openDetailModalLoading("جزئیات خرابی");
    try {
      const fault = await FMMS.api.getFault(faultId);
      let vehicle = vehiclesById[fault.vehicle_id];
      if (!vehicle) {
        try {
          vehicle = await FMMS.api.getVehicle(fault.vehicle_id);
          vehiclesById[vehicle.id] = vehicle;
        } catch (_) {
          vehicle = null;
        }
      }

      const repairOrder = await findRepairOrderForFault(fault);
      const repairValue = repairOrder
        ? `<span class="mono">${FMMS.ui.escapeHtml(repairOrder.id)}</span> — ${FMMS.ui.badge(repairOrder.status)}`
        : `<span class="text-muted">این اطلاعات در API فعلی موجود نیست.</span>`;

      const reporterValue = fault.created_by
        ? `${FMMS.ui.escapeHtml(fault.created_by.name)} — ${FMMS.ui.escapeHtml(fault.created_by.role)}`
        : fault.reported_by_id
          ? `<span class="mono">${FMMS.ui.escapeHtml(fault.reported_by_id)}</span>`
          : "—";

      const caps = FMMS.api.capabilities;
      const dlRows = [
        ["شناسه خرابی", `<span class="mono">${FMMS.ui.escapeHtml(fault.id)}</span>`],
        ["خودرو", vehicle ? FMMS.ui.vehicleLabel(vehicle) : `<span class="mono">${fault.vehicle_id}</span>`],
        ["پلاک", vehicle ? `<span class="mono">${FMMS.ui.escapeHtml(vehicle.plate_number)}</span>` : "—"],
        ["کد خرابی", `<span class="mono">${FMMS.ui.escapeHtml(fault.code)}</span>`],
        ["وضعیت", FMMS.ui.badge(fault.status)],
        ["توضیحات", FMMS.ui.escapeHtml(fault.description)],
        ["ثبت‌کننده", reporterValue],
        ["زمان ثبت", FMMS.ui.formatDateTime(fault.reported_at || fault.created_at)],
        ["آخرین بروزرسانی", FMMS.ui.formatDateTime(fault.updated_at)],
        ["دستور تعمیر مرتبط", repairValue],
        ["شناسه بازرسی", fault.inspection_id ? `<span class="mono">${fault.inspection_id}</span>` : "—"],
        ["اعلان SAP", fault.sap_notification_number || "—"],
      ];

      if (caps.severityScope !== "item") {
        dlRows.splice(5, 0, ["شدت کلی خرابی", FMMS.ui.badge(fault.severity)]);
      }

      const body =
        FMMS.ui.renderDl(dlRows) +
        FMMS.ui.renderFaultSeverityBlock(fault) +
        renderItemSeverityTable(fault.items) +
        (repairOrder && FMMS.api.capabilities.repairTimeline
          ? `<h6 class="mt-3 mb-2">تاریخچه تعمیر</h6><div id="fault-detail-timeline" class="text-muted">در حال بارگذاری…</div>`
          : "");

      FMMS.ui.openDetailModal(`جزئیات خرابی · ${fault.code}`, body);

      if (repairOrder && FMMS.api.capabilities.repairTimeline) {
        try {
          const events = await FMMS.api.getRepairTimeline(repairOrder.id);
          const host = document.getElementById("fault-detail-timeline");
          if (host) host.innerHTML = FMMS.ui.renderTimeline(events);
        } catch (_) {
          const host = document.getElementById("fault-detail-timeline");
          if (host) host.textContent = "بارگذاری تاریخچه ممکن نشد.";
        }
      }
    } catch (err) {
      FMMS.ui.openDetailModal("جزئیات خرابی", `<div class="text-danger">${FMMS.ui.escapeHtml(err.message)}</div>`);
      FMMS.ui.toast(err.message, "error");
    }
  }

  function updateFilterHint() {
    const hint = document.getElementById("faults-filter-hint");
    if (!hint) return;
    const caps = FMMS.api.capabilities;
    if (currentFilter === "closed" && !caps.faultListFilters.status) {
      hint.textContent =
        "فیلتر status در YAML وجود ندارد؛ خرابی‌های بسته از vehicle_id و فیلتر سمت کلاینت استخراج می‌شوند.";
    } else if (currentFilter === "all" && !caps.faultListFilters.status) {
      hint.textContent = "نمای «همه» با تجمیع vehicle_id و open_by_severity پیاده شده است.";
    } else if (currentFilter === "vehicle") {
      hint.textContent = "منبع: GET /faults/?vehicle_id=…";
    } else {
      hint.textContent = "منبع: GET /faults/?open_by_severity=…";
    }
  }

  async function loadFaultList() {
    const tbody = document.getElementById("faults-tbody");
    tbody.innerHTML = `<tr><td colspan="7">در حال بارگذاری…</td></tr>`;
    try {
      await ensureVehicles();
      const res = await FMMS.api.listFaultsFiltered(
        currentFilter,
        currentFilter === "vehicle" ? filterVehicleId : undefined
      );
      const sorted = res.results.slice().sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      tbody.innerHTML = sorted.length
        ? sorted.map(faultRow).join("")
        : `<tr><td colspan="7"><div class="empty-state"><div class="title">خرابی‌ای یافت نشد</div></div></td></tr>`;
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7">${FMMS.ui.escapeHtml(err.message)}</td></tr>`;
      FMMS.ui.toast(err.message, "error");
    }
  }

  function wireToolbar() {
    if (toolbarWired) return;
    const vehicleWrap = document.getElementById("faults-vehicle-filter-wrap");
    const vehicleSelect = document.getElementById("faults-vehicle-filter");

    document.querySelectorAll(".faults-filter-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".faults-filter-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        currentFilter = btn.dataset.faultFilter;
        vehicleWrap.style.display = currentFilter === "vehicle" ? "flex" : "none";
        updateFilterHint();
        loadFaultList();
      });
    });

    vehicleSelect.addEventListener("change", () => {
      filterVehicleId = vehicleSelect.value;
      if (currentFilter === "vehicle") loadFaultList();
    });

    toolbarWired = true;
  }

  async function populateVehicleFilter() {
    await ensureVehicles();
    const select = document.getElementById("faults-vehicle-filter");
    const vehicles = Object.values(vehiclesById);
    select.innerHTML = vehicles
      .map((v) => `<option value="${v.id}">${FMMS.ui.escapeHtml(v.plate_number)} — ${FMMS.ui.vehicleLabel(v)}</option>`)
      .join("");
    if (vehicles.length) filterVehicleId = vehicles[0].id;
  }

  async function render() {
    wireToolbar();
    await populateVehicleFilter();
    updateFilterHint();
    await loadFaultList();

    const tbody = document.getElementById("faults-tbody");
    if (!detailWired) {
      tbody.addEventListener("click", (e) => {
        const btn = e.target.closest('[data-action="detail"]');
        if (!btn) return;
        const row = btn.closest("tr[data-fault-id]");
        if (row) showFaultDetail(row.dataset.faultId);
      });
      detailWired = true;
    }
  }

  async function decide(faultId, vehicleId, usable, btnGroup) {
    btnGroup.querySelectorAll("button").forEach((b) => (b.disabled = true));
    try {
      if (usable) {
        await FMMS.api.closeFault(faultId);
        FMMS.ui.toast("خرابی بسته شد؛ خودرو قابل استفاده اعلام شد.");
      } else {
        const updated = await FMMS.api.deactivateVehicleForFault(vehicleId);
        if (updated?.id) {
          vehiclesById[updated.id] = updated;
        } else {
          const fresh = await FMMS.api.getVehicle(vehicleId);
          vehiclesById[vehicleId] = fresh;
        }
        FMMS.ui.toast("وضعیت خودرو به «غیرفعال» تغییر کرد.");
      }
      await renderDistribution();
    } catch (err) {
      FMMS.ui.toast(err.message, "error");
      btnGroup.querySelectorAll("button").forEach((b) => (b.disabled = false));
    }
  }

  async function renderDistribution() {
    const tbody = document.getElementById("distribution-tbody");
    tbody.innerHTML = `<tr><td colspan="5">در حال بارگذاری…</td></tr>`;
    try {
      await ensureVehicles();
      const faults = await loadDistributionFaults();

      tbody.innerHTML = faults.length
        ? faults
            .map((f) => {
              const v = vehiclesById[f.vehicle_id];
              return `<tr data-fault-id="${f.id}">
              <td>${FMMS.ui.vehicleLabel(v)}</td>
              <td>${FMMS.ui.escapeHtml(f.description)}</td>
              <td>${FMMS.ui.badge(f.severity)}</td>
              <td>${v ? FMMS.ui.badge(v.status) : "—"}</td>
              <td>${distributionActionsCell(f, v)}</td>
            </tr>`;
            })
            .join("")
        : `<tr><td colspan="5"><div class="empty-state"><div class="title">خرابی بازی برای تصمیم‌گیری وجود ندارد</div><div>پس از شکست یک بازرسی در «شبیه‌سازی راننده»، مورد جدید این‌جا نمایش داده می‌شود.</div></div></td></tr>`;

      tbody.querySelectorAll("tr[data-fault-id]").forEach((tr) => {
        const fault = faults.find((f) => f.id === tr.dataset.faultId);
        const v = vehiclesById[fault.vehicle_id];
        if (getDistributionDecision(fault, v).reviewed) return;
        if (!DISTRIBUTION_ACTIONABLE.has(fault.status)) return;
        const group = tr.querySelector(`#dist-actions-${fault.id}`);
        if (!group) return;
        group.querySelector('[data-action="usable"]')?.addEventListener("click", () => decide(fault.id, fault.vehicle_id, true, group));
        group.querySelector('[data-action="unusable"]')?.addEventListener("click", () => decide(fault.id, fault.vehicle_id, false, group));
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5">${FMMS.ui.escapeHtml(err.message)}</td></tr>`;
      FMMS.ui.toast(err.message, "error");
    }
  }

  FMMS.pages.faults = { render, renderDistribution };
})(window.FMMS);
