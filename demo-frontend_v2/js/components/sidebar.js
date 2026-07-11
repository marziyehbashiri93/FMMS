window.FMMS = window.FMMS || {};

(function (FMMS) {
  const SIDEBAR_HTML = "\n                <a class=\"nav-link\" href=\"dashboard.html\" data-page=\"dashboard\">\n                    <span class=\"nav-icon\" aria-hidden=\"true\">\n                        <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M3 10.5 12 4l9 6.5V19a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-8.5Z\"/></svg>\n                    </span>\n                    <span class=\"nav-label\">\u062f\u0627\u0634\u0628\u0648\u0631\u062f</span>\n                </a>\n\n                <a class=\"nav-link\" href=\"vehicles.html\" data-page=\"vehicles\">\n                    <span class=\"nav-icon\" aria-hidden=\"true\">\n                        <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M3 8h11v8H3z\"/><path d=\"M14 10h3l3 3v3h-6V10Z\"/><circle cx=\"7\" cy=\"18\" r=\"2\"/><circle cx=\"18\" cy=\"18\" r=\"2\"/></svg>\n                    </span>\n                    <span class=\"nav-label\">\u062e\u0648\u062f\u0631\u0648\u0647\u0627</span>\n                </a>\n\n                <div class=\"nav-group\" data-group=\"driver\">\n                    <button type=\"button\" class=\"nav-group-toggle\" aria-expanded=\"false\">\n                        <span class=\"nav-group-label\">\n                            <span class=\"nav-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"12\" cy=\"7\" r=\"3.5\"/><path d=\"M5 20v-1.2c0-2.8 3.1-4.3 7-4.3s7 1.5 7 4.3V20\"/><path d=\"M16 12h4l1.5 2.5H18\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">\u0631\u0627\u0646\u0646\u062f\u0647</span>\n                        </span>\n                        <span class=\"nav-chevron\" aria-hidden=\"true\">\n                            <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"m6 9 6 6 6-6\"/></svg>\n                        </span>\n                    </button>\n                    <div class=\"nav-group-items\">\n                        <a class=\"nav-sublink\" href=\"driver-inspections.html\" data-page=\"inspection\">\n                            <span class=\"nav-sublink-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2\"/><rect x=\"9\" y=\"3\" width=\"6\" height=\"4\" rx=\"1\"/><path d=\"M9 12h6M9 16h4\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">\u0628\u0627\u0632\u0631\u0633\u06cc \u0631\u0648\u0632\u0627\u0646\u0647 \u062e\u0648\u062f\u0631\u0648</span>\n                        </a>\n                        <a class=\"nav-sublink\" href=\"inspections.html?view=handover\" data-page=\"handover\">\n                            <span class=\"nav-sublink-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M15.5 7.5 18 10l-6 6-3-3 2.5-2.5\"/><path d=\"M6 18h12\"/><path d=\"M7 14l-2 2v2h2l2-2\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">\u062a\u0627\u06cc\u06cc\u062f \u062a\u062d\u0648\u06cc\u0644 \u062e\u0648\u062f\u0631\u0648</span>\n                        </a>\n                    </div>\n                </div>\n\n                <div class=\"nav-group\" data-group=\"distribution\">\n                    <button type=\"button\" class=\"nav-group-toggle\" aria-expanded=\"false\">\n                        <span class=\"nav-group-label\">\n                            <span class=\"nav-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 22s7-4.5 7-11a4 4 0 0 0-7-2 4 4 0 0 0-7 2c0 6.5 7 11 7 11Z\"/><path d=\"M12 8v4\"/><path d=\"M12 16h.01\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">\u062a\u0648\u0632\u06cc\u0639</span>\n                        </span>\n                        <span class=\"nav-chevron\" aria-hidden=\"true\">\n                            <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"m6 9 6 6 6-6\"/></svg>\n                        </span>\n                    </button>\n                    <div class=\"nav-group-items\">\n                        <a class=\"nav-sublink\" href=\"faults.html?view=distribution\" data-page=\"distribution\">\n                            <span class=\"nav-sublink-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 9v4\"/><path d=\"M12 17h.01\"/><path d=\"M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">\u062f\u0631\u062e\u0648\u0627\u0633\u062a\u200c\u0647\u0627\u06cc \u062a\u0639\u0645\u06cc\u0631</span>\n                        </a>\n                    </div>\n                </div>\n\n                <div class=\"nav-group\" data-group=\"transport\">\n                    <button type=\"button\" class=\"nav-group-toggle\" aria-expanded=\"false\">\n                        <span class=\"nav-group-label\">\n                            <span class=\"nav-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M3 8h11v8H3z\"/><path d=\"M14 10h3l3 3v3h-6V10Z\"/><circle cx=\"7\" cy=\"18\" r=\"2\"/><circle cx=\"18\" cy=\"18\" r=\"2\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">\u062a\u0631\u0627\u0628\u0631\u06cc</span>\n                        </span>\n                        <span class=\"nav-chevron\" aria-hidden=\"true\">\n                            <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"m6 9 6 6 6-6\"/></svg>\n                        </span>\n                    </button>\n                    <div class=\"nav-group-items\">\n                        <a class=\"nav-sublink\" href=\"materials.html?scope=transport\" data-page=\"transport-materials\">\n                            <span class=\"nav-sublink-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z\"/><path d=\"M3.3 7.7 12 12l8.7-4.3M12 22V12\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">\u062f\u0631\u062e\u0648\u0627\u0633\u062a\u200c\u0647\u0627\u06cc \u0642\u0637\u0639\u0647</span>\n                        </a>\n                        <a class=\"nav-sublink\" href=\"transport.html\" data-page=\"transport-repairs\">\n                            <span class=\"nav-sublink-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z\"/><path d=\"M14 2v6h6\"/><path d=\"M9 13h6M9 17h4\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">\u062f\u0631\u062e\u0648\u0627\u0633\u062a\u200c\u0647\u0627\u06cc \u062a\u0639\u0645\u06cc\u0631</span>\n                        </a>\n                        <a class=\"nav-sublink\" href=\"transport.html?view=final-approval\" data-page=\"transport-handover\">\n                            <span class=\"nav-sublink-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M15.5 7.5 18 10l-6 6-3-3 2.5-2.5\"/><path d=\"M6 18h12\"/><path d=\"M7 14l-2 2v2h2l2-2\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">\u062a\u0627\u06cc\u06cc\u062f \u0646\u0647\u0627\u06cc\u06cc \u062a\u0639\u0645\u06cc\u0631\u0627\u062a</span>\n                        </a>\n                        <a class=\"nav-sublink\" href=\"invoices.html\" data-page=\"transport-invoices\">\n                            <span class=\"nav-sublink-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z\"/><path d=\"M14 2v6h6\"/><path d=\"M8 13h8M8 17h5\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">\u0641\u0627\u06a9\u062a\u0648\u0631\u0647\u0627\u06cc \u062e\u0627\u0631\u062c\u06cc</span>\n                        </a>\n                    </div>\n                </div>\n\n                <div class=\"nav-group\" data-group=\"workshop\">\n                    <button type=\"button\" class=\"nav-group-toggle\" aria-expanded=\"false\">\n                        <span class=\"nav-group-label\">\n                            <span class=\"nav-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76Z\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">\u062a\u0639\u0645\u06cc\u0631\u0627\u062a</span>\n                        </span>\n                        <span class=\"nav-chevron\" aria-hidden=\"true\">\n                            <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"m6 9 6 6 6-6\"/></svg>\n                        </span>\n                    </button>\n                    <div class=\"nav-group-items\">\n                        <a class=\"nav-sublink\" href=\"repairs.html\" data-page=\"workshop-orders\">\n                            <span class=\"nav-sublink-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76Z\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">\u062f\u0633\u062a\u0648\u0631\u0627\u062a \u062a\u0639\u0645\u06cc\u0631</span>\n                        </a>\n                        <a class=\"nav-sublink\" href=\"materials.html?scope=workshop\" data-page=\"workshop-materials\">\n                            <span class=\"nav-sublink-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M16.5 9.4 7.55 4.24\"/><path d=\"M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l2.45-1.4\"/><path d=\"m10 12 10.5-6\"/><path d=\"M3.27 6.96 12 12.01l8.73-5.05M12 22.08V12\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u0642\u0637\u0639\u0647</span>\n                        </a>\n                        <a class=\"nav-sublink\" href=\"repairs.html?view=history\" data-page=\"workshop-history\">\n                            <span class=\"nav-sublink-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><circle cx=\"12\" cy=\"12\" r=\"9\"/><path d=\"M12 7v5l3 2\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">\u062a\u0627\u0631\u06cc\u062e\u0686\u0647 \u062a\u0639\u0645\u06cc\u0631\u0627\u062a</span>\n                        </a>\n                    </div>\n                </div>\n\n                <div class=\"nav-group\" data-group=\"sap\">\n                    <button type=\"button\" class=\"nav-group-toggle\" aria-expanded=\"false\">\n                        <span class=\"nav-group-label\">\n                            <span class=\"nav-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><ellipse cx=\"12\" cy=\"5\" rx=\"9\" ry=\"3\"/><path d=\"M3 5v6c0 1.66 4.03 3 9 3s9-1.34 9-3V5\"/><path d=\"M3 11v6c0 1.66 4.03 3 9 3s9-1.34 9-3v-6\"/><path d=\"M7 19v2M12 19v2M17 19v2\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">SAP</span>\n                        </span>\n                        <span class=\"nav-chevron\" aria-hidden=\"true\">\n                            <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"m6 9 6 6 6-6\"/></svg>\n                        </span>\n                    </button>\n                    <div class=\"nav-group-items\">\n                        <a class=\"nav-sublink\" href=\"sap.html\" data-page=\"sap\">\n                            <span class=\"nav-sublink-icon\" aria-hidden=\"true\">\n                                <svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.75\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M18 10h-5V7l-5 8h5v3l5-8Z\"/><path d=\"M4 19h16\"/></svg>\n                            </span>\n                            <span class=\"nav-label\">\u0648\u0636\u0639\u06cc\u062a \u06cc\u06a9\u067e\u0627\u0631\u0686\u0647\u200c\u0633\u0627\u0632\u06cc</span>\n                        </a>\n                    </div>\n                </div>\n            ";

  const PAGE_CONFIG = {
    dashboard: { title: "داشبورد کنترل ناوگان", breadcrumb: ["داشبورد"], url: "dashboard.html" },
    vehicles: { title: "خودروها", breadcrumb: ["داشبورد", "خودروها"], url: "vehicles.html" },
    inspection: { title: "بازرسی روزانه خودرو", breadcrumb: ["داشبورد", "راننده", "بازرسی روزانه خودرو"], group: "driver", url: "driver-inspections.html" },
    handover: { title: "تایید تحویل خودرو", breadcrumb: ["داشبورد", "راننده", "تایید تحویل خودرو"], group: "driver", url: "inspections.html?view=handover" },
    faults: { title: "خرابی‌ها", breadcrumb: ["داشبورد", "خرابی‌ها"], url: "faults.html" },
    distribution: { title: "درخواست‌های تعمیر", breadcrumb: ["داشبورد", "توزیع", "درخواست‌های تعمیر"], group: "distribution", url: "faults.html?view=distribution" },
    "transport-repairs": { title: "درخواست‌های تعمیر", breadcrumb: ["داشبورد", "ترابری", "درخواست‌های تعمیر"], group: "transport", url: "transport.html", wizard: ["بررسی درخواست", "تصمیم", "تخصیص"], wizardStep: 1 },
    "transport-handover": { title: "تایید نهایی تعمیرات", breadcrumb: ["داشبورد", "ترابری", "تایید نهایی تعمیرات"], group: "transport", url: "transport.html?view=final-approval", wizard: ["تایید راننده", "بررسی ترابری", "بازگشت به ناوگان"], wizardStep: 2 },
    "transport-materials": { title: "درخواست‌های قطعه", breadcrumb: ["داشبورد", "ترابری", "درخواست‌های قطعه"], group: "transport", url: "materials.html?scope=transport" },
    "transport-invoices": { title: "فاکتورهای خارجی", breadcrumb: ["داشبورد", "ترابری", "فاکتورهای خارجی"], group: "transport", url: "invoices.html" },
    "workshop-orders": { title: "دستورات تعمیر", breadcrumb: ["داشبورد", "تعمیرات", "دستورات تعمیر"], group: "workshop", url: "repairs.html", wizard: ["تایید تعمیرگاه", "شروع تعمیر", "قطعات", "پایان تعمیر"], wizardStep: 1 },
    "workshop-materials": { title: "درخواست قطعه", breadcrumb: ["داشبورد", "تعمیرات", "درخواست قطعه"], group: "workshop", url: "materials.html?scope=workshop" },
    "workshop-history": { title: "تاریخچه تعمیرات", breadcrumb: ["داشبورد", "تعمیرات", "تاریخچه تعمیرات"], group: "workshop", url: "repairs.html?view=history" },
    sap: { title: "وضعیت یکپارچه‌سازی SAP", breadcrumb: ["داشبورد", "SAP", "وضعیت یکپارچه‌سازی"], group: "sap", url: "sap.html" },
  };

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

  function pageConfig(pageId) { return PAGE_CONFIG[pageId] || PAGE_CONFIG.dashboard; }
  function isPageAllowedForRole(pageId, role) { const allowed = ROLE_PAGES[role]; return !allowed || allowed.includes(pageId); }
  function isGroupVisibleForRole(groupId, role) { const allowed = ROLE_PAGES[role]; if (!allowed) return true; return (GROUP_PAGES[groupId] || []).some((p) => allowed.includes(p)); }
  function setGroupExpanded(group, expanded) {
    group.classList.toggle("expanded", expanded);
    group.querySelector(".nav-group-toggle")?.setAttribute("aria-expanded", expanded ? "true" : "false");
  }
  function defaultExpandedGroupsForRole(role) {
    return ({ DRIVER: ["driver"], DISTRIBUTION: ["distribution"], TRANSPORT: ["transport"], WORKSHOP: ["workshop"], MANAGER: [] })[role] || [];
  }
  function applyRoleVisibility(activePage) {
    const role = FMMS.session.getRole();
    document.querySelectorAll(".sidebar-nav .nav-link, .sidebar-nav .nav-sublink").forEach((link) => {
      const pageId = link.dataset.page;
      link.style.display = isPageAllowedForRole(pageId, role) ? "" : "none";
    });
    document.querySelectorAll(".nav-group").forEach((group) => {
      group.style.display = isGroupVisibleForRole(group.dataset.group, role) ? "" : "none";
      setGroupExpanded(group, false);
    });
    defaultExpandedGroupsForRole(role).forEach((groupId) => {
      const group = document.querySelector(`.nav-group[data-group="${groupId}"]`);
      if (group) setGroupExpanded(group, true);
    });
    const activeGroup = pageConfig(activePage).group;
    if (activeGroup) {
      const group = document.querySelector(`.nav-group[data-group="${activeGroup}"]`);
      if (group) setGroupExpanded(group, true);
    }
    if (!isPageAllowedForRole(activePage, role)) window.location.href = "dashboard.html";
  }

  function renderSidebar(activePage) {
    const host = document.getElementById("app-sidebar");
    if (!host) return;
    host.innerHTML = `<nav class="sidebar-nav" id="sidebar-nav">${SIDEBAR_HTML}</nav>`;
    host.querySelectorAll(".nav-group-toggle").forEach((toggle) => {
      toggle.addEventListener("click", () => {
        const group = toggle.closest(".nav-group");
        if (group) setGroupExpanded(group, !group.classList.contains("expanded"));
      });
    });
    host.querySelectorAll(".sidebar-nav .nav-link, .sidebar-nav .nav-sublink").forEach((link) => {
      link.classList.toggle("active", link.dataset.page === activePage);
    });
    host.querySelectorAll(".nav-group").forEach((group) => {
      group.classList.toggle("has-active", (GROUP_PAGES[group.dataset.group] || []).includes(activePage));
    });
    applyRoleVisibility(activePage);
  }

  function refreshWorkshopWizard(orders) {
    const cfg = PAGE_CONFIG["workshop-orders"];
    const wizardEl = document.getElementById("page-chrome-wizard");
    if (!wizardEl || !cfg?.wizard?.length) return;
    wizardEl.style.display = "block";
    wizardEl.innerHTML = FMMS.components.breadcrumb.renderWizard(cfg.wizard, deriveWorkshopWizardStep(orders));
  }

  function workflowStageLabel(vehicle, fault, repairOrder) {
    if (repairOrder) {
      if (repairOrder.status === "CREATED") return "انتظار تایید ترابری";
      if (repairOrder.status === "APPROVED") return "انتخاب تعمیرگاه";
      if (repairOrder.status === "WORKSHOP_ASSIGNED") return "پذیرش تعمیرگاه";
      if (repairOrder.status === "WAITING_WORKSHOP_CONFIRMATION" || repairOrder.status === "ASSIGNED") return "آماده شروع تعمیر";
      if (repairOrder.status === "IN_PROGRESS" || repairOrder.status === "WAITING_PARTS") return "در حال تعمیر";
      if (repairOrder.status === "WAITING_DRIVER_CONFIRMATION") return "منتظر تایید راننده";
      if (repairOrder.status === "WAITING_TRANSPORT_FINAL_APPROVAL") return "منتظر تایید نهایی ترابری";
      if (repairOrder.status === "ACCEPTED_BY_DRIVER") return "تحویل تایید شد";
      if (repairOrder.status === "REJECTED_BY_DRIVER") return "رد راننده";
      if (repairOrder.status === "CANCELLED") return "تعمیر لغو شد";
      if (repairOrder.status === "COMPLETED") return "تعمیر تکمیل‌شده";
    }
    if (fault && fault.status === "OPEN") return "انتظار تصمیم توزیع";
    if (vehicle?.status === "INACTIVE") return "خودرو غیرفعال";
    if (vehicle?.status === "WAITING_DRIVER_CONFIRMATION") return "منتظر تایید راننده";
    if (vehicle?.status === "WAITING_TRANSPORT_FINAL_APPROVAL") return "منتظر تایید نهایی ترابری";
    if (vehicle?.status === "UNDER_REPAIR") return "در حال تعمیر";
    return "در جریان";
  }
  function vehicleStatusSummary(vehicle, repairOrder) {
    if (vehicle?.status === "WAITING_DRIVER_CONFIRMATION") return "منتظر تایید راننده";
    if (repairOrder?.status === "WAITING_TRANSPORT_FINAL_APPROVAL" || vehicle?.status === "WAITING_TRANSPORT_FINAL_APPROVAL") return "منتظر تایید نهایی ترابری";
    if (repairOrder?.status === "IN_PROGRESS" || vehicle?.status === "UNDER_REPAIR") return "در حال تعمیر";
    if (vehicle?.status === "ACTIVE") return "فعال";
    if (vehicle?.status === "INACTIVE") return "غیرفعال";
    if (vehicle?.status === "OUT_OF_SERVICE") return "خارج از سرویس";
    return FMMS.ui.badge(vehicle?.status || "—");
  }
  function deriveWorkshopWizardStep(orders) {
    if (!orders?.length) return 1;
    const stepByStatus = { WORKSHOP_ASSIGNED: 1, WAITING_WORKSHOP_CONFIRMATION: 2, ASSIGNED: 2, IN_PROGRESS: 3, WAITING_PARTS: 3, WAITING_DRIVER_CONFIRMATION: 4, WAITING_TRANSPORT_FINAL_APPROVAL: 4, COMPLETED: 4, ACCEPTED_BY_DRIVER: 4, REJECTED_BY_DRIVER: 4, CANCELLED: 1 };
    return orders.reduce((max, order) => Math.max(max, stepByStatus[order.status] || 1), 1);
  }

  FMMS.components = FMMS.components || {};
  FMMS.components.sidebar = { render: renderSidebar, applyRoleVisibility, pageConfig, isPageAllowedForRole };
  FMMS.shell = {
    navigate: (pageId) => { window.location.href = pageConfig(pageId).url; },
    applyRoleVisibility: () => applyRoleVisibility(document.body.dataset.activePage || "dashboard"),
    getCurrentPage: () => document.body.dataset.activePage || "dashboard",
    refreshWorkshopWizard,
  };
  FMMS.workflow = { workflowStageLabel, vehicleStatusSummary, deriveWorkshopWizardStep };

  function activatePageSection(pageId) {
    const map = {
      dashboard: ["page-dashboard"],
      vehicles: ["page-vehicles"],
      inspection: ["page-inspection"],
      handover: ["page-handover"],
      faults: ["page-faults"],
      distribution: ["page-distribution"],
      "transport-repairs": ["page-transport", "repairs"],
      "transport-materials": ["page-transport", "materials"],
      "transport-invoices": ["page-transport", "invoices"],
      "transport-handover": ["page-transport-handover"],
      "workshop-orders": ["page-workshop", null, "orders"],
      "workshop-materials": ["page-workshop", null, "materials"],
      "workshop-history": ["page-workshop", null, "history"],
      sap: ["page-sap"],
    };
    const [sectionId, transportView, workshopView] = map[pageId] || map.dashboard;
    document.querySelectorAll(".page").forEach((el) => {
      el.style.display = el.id === sectionId ? "block" : "none";
    });
    document.querySelectorAll("[data-transport-view]").forEach((el) => {
      el.style.display = el.dataset.transportView === transportView ? "block" : "none";
    });
    document.querySelectorAll("[data-workshop-view]").forEach((el) => {
      el.style.display = el.dataset.workshopView === workshopView ? "block" : "none";
    });
  }

  function initPage(pageId, renderFn) {
    if (!FMMS.session.isAuthenticated()) {
      window.location.href = "../index.html";
      return;
    }
    document.body.dataset.activePage = pageId;
    FMMS.components.toast?.render?.();
    FMMS.components.modal?.render?.();
    FMMS.components.modal?.renderDebugPanel?.();
    FMMS.components.header?.render?.(pageId);
    renderSidebar(pageId);
    activatePageSection(pageId);
    FMMS.components.breadcrumb?.render?.(pageId);
    Promise.resolve(renderFn?.()).catch((err) => {
      console.error(`[FMMS] page render failed (${pageId}):`, err);
      FMMS.ui?.toast?.(err.message || "خطا در بارگذاری صفحه", "error");
    });
  }

  FMMS.pageBoot = { initPage };
})(window.FMMS);
