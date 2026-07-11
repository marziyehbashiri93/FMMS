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

  function distributionActionsCell(fault, vehicle) {
    const detailBtn = `<button type="button" class="btn btn-fmms-outline btn-sm" data-action="dist-detail">مشاهده جزئیات</button>`;
    const state = getDistributionDecision(fault, vehicle);
    if (state.reviewed) {
      return detailBtn;
    }
    if (!DISTRIBUTION_ACTIONABLE.has(fault.status)) {
      return detailBtn;
    }
    const groupId = `dist-actions-${fault.id}`;
    return `<div class="d-flex flex-wrap gap-1" id="${groupId}">
      ${detailBtn}
      <button type="button" class="btn btn-fmms-success btn-sm" data-action="usable">خودرو قابل استفاده است</button>
      <button type="button" class="btn btn-fmms-danger btn-sm" data-action="unusable">خودرو غیرقابل استفاده است</button>
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
    if (caps.severityScope === "fault" || !items?.length) return "";
    const rows = (items || []).map(
      (item) => `<tr>
        <td class="distribution-item-component">${FMMS.ui.escapeHtml(item.component)}</td>
        <td class="distribution-item-desc">${FMMS.ui.escapeHtml(item.description)}</td>
        <td>${FMMS.ui.badge(item.severity)}</td>
        <td class="mono">${FMMS.ui.escapeHtml(item.inspection_item_id || "—")}</td>
      </tr>`
    );
    return (
      `<div class="modal-section distribution-modal-section"><div class="modal-section-title">آیتم‌های خرابی (بازرسی)</div>` +
      `<div class="distribution-fault-items-table">` +
      FMMS.ui.renderTable(["قطعه", "توضیح", "شدت", "آیتم بازرسی"], rows) +
      `</div></div>`
    );
  }

  function renderDistributionSummary(fault, vehicle, repairOrder) {
    const vehicleValue = vehicle ? FMMS.ui.vehicleLabel(vehicle) : `<span class="mono">${FMMS.ui.escapeHtml(fault.vehicle_id)}</span>`;
    const inspectionValue = fault.inspection_id
      ? `<span class="dm-summary-text">تکمیل‌شده</span>`
      : `<span class="dm-summary-muted">—</span>`;
    const repairValue = repairOrder
      ? FMMS.ui.badge(repairOrder.status)
      : `<span class="dm-summary-muted">ثبت نشده</span>`;
    const sapValue = fault.sap_notification_number
      ? FMMS.ui.badge("SUCCESS")
      : FMMS.ui.badge("PENDING");

    return `<div class="distribution-summary-card">
      <div class="distribution-summary-heading">خلاصه بازرسی</div>
      <div class="distribution-summary-grid">
        <div class="distribution-summary-item">
          <span class="dm-summary-label">خودرو</span>
          <span class="dm-summary-value">${vehicleValue}</span>
        </div>
        <div class="distribution-summary-item">
          <span class="dm-summary-label">بازرسی</span>
          <span class="dm-summary-value">${inspectionValue}</span>
        </div>
        <div class="distribution-summary-item">
          <span class="dm-summary-label">خرابی</span>
          <span class="dm-summary-value">${FMMS.ui.badge(fault.status)}</span>
        </div>
        <div class="distribution-summary-item">
          <span class="dm-summary-label">شدت</span>
          <span class="dm-summary-value">${FMMS.ui.badge(fault.severity)}</span>
        </div>
        <div class="distribution-summary-item">
          <span class="dm-summary-label">دستور تعمیر</span>
          <span class="dm-summary-value">${repairValue}</span>
        </div>
        <div class="distribution-summary-item">
          <span class="dm-summary-label">SAP</span>
          <span class="dm-summary-value">${sapValue}</span>
        </div>
      </div>
    </div>`;
  }

  function renderDistributionDecisionCard(reviewed, decisionState, faultStatus) {
    if (reviewed) {
      return `<div class="distribution-decision-sticky">
        <div class="distribution-decision-card distribution-decision-card--reviewed">
          <div class="distribution-decision-header">
            <h4 class="distribution-decision-title">تصمیم توزیع</h4>
            <p class="distribution-decision-sub">تصمیم برای این خودرو قبلاً ثبت شده است.</p>
          </div>
          <div class="distribution-reviewed-banner">
            <span class="distribution-reviewed-label">تصمیم ثبت‌شده</span>
            <span class="distribution-reviewed-value">${FMMS.ui.escapeHtml(decisionState.decision)}</span>
          </div>
        </div>
      </div>`;
    }
    if (!DISTRIBUTION_ACTIONABLE.has(faultStatus)) return "";
    return `<div class="distribution-decision-sticky">
      <div class="distribution-decision-card">
        <div class="distribution-decision-header">
          <h4 class="distribution-decision-title">تصمیم توزیع</h4>
          <p class="distribution-decision-sub">مشخص کنید آیا این خودرو می‌تواند به سرویس بازگردد.</p>
        </div>
        <div class="transport-detail-actions">
          <p class="distribution-decision-hint">پس از بررسی جزئیات خرابی و خودرو، یکی از گزینه‌های زیر را انتخاب کنید.</p>
          <div class="distribution-option-cards">
            <div class="distribution-option-card distribution-option-usable">
              <button type="button" class="btn btn-fmms-success btn-sm distribution-option-btn" id="distribution-detail-usable">
                <span class="distribution-option-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9L18 10l-2.7-3.6a1 1 0 0 0-.8-.4H9.5a1 1 0 0 0-.8.4L6 10l-2.5 1.1C2.7 11.3 2 12.1 2 13v3c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><circle cx="17" cy="17" r="2"/><path d="m9 12 2 2 4-4"/></svg>
                </span>
                <span class="distribution-option-text">
                  <span class="distribution-option-label">خودرو قابل استفاده است</span>
                  <span class="distribution-option-desc">خودرو برای بهره‌برداری ایمن است.</span>
                </span>
              </button>
            </div>
            <div class="distribution-option-card distribution-option-unusable">
              <button type="button" class="btn btn-fmms-danger btn-sm distribution-option-btn" id="distribution-detail-unusable">
                <span class="distribution-option-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>
                </span>
                <span class="distribution-option-text">
                  <span class="distribution-option-label">خودرو غیرقابل استفاده است</span>
                  <span class="distribution-option-desc">خودرو تا پایان تعمیر خارج از سرویس می‌ماند.</span>
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>`;
  }

  function wireDistributionOptionCards() {
    document.querySelectorAll(".distribution-option-btn").forEach((btn) => {
      btn.addEventListener(
        "click",
        () => {
          document.querySelectorAll(".distribution-option-card").forEach((card) => card.classList.remove("is-selected"));
          btn.closest(".distribution-option-card")?.classList.add("is-selected");
        },
        true
      );
    });
  }

  function hideDetailModal() {
    bootstrap.Modal.getInstance(document.getElementById("detail-modal"))?.hide();
  }

  async function showDistributionDetail(faultId) {
    FMMS.ui.openDetailModalLoading("بررسی تصمیم توزیع");
    try {
      await ensureVehicles();
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
      const decisionState = getDistributionDecision(fault, vehicle);
      const reviewer = FMMS.session.roleLabel(FMMS.session.getRole());

      const reporterValue = fault.created_by
        ? FMMS.ui.createdByLabel(fault.created_by)
        : fault.reported_by_id
          ? `<span class="mono">${FMMS.ui.escapeHtml(fault.reported_by_id)}</span>`
          : "—";

      const vehicleRows = [
        ["خودرو", vehicle ? FMMS.ui.vehicleLabel(vehicle) : `<span class="mono">${fault.vehicle_id}</span>`],
        ["پلاک", vehicle ? `<span class="mono">${FMMS.ui.escapeHtml(vehicle.plate_number)}</span>` : "—"],
        ["وضعیت خودرو", vehicle ? FMMS.ui.badge(vehicle.status) : "—"],
        ["شماره تجهیز SAP", vehicle?.sap_equipment_number ? `<span class="mono">${FMMS.ui.escapeHtml(vehicle.sap_equipment_number)}</span>` : "—"],
      ];

      const inspectionRows = [
        ["شناسه بازرسی", fault.inspection_id ? `<span class="mono">${fault.inspection_id}</span>` : "—"],
        ["زمان ثبت", FMMS.ui.formatDateTime(fault.reported_at || fault.created_at)],
        ["ثبت‌کننده", reporterValue],
      ];

      const faultRows = [
        ["شناسه خرابی", `<span class="mono">${FMMS.ui.escapeHtml(fault.id)}</span>`],
        ["کد خرابی", `<span class="mono">${FMMS.ui.escapeHtml(fault.code)}</span>`],
        ["توضیح خرابی", FMMS.ui.escapeHtml(fault.description)],
        ["وضعیت خرابی", FMMS.ui.badge(fault.status)],
        ["شدت", FMMS.ui.badge(fault.severity)],
      ];

      const sapRows = [
        ["اعلان SAP", fault.sap_notification_number ? `<span class="mono">${FMMS.ui.escapeHtml(fault.sap_notification_number)}</span>` : "—"],
        ["وضعیت یکپارچه‌سازی", fault.sap_notification_number ? FMMS.ui.badge("SUCCESS") : FMMS.ui.badge("PENDING")],
      ];

      const repairRows = repairOrder
        ? [
            ["شناسه دستور تعمیر", `<span class="mono">${FMMS.ui.escapeHtml(repairOrder.id)}</span>`],
            ["وضعیت دستور", FMMS.ui.badge(repairOrder.status)],
          ]
        : [["دستور تعمیر", `<span class="text-muted">هنوز ثبت نشده است.</span>`]];

      let reviewedSection = "";
      if (decisionState.reviewed) {
        reviewedSection = `<div class="modal-section distribution-modal-section"><div class="modal-section-title">تصمیم ثبت‌شده</div>${FMMS.ui.renderDl([
          ["وضعیت", "بررسی شد"],
          ["تصمیم", decisionState.decision],
          ["وضعیت خودرو", vehicle ? FMMS.ui.badge(vehicle.status) : "—"],
          ["ثبت‌کننده (نمای فعلی)", FMMS.ui.escapeHtml(reviewer)],
        ])}</div>`;
      }

      let body =
        `<div class="distribution-detail-modal">` +
        renderDistributionSummary(fault, vehicle, repairOrder) +
        `<div class="modal-section distribution-modal-section"><div class="modal-section-title">اطلاعات خودرو</div>${FMMS.ui.renderDl(vehicleRows)}</div>` +
        `<div class="modal-section distribution-modal-section"><div class="modal-section-title">اطلاعات بازرسی</div>${FMMS.ui.renderDl(inspectionRows)}</div>` +
        `<div class="modal-section distribution-modal-section"><div class="modal-section-title">اطلاعات خرابی</div>${FMMS.ui.renderDl(faultRows)}</div>` +
        `<div class="modal-section distribution-modal-section"><div class="modal-section-title">دستور تعمیر</div>${FMMS.ui.renderDl(repairRows)}</div>` +
        `<div class="modal-section distribution-modal-section"><div class="modal-section-title">اطلاعات SAP</div>${FMMS.ui.renderDl(sapRows)}</div>` +
        renderItemSeverityTable(fault.items) +
        reviewedSection +
        (repairOrder && FMMS.api.capabilities.repairTimeline
          ? `<div class="modal-section distribution-modal-section"><div class="modal-section-title">تاریخچه مراحل</div><div id="distribution-detail-timeline" class="distribution-timeline-host text-muted">در حال بارگذاری…</div></div>`
          : "") +
        renderDistributionDecisionCard(decisionState.reviewed, decisionState, fault.status) +
        `</div>`;

      const titlePlate = vehicle?.plate_number || fault.code;
      FMMS.ui.openDetailModal("بررسی تایید توزیع", body);

      const modalEl = document.getElementById("detail-modal");
      const subEl = document.getElementById("detail-modal-subtitle");
      const dismissBtn = document.getElementById("detail-modal-dismiss");
      if (subEl) {
        subEl.textContent = vehicle ? FMMS.ui.vehicleLabel(vehicle) : titlePlate;
        subEl.classList.remove("d-none");
      }
      if (dismissBtn) dismissBtn.textContent = "انصراف";
      modalEl?.classList.add("distribution-detail-mode");
      wireDistributionOptionCards();

      const bindDecision = (id, usable) => {
        document.getElementById(id)?.addEventListener("click", async (e) => {
          const btn = e.currentTarget;
          btn.disabled = true;
          document.getElementById("distribution-detail-usable")?.setAttribute("disabled", "disabled");
          document.getElementById("distribution-detail-unusable")?.setAttribute("disabled", "disabled");
          try {
            if (usable) {
              await FMMS.api.closeFault(fault.id);
              FMMS.ui.toast("خرابی بسته شد؛ خودرو قابل استفاده اعلام شد.");
            } else {
              const updated = await FMMS.api.deactivateVehicleForFault(fault.vehicle_id);
              if (updated?.id) {
                vehiclesById[updated.id] = updated;
              } else {
                const fresh = await FMMS.api.getVehicle(fault.vehicle_id);
                vehiclesById[fault.vehicle_id] = fresh;
              }
              FMMS.ui.toast("وضعیت خودرو به «غیرفعال» تغییر کرد.");
            }
            hideDetailModal();
            await renderDistribution();
          } catch (err) {
            FMMS.ui.toast(err.message, "error");
            btn.disabled = false;
            document.getElementById("distribution-detail-usable")?.removeAttribute("disabled");
            document.getElementById("distribution-detail-unusable")?.removeAttribute("disabled");
          }
        });
      };

      bindDecision("distribution-detail-usable", true);
      bindDecision("distribution-detail-unusable", false);

      if (repairOrder && FMMS.api.capabilities.repairTimeline) {
        try {
          const events = await FMMS.api.getRepairTimeline(repairOrder.id);
          const host = document.getElementById("distribution-detail-timeline");
          if (host) host.innerHTML = FMMS.ui.renderTimeline(events);
        } catch (_) {
          const host = document.getElementById("distribution-detail-timeline");
          if (host) host.textContent = "بارگذاری تاریخچه ممکن نشد.";
        }
      }
    } catch (err) {
      FMMS.ui.openDetailModal("بررسی تصمیم توزیع", `<div class="text-danger">${FMMS.ui.escapeHtml(err.message)}</div>`);
      FMMS.ui.toast(err.message, "error");
    }
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
        `<div class="modal-section"><div class="modal-section-title">اطلاعات خرابی</div>${FMMS.ui.renderDl(dlRows)}</div>` +
        FMMS.ui.renderFaultSeverityBlock(fault) +
        renderItemSeverityTable(fault.items) +
        (repairOrder && FMMS.api.capabilities.repairTimeline
          ? `<div class="modal-section"><div class="modal-section-title">تاریخچه مراحل</div><div id="fault-detail-timeline" class="text-muted">در حال بارگذاری…</div></div>`
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

        tr.querySelector('[data-action="dist-detail"]')?.addEventListener("click", () => showDistributionDetail(fault.id));

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


document.addEventListener("DOMContentLoaded", () => {
  const view = new URLSearchParams(location.search).get("view") || document.body.dataset.view || "faults";
  if (view === "distribution") {
    FMMS.pageBoot?.initPage("distribution", () => FMMS.pages.faults?.renderDistribution?.());
  } else {
    FMMS.pageBoot?.initPage("faults", () => FMMS.pages.faults?.render?.());
  }
});
