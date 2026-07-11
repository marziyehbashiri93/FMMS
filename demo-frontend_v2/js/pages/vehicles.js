/**
 * Page: خودروها (Vehicle management)
 */
window.FMMS = window.FMMS || {};
FMMS.pages = FMMS.pages || {};

(function (FMMS) {
  const PAGE_SIZE = 15;
  const COLSPAN = 7;

  let allVehicles = [];
  let filteredVehicles = [];
  let currentPage = 1;
  let detailWired = false;
  let paginationWired = false;

  const OPEN_REPAIR_STATUSES = new Set([
    "CREATED",
    "APPROVED",
    "WORKSHOP_ASSIGNED",
    "WAITING_WORKSHOP_CONFIRMATION",
    "WAITING_PARTS",
    "ASSIGNED",
    "IN_PROGRESS",
    "WAITING_DRIVER_CONFIRMATION",
  ]);

  function rowHtml(v) {
    const vehicleNumber = v.sap_equipment_number || v.id;
    return `<tr data-vehicle-id="${v.id}">
      <td class="mono">${FMMS.ui.escapeHtml(vehicleNumber)}</td>
      <td class="mono">${FMMS.ui.escapeHtml(v.plate_number)}</td>
      <td>${FMMS.ui.escapeHtml(v.make)} ${FMMS.ui.escapeHtml(v.model)}</td>
      <td>${FMMS.ui.escapeHtml(String(v.year || "—"))}</td>
      <td>${FMMS.ui.badge(v.status)}</td>
      <td class="mono">${FMMS.ui.escapeHtml(v.sap_equipment_number || "—")}</td>
      <td><button type="button" class="btn btn-fmms-outline btn-sm" data-action="detail">مشاهده جزئیات</button></td>
    </tr>`;
  }

  function workshopTypeLabel(type) {
    if (type === "INTERNAL") return "تعمیرگاه داخلی";
    if (type === "EXTERNAL") return "تعمیرگاه خارجی";
    return "—";
  }

  async function loadFaultsForVehicle(vehicleId) {
    return FMMS.api.asPage(await FMMS.api.listFaultsByVehicle(vehicleId)).results;
  }

  function renderFaultsHistorySection(faults) {
    if (!faults.length) {
      return `<h6 class="mt-4 mb-2">خرابی‌ها</h6><div class="text-muted">خرابی ثبت‌شده‌ای برای این خودرو یافت نشد.</div>`;
    }
    const sorted = faults.slice().sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    const rows = sorted.map(
      (f) => `<tr>
        <td class="mono small">${FMMS.ui.escapeHtml(f.code)}</td>
        <td>${FMMS.ui.escapeHtml(f.description)}</td>
        <td>${FMMS.ui.badge(f.severity)}</td>
        <td>${FMMS.ui.badge(f.status)}</td>
        <td>${FMMS.ui.formatDateTime(f.reported_at || f.created_at)}</td>
      </tr>`
    );
    return `<h6 class="mt-4 mb-2">خرابی‌های این خودرو</h6>${FMMS.ui.renderTable(
      ["کد", "شرح", "شدت", "وضعیت", "تاریخ ثبت"],
      rows
    )}`;
  }

  function summarizeVehicleContext(vehicle, faults, repairOrders) {
    const sortedFaults = faults.slice().sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    const lastFault = sortedFaults[0];
    const openFaults = sortedFaults.filter((f) => f.status !== "CLOSED");
    const closedFaults = sortedFaults.filter((f) => f.status === "CLOSED");
    const openRepairs = repairOrders.filter((ro) => OPEN_REPAIR_STATUSES.has(ro.status));
    const lastRepair = repairOrders.slice().sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))[0];

    return [
      ["آخرین خرابی", lastFault ? `${FMMS.ui.escapeHtml(lastFault.description)} — ${FMMS.ui.badge(lastFault.status)}` : "—"],
      ["خرابی‌های باز", openFaults.length ? `${openFaults.length} مورد` : "—"],
      ["خرابی‌های بسته", closedFaults.length ? `${closedFaults.length} مورد` : "—"],
      [
        "RepairOrder باز",
        openRepairs.length
          ? `<span class="mono">${FMMS.ui.escapeHtml(openRepairs[0].id)}</span> — ${FMMS.ui.badge(openRepairs[0].status)}`
          : "—",
      ],
      ["وضعیت آخرین تعمیر", lastRepair ? FMMS.ui.badge(lastRepair.status) : "—"],
    ];
  }

  function renderRepairOrdersSection(orders) {
    if (!orders.length) {
      return `<h6 class="mt-4 mb-2">دستورات تعمیر</h6><div class="text-muted">دستور تعمیری ثبت نشده است.</div>`;
    }
    const sorted = orders.slice().sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
    const summaryRows = sorted.map(
      (ro) => `<tr>
        <td class="mono small">${FMMS.ui.escapeHtml(ro.id)}</td>
        <td>${FMMS.ui.badge(ro.status)}</td>
        <td>${workshopTypeLabel(ro.workshop_type)}</td>
        <td class="mono small">${FMMS.ui.escapeHtml(ro.sap_order_number || "—")}</td>
        <td>${FMMS.ui.formatDateTime(ro.updated_at)}</td>
      </tr>`
    );
    return (
      `<h6 class="mt-4 mb-2">دستورات تعمیر</h6>` +
      FMMS.ui.renderTable(["شناسه", "وضعیت", "تعمیرگاه", "SAP PM", "بروزرسانی"], summaryRows)
    );
  }

  async function loadRepairOrdersForVehicle(vehicleId) {
    return FMMS.api.asPage(await FMMS.api.listRepairOrders(vehicleId)).results;
  }

  async function workshopStatusForVehicle(vehicle, repairOrders) {
    const open = repairOrders.filter((ro) => OPEN_REPAIR_STATUSES.has(ro.status));
    if (open.length) {
      return {
        label: "در فرآیند تعمیر",
        detail: `${FMMS.ui.badge(open[0].status)} <span class="mono small">${FMMS.ui.escapeHtml(open[0].id)}</span>`,
      };
    }
    if (vehicle.status === "UNDER_REPAIR") {
      return { label: "در فرآیند تعمیر", detail: FMMS.ui.badge("UNDER_REPAIR") };
    }
    return { label: "در تعمیرگاه نیست", detail: "—" };
  }

  async function showVehicleDetail(vehicleId) {
    FMMS.ui.openDetailModalLoading("جزئیات خودرو");
    try {
      const vehicle = await FMMS.api.getVehicle(vehicleId);
      const repairOrders = await loadRepairOrdersForVehicle(vehicleId);
      const faults = await loadFaultsForVehicle(vehicleId);
      const workshop = await workshopStatusForVehicle(vehicle, repairOrders);
      const rows = [
        ["شناسه خودرو", `<span class="mono">${FMMS.ui.escapeHtml(vehicle.id)}</span>`],
        ["پلاک", `<span class="mono">${FMMS.ui.escapeHtml(vehicle.plate_number)}</span>`],
        ["VIN", `<span class="mono">${FMMS.ui.escapeHtml(vehicle.vin)}</span>`],
        ["کد تجهیز SAP", `<span class="mono">${FMMS.ui.escapeHtml(vehicle.sap_equipment_number || "—")}</span>`],
        ["وضعیت خودرو", FMMS.ui.badge(vehicle.status)],
        ["سازنده / مدل", `${FMMS.ui.escapeHtml(vehicle.make)} ${FMMS.ui.escapeHtml(vehicle.model)} (${vehicle.year || "—"})`],
        ["وضعیت تعمیرگاهی", `<strong>${workshop.label}</strong><br>${workshop.detail}`],
        ...summarizeVehicleContext(vehicle, faults, repairOrders),
      ];
      const body =
        `<div class="modal-section"><div class="modal-section-title">اطلاعات اصلی</div>${FMMS.ui.renderDl(rows)}</div>` +
        `<div class="modal-section">${renderFaultsHistorySection(faults)}</div>` +
        `<div class="modal-section">${renderRepairOrdersSection(repairOrders)}</div>`;
      FMMS.ui.openDetailModal(`جزئیات خودرو · ${vehicle.plate_number}`, body);
    } catch (err) {
      FMMS.ui.openDetailModal("جزئیات خودرو", `<div class="text-danger">${FMMS.ui.escapeHtml(err.message)}</div>`);
      FMMS.ui.toast(err.message, "error");
    }
  }

  function getFilteredVehicles() {
    const q = document.getElementById("vehicles-search").value.trim().toLowerCase();
    const status = document.getElementById("vehicles-status-filter").value;
    return allVehicles.filter((v) => {
      const haystack = [v.plate_number, v.vin, v.model, v.make, v.sap_equipment_number, v.id]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      const matchesQ = !q || haystack.includes(q);
      const matchesStatus = !status || v.status === status;
      return matchesQ && matchesStatus;
    });
  }

  function renderSummary(totalFiltered) {
    const summaryEl = document.getElementById("vehicles-summary");
    if (!summaryEl) return;
    if (!allVehicles.length) {
      summaryEl.textContent = "";
      return;
    }
    const q = document.getElementById("vehicles-search").value.trim();
    const status = document.getElementById("vehicles-status-filter").value;
    const hasFilter = Boolean(q || status);
    if (!hasFilter) {
      summaryEl.textContent = `${allVehicles.length.toLocaleString("fa-IR")} خودرو ثبت‌شده`;
      return;
    }
    summaryEl.textContent = `${totalFiltered.toLocaleString("fa-IR")} نتیجه از ${allVehicles.length.toLocaleString("fa-IR")} خودرو`;
  }

  function renderPagination(totalItems) {
    const paginationEl = document.getElementById("vehicles-pagination");
    if (!paginationEl) return;

    const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
    if (currentPage > totalPages) currentPage = totalPages;

    if (totalItems <= PAGE_SIZE) {
      paginationEl.innerHTML = "";
      return;
    }

    const start = (currentPage - 1) * PAGE_SIZE + 1;
    const end = Math.min(currentPage * PAGE_SIZE, totalItems);

    paginationEl.innerHTML = `<div class="table-pagination-info">${start.toLocaleString("fa-IR")}–${end.toLocaleString("fa-IR")} از ${totalItems.toLocaleString("fa-IR")}</div>
      <div class="table-pagination-controls">
        <button type="button" class="btn btn-fmms-outline btn-sm" data-page-nav="prev"${currentPage <= 1 ? " disabled" : ""}>قبلی</button>
        <span class="table-pagination-current">صفحه ${currentPage.toLocaleString("fa-IR")} از ${totalPages.toLocaleString("fa-IR")}</span>
        <button type="button" class="btn btn-fmms-outline btn-sm" data-page-nav="next"${currentPage >= totalPages ? " disabled" : ""}>بعدی</button>
      </div>`;
  }

  function renderTableBody() {
    const tbody = document.getElementById("vehicles-tbody");
    if (!tbody) return;

    filteredVehicles = getFilteredVehicles();
    renderSummary(filteredVehicles.length);

    if (!allVehicles.length) {
      tbody.innerHTML = `<tr><td colspan="${COLSPAN}"><div class="empty-state"><div class="title">خودرویی ثبت نشده است</div><div class="subtitle">پس از ثبت یا همگام‌سازی SAP، خودروها اینجا نمایش داده می‌شوند.</div></div></td></tr>`;
      renderPagination(0);
      return;
    }

    if (!filteredVehicles.length) {
      tbody.innerHTML = `<tr><td colspan="${COLSPAN}"><div class="empty-state"><div class="title">نتیجه‌ای یافت نشد</div><div class="subtitle">فیلتر یا عبارت جستجو را تغییر دهید.</div></div></td></tr>`;
      renderPagination(0);
      return;
    }

    const totalPages = Math.max(1, Math.ceil(filteredVehicles.length / PAGE_SIZE));
    if (currentPage > totalPages) currentPage = totalPages;

    const start = (currentPage - 1) * PAGE_SIZE;
    const pageItems = filteredVehicles.slice(start, start + PAGE_SIZE);
    tbody.innerHTML = pageItems.map(rowHtml).join("");
    renderPagination(filteredVehicles.length);
  }

  function applyFilters(resetPage) {
    if (resetPage !== false) currentPage = 1;
    renderTableBody();
  }

  function wirePagination() {
    if (paginationWired) return;
    const paginationEl = document.getElementById("vehicles-pagination");
    if (!paginationEl) return;
    paginationEl.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-page-nav]");
      if (!btn || btn.disabled) return;
      const totalPages = Math.max(1, Math.ceil(filteredVehicles.length / PAGE_SIZE));
      if (btn.dataset.pageNav === "prev" && currentPage > 1) {
        currentPage -= 1;
        renderTableBody();
      } else if (btn.dataset.pageNav === "next" && currentPage < totalPages) {
        currentPage += 1;
        renderTableBody();
      }
    });
    paginationWired = true;
  }

  async function render() {
    const tbody = document.getElementById("vehicles-tbody");
    if (!tbody) return;

    currentPage = 1;
    tbody.innerHTML = `<tr><td colspan="${COLSPAN}">در حال بارگذاری…</td></tr>`;
    document.getElementById("vehicles-summary").textContent = "";
    document.getElementById("vehicles-pagination").innerHTML = "";

    try {
      const res = await FMMS.api.listAllVehicles();
      allVehicles = res.results.slice().sort((a, b) => {
        const aKey = a.plate_number || a.id;
        const bKey = b.plate_number || b.id;
        return aKey.localeCompare(bKey, "fa");
      });
      applyFilters(false);
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="${COLSPAN}"><div class="text-danger">${FMMS.ui.escapeHtml(err.message)}</div></td></tr>`;
      FMMS.ui.toast(err.message, "error");
      return;
    }

    if (!detailWired) {
      document.getElementById("vehicles-search").addEventListener("input", () => applyFilters());
      document.getElementById("vehicles-status-filter").addEventListener("change", () => applyFilters());
      tbody.addEventListener("click", (e) => {
        const btn = e.target.closest('[data-action="detail"]');
        if (!btn) return;
        const row = btn.closest("tr[data-vehicle-id]");
        if (row) showVehicleDetail(row.dataset.vehicleId);
      });
      detailWired = true;
    }

    wirePagination();
  }

  FMMS.pages.vehicles = { render };
})(window.FMMS);


document.addEventListener("DOMContentLoaded", () => {
  FMMS.pageBoot?.initPage("vehicles", () => FMMS.pages.vehicles?.render?.());
});
