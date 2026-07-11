/**
 * FMMS.shell — router + page chrome + nav
 * FMMS.pages.dashboard — the dashboard page itself
 * FMMS.workflow — stage labels for dashboard cards
 */
window.FMMS = window.FMMS || {};

(function (FMMS) {
  const PAGE_META = {
    dashboard: { domPage: "dashboard", group: null },
    vehicles: { domPage: "vehicles", group: null },
    inspection: { domPage: "inspection", group: "driver" },
    handover: { domPage: "handover", group: "driver" },
    faults: { domPage: "faults", group: null },
    distribution: { domPage: "distribution", group: "distribution" },
    "transport-repairs": { domPage: "transport", group: "transport", transportView: "repairs" },
    "transport-handover": { domPage: "transport-handover", group: "transport" },
    "transport-materials": { domPage: "transport", group: "transport", transportView: "materials" },
    "transport-invoices": { domPage: "transport", group: "transport", transportView: "invoices" },
    transport: { domPage: "transport", group: "transport", transportView: "repairs" },
    "workshop-orders": { domPage: "workshop", group: "workshop", workshopView: "orders" },
    "workshop-materials": { domPage: "workshop", group: "workshop", workshopView: "materials" },
    "workshop-history": { domPage: "workshop", group: "workshop", workshopView: "history" },
    workshop: { domPage: "workshop", group: "workshop", workshopView: "orders" },
    sap: { domPage: "sap", group: "sap" },
  };

  const PAGE_CHROME = {
    dashboard: {
      title: "داشبورد کنترل ناوگان",
      breadcrumb: ["داشبورد"],
    },
    vehicles: { title: "خودروها", breadcrumb: ["داشبورد", "خودروها"] },
    inspection: { title: "بازرسی روزانه خودرو", breadcrumb: ["داشبورد", "راننده", "بازرسی روزانه خودرو"] },
    handover: { title: "تایید تحویل خودرو", breadcrumb: ["داشبورد", "راننده", "تایید تحویل خودرو"] },
    faults: { title: "خرابی‌ها", breadcrumb: ["داشبورد", "خرابی‌ها"] },
    distribution: {
      title: "درخواست‌های تعمیر",
      breadcrumb: ["داشبورد", "توزیع", "درخواست‌های تعمیر"],
    },
    "transport-repairs": {
      title: "تایید درخواست تعمیر",
      breadcrumb: ["داشبورد", "ترابری", "تایید درخواست تعمیر"],
      wizard: ["بررسی درخواست", "تصمیم", "تخصیص"],
      wizardStep: 1,
    },
    "transport-handover": {
      title: "تایید تحویل خودرو",
      breadcrumb: ["داشبورد", "ترابری", "تایید تحویل خودرو"],
      wizard: ["تایید راننده", "بررسی ترابری", "بازگشت به ناوگان"],
      wizardStep: 2,
    },
    "transport-materials": {
      title: "درخواست‌های قطعه",
      breadcrumb: ["داشبورد", "ترابری", "درخواست‌های قطعه"],
    },
    "transport-invoices": {
      title: "فاکتورهای خارجی",
      breadcrumb: ["داشبورد", "ترابری", "فاکتورهای خارجی"],
    },
    "workshop-orders": {
      title: "دستورات تعمیر",
      breadcrumb: ["داشبورد", "تعمیرات", "دستورات تعمیر"],
      wizard: ["تایید تعمیرگاه", "شروع تعمیر", "قطعات", "پایان تعمیر"],
      wizardStep: 1,
    },
    "workshop-materials": {
      title: "درخواست قطعه",
      breadcrumb: ["داشبورد", "تعمیرات", "درخواست قطعه"],
    },
    "workshop-history": {
      title: "تاریخچه تعمیرات",
      breadcrumb: ["داشبورد", "تعمیرات", "تاریخچه تعمیرات"],
    },
    sap: {
      title: "وضعیت یکپارچه‌سازی SAP",
      breadcrumb: ["داشبورد", "SAP", "وضعیت یکپارچه‌سازی"],
    },
  };

  const BC_HOME_ICON =
    '<svg class="bc-home-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5 12 4l9 6.5V19a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-8.5Z"/></svg>';

  const GROUP_PAGES = {
    driver: ["inspection", "handover"],
    distribution: ["distribution"],
    transport: ["transport-repairs", "transport-handover", "transport-materials", "transport-invoices"],
    workshop: ["workshop-orders", "workshop-materials", "workshop-history"],
    sap: ["sap"],
  };

  const ROLE_PAGES = {
    MANAGER: null,
    DRIVER: ["dashboard", "inspection", "handover"],
    DISTRIBUTION: ["dashboard", "distribution"],
    TRANSPORT: ["dashboard", "transport-repairs", "transport-handover", "transport-materials", "transport-invoices"],
    WORKSHOP: ["dashboard", "workshop-orders", "workshop-materials", "workshop-history"],
  };

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

  function renderLocalWizardHtml(steps, currentStep) {
    return `<div class="page-wizard-inner">${steps
      .map((label, i) => {
        const n = i + 1;
        const cls = n < currentStep ? "done" : n === currentStep ? "current" : "";
        const dot = n < currentStep ? "✓" : String(n);
        return `<div class="page-wizard-step ${cls}"><span class="page-wizard-dot">${dot}</span><span class="page-wizard-label">${label}</span></div>`;
      })
      .join("")}</div>`;
  }

  function renderBreadcrumbHtml(parts) {
    return parts
      .map((part, i) => {
        const sep = i > 0 ? '<span class="bc-sep">/</span>' : "";
        const isLast = i === parts.length - 1;
        if (isLast) {
          const home = i === 0 ? BC_HOME_ICON : "";
          return `${sep}<span class="bc-current">${home}${part}</span>`;
        }
        if (i === 0) {
          return `${sep}<a href="#dashboard" data-bc-page="dashboard">${BC_HOME_ICON}${part}</a>`;
        }
        return `${sep}<span>${part}</span>`;
      })
      .join("");
  }

  function renderPageChrome(pageId) {
    const chrome = document.getElementById("app-page-chrome");
    if (!chrome) return;
    const cfg = PAGE_CHROME[pageId];
    if (!cfg) {
      chrome.style.display = "none";
      return;
    }
    chrome.style.display = "block";
    const titleEl = document.getElementById("page-chrome-title");
    if (titleEl) titleEl.textContent = cfg.title;
    const bcEl = document.getElementById("page-breadcrumb");
    if (bcEl) bcEl.innerHTML = renderBreadcrumbHtml(cfg.breadcrumb || []);
    const wizardEl = document.getElementById("page-chrome-wizard");
    if (wizardEl) {
      if (cfg.wizard?.length) {
        wizardEl.style.display = "block";
        wizardEl.innerHTML = renderLocalWizardHtml(cfg.wizard, cfg.wizardStep || 1);
      } else {
        wizardEl.style.display = "none";
        wizardEl.innerHTML = "";
      }
    }
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
    document.querySelectorAll(".sidebar-nav .nav-link, .sidebar-nav .nav-sublink").forEach((link) => {
      const pageId = link.dataset.page;
      if (!pageId) return;
      link.style.display = isPageAllowedForRole(pageId, role) ? "" : "none";
    });
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
    renderPageChrome(pageId);

    const loaders = {
      dashboard: FMMS.pages.dashboard.render,
      vehicles: FMMS.pages.vehicles?.render,
      inspection: FMMS.pages.inspection?.render,
      handover: FMMS.pages.handover?.render,
      "transport-handover": FMMS.pages.transportHandover?.render,
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

    document.getElementById("page-breadcrumb")?.addEventListener("click", (e) => {
      const link = e.target.closest("[data-bc-page]");
      if (!link) return;
      e.preventDefault();
      navigate(link.dataset.bcPage);
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

  function refreshWorkshopWizard(orders) {
    if (currentPage !== "workshop-orders") return;
    const cfg = PAGE_CHROME["workshop-orders"];
    if (!cfg?.wizard?.length) return;
    const wizardEl = document.getElementById("page-chrome-wizard");
    if (!wizardEl) return;
    wizardEl.style.display = "block";
    wizardEl.innerHTML = renderLocalWizardHtml(cfg.wizard, deriveWorkshopWizardStep(orders));
  }

  FMMS.shell = {
    init,
    navigate,
    applyRoleVisibility,
    getCurrentPage: () => currentPage,
    refreshWorkshopWizard,
  };

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

  FMMS.workflow = { workflowStageLabel, vehicleStatusSummary, deriveWorkshopWizardStep };

  function deriveWorkshopWizardStep(orders) {
    if (!orders?.length) return 1;
    const stepByStatus = {
      WORKSHOP_ASSIGNED: 1,
      WAITING_WORKSHOP_CONFIRMATION: 2,
      ASSIGNED: 2,
      IN_PROGRESS: 3,
      WAITING_PARTS: 3,
      WAITING_DRIVER_CONFIRMATION: 4,
      COMPLETED: 4,
      ACCEPTED_BY_DRIVER: 4,
      REJECTED_BY_DRIVER: 4,
      CANCELLED: 1,
    };
    return orders.reduce((max, order) => Math.max(max, stepByStatus[order.status] || 1), 1);
  }

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
