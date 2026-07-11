/** Dashboard page module. */
window.FMMS = window.FMMS || {};

(function (FMMS) {
  FMMS.pages = FMMS.pages || {};

  const DASHBOARD_WORKFLOW_STEPS = [
    "خودرو",
    "بازرسی راننده",
    "ثبت خرابی",
    "تصمیم توزیع",
    "تایید ترابری",
    "تعمیرگاه و تعمیر",
    "یکپارچه‌سازی SAP",
  ];

  const KPI_ICONS = {
    vehicles: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8h11v8H3z"/><path d="M14 10h3l3 3v3h-6V10Z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/></svg>`,
    active: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="m8.5 12.5 10.5 10.5 16 7"/></svg>`,
    faults: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/></svg>`,
    repair: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76Z"/></svg>`,
    sap: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v6c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/><path d="M3 11v6c0 1.66 4.03 3 9 3s9-1.34 9-3v-6"/></svg>`,
  };

  function renderKpiCard(label, value, foot, iconKey, tone, valueClass) {
    return `<div class="kpi-card">
      <div class="kpi-card-head">
        <div class="kpi-card-label">${label}</div>
        <span class="kpi-card-icon tone-${tone}" aria-hidden="true">${KPI_ICONS[iconKey]}</span>
      </div>
      <div class="kpi-card-value${valueClass ? ` ${valueClass}` : ""}">${value}</div>
      <div class="kpi-card-foot">${foot}</div>
    </div>`;
  }

  function deriveDashboardWorkflowStep(metrics) {
    if (metrics.inProgressRepairs > 0) return 6;
    if (metrics.pendingApproval > 0) return 5;
    if (metrics.openFaults > 0) return 4;
    if (metrics.activeVehicles > 0) return 2;
    return 1;
  }

  function renderDashboardWorkflowTimeline(currentStep) {
    return DASHBOARD_WORKFLOW_STEPS.map((label, i) => {
      const n = i + 1;
      const cls = n < currentStep ? "done" : n === currentStep ? "current" : "";
      const dot = n < currentStep ? "✓" : String(n);
      return `<div class="dashboard-wf-step ${cls}">
        <span class="dashboard-wf-dot">${dot}</span>
        <span class="dashboard-wf-label">${label}</span>
      </div>`;
    }).join("");
  }

  function summarizeSapStatus(transactions) {
    if (!transactions.length) {
      return { value: "—", foot: "تراکنشی ثبت نشده", tone: "blue", text: true };
    }
    const failed = transactions.filter((t) => ["FAILED", "EXHAUSTED"].includes(t.status)).length;
    const retrying = transactions.filter((t) => t.status === "RETRYING").length;
    const pending = transactions.filter((t) => t.status === "PENDING").length;
    if (failed > 0) {
      return { value: String(failed), foot: "تراکنش ناموفق", tone: "red", text: false };
    }
    if (retrying > 0 || pending > 0) {
      return { value: String(retrying + pending), foot: "در انتظار / تلاش مجدد", tone: "amber", text: false };
    }
    return { value: "سالم", foot: "همه تراکنش‌ها موفق", tone: "green", text: true };
  }

  async function renderDashboard() {
    const statsEl = document.getElementById("dashboard-stats");
    const timelineEl = document.getElementById("dashboard-workflow-timeline");
    const workflowsEl = document.getElementById("dashboard-workflows");
    const faultsEl = document.getElementById("dashboard-recent-faults");
    const repairsEl = document.getElementById("dashboard-recent-repairs");
    if (!statsEl) return;
    statsEl.innerHTML = renderKpiCard("در حال بارگذاری…", "…", "", "vehicles", "neutral", false);

    try {
      const [vehiclesRaw, faultsRaw, repairOrdersRaw, sapRaw] = await Promise.all([
        FMMS.api.listAllVehicles(),
        FMMS.api.listFaultsFiltered("all"),
        FMMS.api.listAllRepairOrders(),
        FMMS.api.listSapTransactions(),
      ]);
      const vehicles = vehiclesRaw;
      const faults = faultsRaw;
      const repairOrders = FMMS.api.asPage(repairOrdersRaw);
      const sapTransactions = FMMS.api.asPage(sapRaw);

      const vehiclesById = Object.fromEntries(vehicles.results.map((v) => [v.id, v]));
      const faultsByVehicle = {};
      faults.results.forEach((f) => {
        if (!faultsByVehicle[f.vehicle_id] || f.status === "OPEN") {
          faultsByVehicle[f.vehicle_id] = f;
        }
      });

      const totalVehicles = vehicles.results.length;
      const activeVehicles = vehicles.results.filter((v) => v.status === "ACTIVE").length;
      const openFaults = faults.results.filter((f) => f.status !== "CLOSED").length;
      const inProgressRepairs = repairOrders.results.filter((r) =>
        ["IN_PROGRESS", "WORKSHOP_ASSIGNED", "ASSIGNED"].includes(r.status)
      ).length;
      const pendingApproval = repairOrders.results.filter((r) =>
        ["CREATED", "APPROVED"].includes(r.status)
      ).length;
      const sapSummary = summarizeSapStatus(sapTransactions.results);

      statsEl.innerHTML =
        renderKpiCard("تعداد خودروها", totalVehicles, "کل ناوگان ثبت‌شده", "vehicles", "neutral", false) +
        renderKpiCard("خودروهای فعال", activeVehicles, "آماده بهره‌برداری", "active", "green", false) +
        renderKpiCard("خرابی‌های باز", openFaults, "در انتظار تصمیم یا تعمیر", "faults", "red", false) +
        renderKpiCard("تعمیرات جاری", inProgressRepairs, "در تعمیرگاه", "repair", "amber", false) +
        renderKpiCard(
          "وضعیت SAP",
          sapSummary.value,
          sapSummary.foot,
          "sap",
          sapSummary.tone,
          sapSummary.text ? "is-text" : false
        );

      if (timelineEl) {
        const currentStep = deriveDashboardWorkflowStep({
          inProgressRepairs,
          pendingApproval,
          openFaults,
          activeVehicles,
        });
        timelineEl.innerHTML = renderDashboardWorkflowTimeline(currentStep);
      }

      const activeOrders = repairOrders.results
        .filter((r) => r.status !== "CANCELLED")
        .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
        .slice(0, 6);

      if (workflowsEl) {
        workflowsEl.innerHTML = activeOrders.length
            ? activeOrders
                .map((ro) => {
                  const v = vehiclesById[ro.vehicle_id];
                  const fault = faultsByVehicle[ro.vehicle_id] || faults.results.find((f) => f.id === ro.fault_id);
                  const eq = v?.sap_equipment_number ? `EQ${v.sap_equipment_number.replace(/\D/g, "").slice(-8)}` : "";
                  return `<div class="workflow-card">
                <div class="workflow-card-title">${FMMS.ui.vehicleLabel(v)}</div>
                <div class="workflow-card-eq mono">${eq || v?.sap_equipment_number || "—"}</div>
                <div class="workflow-card-meta">
                  <span><strong>مرحله فعلی:</strong> ${FMMS.workflow.workflowStageLabel(v, fault, ro)}</span>
                  <span><strong>وضعیت:</strong> ${FMMS.workflow.vehicleStatusSummary(v, ro)}</span>
                </div>
              </div>`;
                })
                .join("")
            : `<div class="empty-state"><div class="title">جریان کاری فعالی نیست</div><div>از منوی «راننده - بازرسی روزانه خودرو» یک بازرسی شروع کنید.</div></div>`;
      }

      const recentFaults = faults.results
        .slice()
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .slice(0, 5);
      if (faultsEl) {
        faultsEl.innerHTML = recentFaults.length
            ? recentFaults
                .map((f) => {
                  const v = vehiclesById[f.vehicle_id];
                  return `<div class="checklist-row">
                <div>
                  <div class="item-name">${FMMS.ui.escapeHtml(f.description)}</div>
                  <div class="item-cat">${FMMS.ui.vehicleLabel(v)} · <span class="mono">${f.code}</span></div>
                </div>
                ${FMMS.ui.badge(f.status)}
              </div>`;
                })
                .join("")
            : `<div class="empty-state">
                <div class="empty-icon">
                <svg xmlns="http://www.w3.org/2000/svg"
                     width="56"
                     height="56"
                     viewBox="0 0 24 24"
                     fill="none"
                     stroke="currentColor"
                     stroke-width="1.6"
                     stroke-linecap="round"
                     stroke-linejoin="round">
                    <path d="M8 3h6l4 4v13a1 1 0 0 1-1 1H8a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/>
                    <path d="M14 3v4h4"/>
                    <path d="M9 11h6"/>
                    <path d="M9 15h4"/>
                </svg>
                </div>
                <div class="subtitle">
                    در حال حاضر موردی برای نمایش وجود ندارد.
                </div>
            </div>`;
      }

      const recentRepairs = repairOrders.results
        .slice()
        .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
        .slice(0, 5);
      if (repairsEl) {
        repairsEl.innerHTML = recentRepairs.length
            ? recentRepairs
                .map((ro) => {
                  const v = vehiclesById[ro.vehicle_id];
                  return `<div class="checklist-row">
                <div>
                  <div class="item-name mono">${FMMS.ui.escapeHtml(ro.id)}</div>
                  <div class="item-cat">${FMMS.ui.vehicleLabel(v)}</div>
                </div>
                ${FMMS.ui.badge(ro.status)}
              </div>`;
                })
                .join("")
            : `<div class="empty-state">
                <div class="empty-icon">
                <svg xmlns="http://www.w3.org/2000/svg"
                     width="56"
                     height="56"
                     viewBox="0 0 24 24"
                     fill="none"
                     stroke="currentColor"
                     stroke-width="1.6"
                     stroke-linecap="round"
                     stroke-linejoin="round">
                    <path d="M8 3h6l4 4v13a1 1 0 0 1-1 1H8a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/>
                    <path d="M14 3v4h4"/>
                    <path d="M9 11h6"/>
                    <path d="M9 15h4"/>
                </svg>
                </div>
                <div class="subtitle">
                    در حال حاضر موردی برای نمایش وجود ندارد.
                </div>
            </div>`;
      }
    } catch (err) {
      statsEl.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="title">خطا در بارگذاری داشبورد</div><div>${FMMS.ui.escapeHtml(err.message)}</div></div>`;
      FMMS.ui.toast(err.message, "error");
    }
  }

  FMMS.pages.dashboard = { render: renderDashboard };
})(window.FMMS);



document.addEventListener("DOMContentLoaded", () => {
  FMMS.pageBoot?.initPage("dashboard", () => FMMS.pages.dashboard?.render?.());
});
