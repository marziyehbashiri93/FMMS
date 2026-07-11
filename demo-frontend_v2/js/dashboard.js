/**
 * FMMS.shell — router + nav + workflow rail (shared chrome)
 * FMMS.pages.dashboard — the dashboard page itself
 * FMMS.workflow — stage labels for manager demo views
 */
window.FMMS = window.FMMS || {};

(function (FMMS) {
  const PAGE_META = {
    dashboard: { domPage: "dashboard", stage: null, group: null },
    vehicles: { domPage: "vehicles", stage: 1, group: null },
    inspection: { domPage: "inspection", stage: 2, group: "driver" },
    handover: { domPage: "handover", stage: 7, group: "driver" },
    faults: { domPage: "faults", stage: 3, group: null },
    distribution: { domPage: "distribution", stage: 4, group: "distribution" },
    "transport-repairs": { domPage: "transport", stage: 5, group: "transport", transportView: "repairs" },
    "transport-materials": { domPage: "transport", stage: 5, group: "transport", transportView: "materials" },
    "transport-invoices": { domPage: "transport", stage: 5, group: "transport", transportView: "invoices" },
    transport: { domPage: "transport", stage: 5, group: "transport", transportView: "repairs" },
    "workshop-orders": { domPage: "workshop", stage: 6, group: "workshop", workshopView: "orders" },
    "workshop-materials": { domPage: "workshop", stage: 6, group: "workshop", workshopView: "materials" },
    "workshop-history": { domPage: "workshop", stage: 6, group: "workshop", workshopView: "history" },
    workshop: { domPage: "workshop", stage: 6, group: "workshop", workshopView: "orders" },
    sap: { domPage: "sap", stage: null, group: "sap" },
  };

  const GROUP_PAGES = {
    driver: ["inspection", "handover"],
    distribution: ["distribution"],
    transport: ["transport-repairs", "transport-materials", "transport-invoices"],
    workshop: ["workshop-orders", "workshop-materials", "workshop-history"],
    sap: ["sap"],
  };

  const ROLE_PAGES = {
    MANAGER: null,
    DRIVER: ["dashboard", "inspection", "handover"],
    DISTRIBUTION: ["dashboard", "distribution"],
    TRANSPORT: ["dashboard", "transport-repairs", "transport-materials", "transport-invoices"],
    WORKSHOP: ["dashboard", "workshop-orders", "workshop-materials", "workshop-history"],
  };

  const WORKFLOW_STAGES = [
    "خودرو",
    "بازرسی راننده",
    "ثبت خرابی",
    "تصمیم توزیع",
    "تایید ترابری",
    "تعمیرگاه و قطعه",
    "تحویل و تایید راننده",
  ];

  let currentPage = "dashboard";
  let expandedGroups = new Set();

  function defaultExpandedGroupsForRole(role) {
    const map = {
      DRIVER: ["driver"],
      DISTRIBUTION: ["distribution"],
      TRANSPORT: ["transport"],
      WORKSHOP: ["workshop"],
      MANAGER: [],
    };
    return map[role] || [];
  }

  function pageMeta(pageId) {
    return PAGE_META[pageId] || PAGE_META.dashboard;
  }

  function normalizePageId(pageId) {
    if (PAGE_META[pageId]) return pageId;
    if (pageId === "transport") return "transport-repairs";
    if (pageId === "workshop") return "workshop-orders";
    return "dashboard";
  }

  function renderWorkflowRail(pageId) {
    const stageIndex = pageMeta(pageId).stage;
    const rail = document.getElementById("workflow-rail");
    if (!rail) return;
    if (stageIndex == null) {
      rail.innerHTML = `<span class="wf-step current"><span class="wf-num">•</span>نمای کلی جریان نگهداری و تعمیرات</span>`;
      return;
    }
    rail.innerHTML = WORKFLOW_STAGES.map((label, i) => {
      const n = i + 1;
      const cls = n < stageIndex ? "done" : n === stageIndex ? "current" : "";
      const sep = i > 0 ? `<span class="wf-sep"></span>` : "";
      return `${sep}<span class="wf-step ${cls}"><span class="wf-num">${n < stageIndex ? "✓" : n}</span>${label}</span>`;
    }).join("");
  }

  function applyTransportView(view) {
    document.querySelectorAll("[data-transport-view]").forEach((el) => {
      el.style.display = el.dataset.transportView === view ? "block" : "none";
    });
  }

  function applyWorkshopView(view) {
    document.querySelectorAll("[data-workshop-view]").forEach((el) => {
      el.style.display = el.dataset.workshopView === view ? "block" : "none";
    });
  }

  function setGroupExpanded(groupId, expanded) {
    const group = document.querySelector(`.nav-group[data-group="${groupId}"]`);
    if (!group) return;
    group.classList.toggle("expanded", expanded);
    const toggle = group.querySelector(".nav-group-toggle");
    if (toggle) toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
    if (expanded) expandedGroups.add(groupId);
    else expandedGroups.delete(groupId);
  }

  function expandGroupForPage(pageId) {
    const group = pageMeta(pageId).group;
    if (group) setGroupExpanded(group, true);
  }

  function updateNavActiveState(pageId) {
    document.querySelectorAll(".sidebar-nav .nav-link, .sidebar-nav .nav-sublink").forEach((link) => {
      link.classList.toggle("active", link.dataset.page === pageId);
    });
    document.querySelectorAll(".nav-group").forEach((group) => {
      const groupId = group.dataset.group;
      const pages = GROUP_PAGES[groupId] || [];
      group.classList.toggle("has-active", pages.includes(pageId));
    });
  }

  function isPageAllowedForRole(pageId, role) {
    const allowed = ROLE_PAGES[role];
    if (!allowed) return true;
    return allowed.includes(pageId);
  }

  function isGroupVisibleForRole(groupId, role) {
    const allowed = ROLE_PAGES[role];
    if (!allowed) return true;
    const pages = GROUP_PAGES[groupId] || [];
    return pages.some((pageId) => allowed.includes(pageId));
  }

  function applyRoleVisibility() {
    const role = FMMS.session.getRole();
    const dashboardLink = document.querySelector('.sidebar-nav .nav-link[data-page="dashboard"]');
    if (dashboardLink) {
      dashboardLink.style.display = isPageAllowedForRole("dashboard", role) ? "" : "none";
    }
    document.querySelectorAll(".nav-group").forEach((group) => {
      group.style.display = isGroupVisibleForRole(group.dataset.group, role) ? "" : "none";
    });
    document.querySelectorAll(".nav-group").forEach((group) => setGroupExpanded(group.dataset.group, false));
    defaultExpandedGroupsForRole(role).forEach((groupId) => setGroupExpanded(groupId, true));
    expandGroupForPage(currentPage);
  }

  function navigate(pageId) {
    pageId = normalizePageId(pageId);
    if (!isPageAllowedForRole(pageId, FMMS.session.getRole())) {
      pageId = "dashboard";
    }
    const meta = pageMeta(pageId);
    currentPage = pageId;
    location.hash = pageId;

    document.querySelectorAll(".page").forEach((el) => (el.style.display = "none"));
    const pageEl = document.getElementById("page-" + meta.domPage);
    if (pageEl) pageEl.style.display = "block";

    if (meta.domPage === "transport" && meta.transportView) {
      applyTransportView(meta.transportView);
    }
    if (meta.domPage === "workshop" && meta.workshopView) {
      applyWorkshopView(meta.workshopView);
    }

    updateNavActiveState(pageId);
    expandGroupForPage(pageId);
    renderWorkflowRail(pageId);

    const loaders = {
      dashboard: FMMS.pages.dashboard.render,
      vehicles: FMMS.pages.vehicles?.render,
      inspection: FMMS.pages.inspection?.render,
      handover: FMMS.pages.handover?.render,
      faults: FMMS.pages.faults?.render,
      distribution: FMMS.pages.faults?.renderDistribution,
      "transport-repairs": () => FMMS.pages.repair?.renderTransport("repairs"),
      "transport-materials": () => FMMS.pages.repair?.renderTransport("materials"),
      "transport-invoices": () => FMMS.pages.repair?.renderTransport("invoices"),
      transport: () => FMMS.pages.repair?.renderTransport("repairs"),
      "workshop-orders": () => FMMS.pages.repair?.renderWorkshop("orders"),
      "workshop-materials": () => FMMS.pages.repair?.renderWorkshop("materials"),
      "workshop-history": () => FMMS.pages.repair?.renderWorkshop("history"),
      workshop: () => FMMS.pages.repair?.renderWorkshop("orders"),
      sap: FMMS.pages.sap?.render,
    };
    const fn = loaders[pageId];
    if (typeof fn === "function") {
      Promise.resolve(fn()).catch((err) => {
        console.error(`[FMMS] page render failed (${pageId}):`, err);
        FMMS.ui?.toast?.(err.message || "خطا در بارگذاری صفحه", "error");
      });
    }
  }

  function wireSidebar() {
    document.querySelectorAll(".sidebar-nav .nav-link, .sidebar-nav .nav-sublink").forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        navigate(link.dataset.page);
      });
    });

    document.querySelectorAll(".nav-group-toggle").forEach((toggle) => {
      toggle.addEventListener("click", () => {
        const group = toggle.closest(".nav-group");
        const groupId = group?.dataset.group;
        if (!groupId) return;
        const isExpanded = group.classList.contains("expanded");
        setGroupExpanded(groupId, !isExpanded);
      });
    });
  }

  let shellInitialized = false;

  function init() {
    if (shellInitialized) {
      applyRoleVisibility();
      const pageId = normalizePageId((location.hash || "").replace("#", "") || "dashboard");
      navigate(pageId);
      return;
    }
    shellInitialized = true;
    wireSidebar();
    window.addEventListener("hashchange", () => {
      const pageId = normalizePageId((location.hash || "").replace("#", "") || "dashboard");
      if (pageId !== currentPage) navigate(pageId);
    });
    applyRoleVisibility();
    defaultExpandedGroupsForRole(FMMS.session.getRole()).forEach((groupId) => setGroupExpanded(groupId, true));
    expandedGroups.forEach((groupId) => setGroupExpanded(groupId, true));
    const initial = normalizePageId((location.hash || "").replace("#", "") || "dashboard");
    navigate(initial);
  }

  FMMS.shell = { init, navigate, applyRoleVisibility, getCurrentPage: () => currentPage };

  /** Derive human-readable workflow stage for dashboard cards. */
  function workflowStageLabel(vehicle, fault, repairOrder) {
    if (repairOrder) {
      if (repairOrder.status === "CREATED") return "انتظار تایید ترابری";
      if (repairOrder.status === "APPROVED") return "انتخاب تعمیرگاه";
      if (repairOrder.status === "WORKSHOP_ASSIGNED") return "پذیرش تعمیرگاه";
      if (repairOrder.status === "WAITING_WORKSHOP_CONFIRMATION" || repairOrder.status === "ASSIGNED") {
        return "آماده شروع تعمیر";
      }
      if (repairOrder.status === "IN_PROGRESS" || repairOrder.status === "WAITING_PARTS") {
        return "در حال تعمیر";
      }
      if (repairOrder.status === "WAITING_DRIVER_CONFIRMATION") return "منتظر تایید راننده";
      if (repairOrder.status === "ACCEPTED_BY_DRIVER") return "تحویل تایید شد";
      if (repairOrder.status === "REJECTED_BY_DRIVER") return "رد راننده";
      if (repairOrder.status === "CANCELLED") return "تعمیر لغو شد";
      if (repairOrder.status === "COMPLETED") return "تعمیر تکمیل‌شده";
    }
    if (fault && fault.status === "OPEN") return "انتظار تصمیم توزیع";
    if (vehicle?.status === "INACTIVE") return "خودرو غیرفعال";
    if (vehicle?.status === "WAITING_DRIVER_CONFIRMATION") return "منتظر تایید راننده";
    if (vehicle?.status === "UNDER_REPAIR") return "در حال تعمیر";
    return "در جریان";
  }

  function vehicleStatusSummary(vehicle, repairOrder) {
    if (vehicle?.status === "WAITING_DRIVER_CONFIRMATION") return "منتظر تایید راننده";
    if (repairOrder?.status === "IN_PROGRESS" || vehicle?.status === "UNDER_REPAIR") return "در حال تعمیر";
    if (vehicle?.status === "ACTIVE") return "فعال";
    if (vehicle?.status === "INACTIVE") return "غیرفعال";
    if (vehicle?.status === "OUT_OF_SERVICE") return "خارج از سرویس";
    return FMMS.ui.badge(vehicle?.status || "—");
  }

  FMMS.workflow = { workflowStageLabel, vehicleStatusSummary };

  FMMS.pages = FMMS.pages || {};

  async function renderDashboard() {
    const statsEl = document.getElementById("dashboard-stats");
    const overviewEl = document.getElementById("dashboard-workflow-overview");
    const workflowsEl = document.getElementById("dashboard-workflows");
    const faultsEl = document.getElementById("dashboard-recent-faults");
    const repairsEl = document.getElementById("dashboard-recent-repairs");
    const statusEl = document.getElementById("dashboard-status-changes");
    if (!statsEl) return;
    statsEl.innerHTML = `<div class="stat-card"><div class="stat-label">در حال بارگذاری…</div></div>`;

    const WORKFLOW_OVERVIEW = [
      { label: "Inspection", fa: "بازرسی" },
      { label: "Fault", fa: "خرابی" },
      { label: "Distribution", fa: "توزیع" },
      { label: "Transport", fa: "ترابری" },
      { label: "Workshop", fa: "تعمیرگاه" },
      { label: "Parts", fa: "قطعه" },
      { label: "Handover", fa: "تحویل" },
    ];
    if (overviewEl) {
      overviewEl.innerHTML = WORKFLOW_OVERVIEW.map(
        (s, i) =>
          `${i > 0 ? '<span class="workflow-overview-arrow">↓</span>' : ""}<span class="workflow-overview-step"><span class="workflow-overview-en">${s.label}</span><span class="workflow-overview-fa">${s.fa}</span></span>`
      ).join("");
    }

    try {
      const [vehiclesRaw, faultsRaw, repairOrdersRaw] = await Promise.all([
        FMMS.api.listAllVehicles(),
        FMMS.api.listFaultsFiltered("all"),
        FMMS.api.listAllRepairOrders(),
      ]);
      const vehicles = vehiclesRaw;
      const faults = faultsRaw;
      const repairOrders = FMMS.api.asPage(repairOrdersRaw);

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

      statsEl.innerHTML = `
        <div class="stat-card">
          <div class="stat-label">کل خودروها</div>
          <div class="stat-value">${totalVehicles}</div>
          <div class="stat-foot">کل ناوگان ثبت‌شده</div>
        </div>
        <div class="stat-card accent-green">
          <div class="stat-label">خودروهای فعال</div>
          <div class="stat-value">${activeVehicles}</div>
          <div class="stat-foot">آماده بهره‌برداری</div>
        </div>
        <div class="stat-card accent-red">
          <div class="stat-label">خرابی‌های باز</div>
          <div class="stat-value">${openFaults}</div>
          <div class="stat-foot">در انتظار تصمیم یا تعمیر</div>
        </div>
        <div class="stat-card accent-amber">
          <div class="stat-label">تعمیرات جاری</div>
          <div class="stat-value">${inProgressRepairs}</div>
          <div class="stat-foot">در تعمیرگاه</div>
        </div>
        <div class="stat-card accent-blue">
          <div class="stat-label">انتظار تایید</div>
          <div class="stat-value">${pendingApproval}</div>
          <div class="stat-foot">ترابری / تعمیرگاه</div>
        </div>
      `;

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
            : `<div class="empty-state"><div class="title">جریان کاری فعالی نیست</div><div>از منوی «راننده → بازرسی روزانه خودرو» یک بازرسی شروع کنید.</div></div>`;
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
            : `<div class="empty-state"><div class="title">خرابی‌ای ثبت نشده</div></div>`;
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
            : `<div class="empty-state"><div class="title">تعمیری ثبت نشده</div></div>`;
      }

      const statusChanges = vehicles.results
        .slice()
        .sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at))
        .slice(0, 5);
      if (statusEl) {
        statusEl.innerHTML = statusChanges.length
            ? statusChanges
                .map(
                  (v) => `<div class="checklist-row">
                <div>
                  <div class="item-name">${FMMS.ui.vehicleLabel(v)}</div>
                  <div class="item-cat">${FMMS.ui.formatDateTime(v.updated_at || v.created_at)}</div>
                </div>
                ${FMMS.ui.badge(v.status)}
              </div>`
                )
                .join("")
            : `<div class="empty-state"><div class="title">تغییری ثبت نشده</div></div>`;
      }
    } catch (err) {
      statsEl.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="title">خطا در بارگذاری داشبورد</div><div>${FMMS.ui.escapeHtml(err.message)}</div></div>`;
      FMMS.ui.toast(err.message, "error");
    }
  }

  FMMS.pages.dashboard = { render: renderDashboard };
})(window.FMMS);
