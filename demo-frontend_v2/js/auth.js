/**
 * Auth + shared UI helpers.
 * Loaded after api.js, before dashboard.js and the page modules.
 */
window.FMMS = window.FMMS || {};

(function (FMMS) {
  // -----------------------------------------------------------------------
  // Shared UI helpers used by every page module
  // -----------------------------------------------------------------------
  const STATUS_LABELS = {
    // vehicle
    ACTIVE: ["فعال", "green"],
    UNDER_REPAIR: ["در حال تعمیر", "orange"],
    WAITING_DRIVER_CONFIRMATION: ["منتظر تایید راننده", "blue"],
    SUSPENDED: ["غیرفعال‌شده", "red"],
    OUT_OF_SERVICE: ["خارج از سرویس", "red"],
    INACTIVE: ["غیرفعال", "red"],
    // fault
    OPEN: ["باز", "amber"],
    ASSIGNED: ["ارجاع‌شده", "blue"],
    IN_REPAIR: ["در حال تعمیر", "amber"],
    CLOSED: ["بسته‌شده", "green"],
    // repair order
    CREATED: ["ایجادشده", "gray"],
    APPROVED: ["تاییدشده", "blue"],
    WORKSHOP_ASSIGNED: ["تعمیرگاه تخصیص یافته", "blue"],
    WAITING_WORKSHOP_CONFIRMATION: ["منتظر تایید تعمیرگاه", "amber"],
    WAITING_PARTS: ["منتظر قطعه", "amber"],
    IN_PROGRESS: ["در حال انجام", "orange"],
    WAITING_DRIVER_CONFIRMATION: ["منتظر تایید راننده", "blue"],
    ACCEPTED_BY_DRIVER: ["تایید راننده", "green"],
    REJECTED_BY_DRIVER: ["رد راننده", "red"],
    COMPLETED: ["تکمیل‌شده", "green"],
    CANCELLED: ["لغوشده", "red"],
    // material request
    REQUESTED: ["درخواست‌شده", "gray"],
    APPROVED: ["تاییدشده", "blue"],
    REJECTED: ["ردشده", "red"],
    WAITING_STOCK: ["منتظر موجودی", "amber"],
    STOCK_ISSUED: ["صادر از انبار", "green"],
    PURCHASE_REQUIRED: ["نیاز به خرید", "amber"],
    RECEIVED: ["دریافت‌شده", "green"],
    // handover / invoice
    ACCEPTED: ["تایید شده", "green"],
    UPLOADED: ["بارگذاری‌شده", "blue"],
    PAID: ["پرداخت‌شده", "green"],
    // severity
    CRITICAL: ["بحرانی", "red"],
    HIGH: ["زیاد", "red"],
    MEDIUM: ["متوسط", "amber"],
    LOW: ["کم", "gray"],
    // sap
    PENDING: ["در انتظار", "gray"],
    SUCCESS: ["موفق", "green"],
    FAILED: ["ناموفق", "red"],
    RETRYING: ["تلاش مجدد", "amber"],
    EXHAUSTED: ["اتمام تلاش‌ها", "red"],
  };

  function badge(statusCode) {
    const entry = STATUS_LABELS[statusCode] || [statusCode, "gray"];
    const [label, tone] = entry;
    return `<span class="badge-fmms badge-${tone}"><span class="dot"></span>${label}</span>`;
  }

  function escapeHtml(str) {
    return String(str ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function formatDateTime(iso) {
    if (!iso) return "—";
    try {
      return new Intl.DateTimeFormat("fa-IR", { dateStyle: "short", timeStyle: "short" }).format(new Date(iso));
    } catch (_) {
      return iso;
    }
  }

  function toast(message, type) {
    const host = document.getElementById("toast-host");
    const el = document.createElement("div");
    el.className = "toast-fmms" + (type === "error" ? " error" : "");
    el.textContent = message;
    host.appendChild(el);
    setTimeout(() => el.remove(), 3600);
  }

  function vehicleLabel(vehicle) {
    if (!vehicle) return "—";
    const name = [vehicle.make, vehicle.model].filter(Boolean).join(" ").trim();
    const plate = vehicle.plate_number || vehicle.vin || vehicle.id || "";
    return name ? `${name} · ${plate}` : String(plate || "—");
  }

  const CATEGORY_LABELS = {
    LIGHT: "سبک",
    MEDIUM: "متوسط",
    HEAVY: "سنگین",
  };

  let detailModalInstance = null;

  function categoryLabel(code) {
    return CATEGORY_LABELS[code] || code || "—";
  }

  function renderDl(rows) {
    return (
      `<dl class="detail-dl">` +
      rows
        .map(([label, value]) => {
          const val = value == null || value === "" ? "—" : value;
          return `<div class="detail-row"><dt>${escapeHtml(label)}</dt><dd>${val}</dd></div>`;
        })
        .join("") +
      `</dl>`
    );
  }

  function renderTable(headers, rows) {
    if (!rows.length) return `<div class="text-muted">موردی ثبت نشده است.</div>`;
    return `<div class="table-fmms-wrap"><table class="table-fmms"><thead><tr>${headers
      .map((h) => `<th>${escapeHtml(h)}</th>`)
      .join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
  }

  function openDetailModal(title, bodyHtml) {
    document.getElementById("detail-modal-title").textContent = title;
    document.getElementById("detail-modal-body").innerHTML = bodyHtml;
    if (!detailModalInstance) {
      detailModalInstance = new bootstrap.Modal(document.getElementById("detail-modal"));
    }
    detailModalInstance.show();
  }

  function openDetailModalLoading(title) {
    openDetailModal(title, `<div class="text-muted py-3">در حال بارگذاری…</div>`);
  }

  function severityLabel(code) {
    const entry = STATUS_LABELS[code];
    return entry ? entry[0] : code || "—";
  }

  function renderSeveritySelect(selected, fieldId, disabled = false) {
    const levels = FMMS.api?.capabilities?.severityLevels || ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
    const options = levels
      .map((s) => `<option value="${s}" ${s === selected ? "selected" : ""}>${severityLabel(s)} (${s})</option>`)
      .join("");
    const disabledAttr = disabled ? " disabled" : "";
    return `<select id="${fieldId}" class="form-control form-control-sm checklist-severity-select"${disabledAttr}>${options}</select>`;
  }

  function renderFaultSeverityBlock(fault) {
    const caps = FMMS.api.capabilities;
    const overall = caps.severityScope === "item" ? null : fault.severity;
    let html = `<div class="severity-readonly-block">`;
    if (overall) {
      html += `<div class="mb-2"><span class="small text-muted d-block mb-1">شدت کلی خرابی</span>${badge(overall)}</div>`;
    }
    if (!caps.faultSeverityEdit) {
      html += `<div class="demo-only-msg">ویرایش شدت خرابی در API فعلی موجود نیست.</div>`;
      html += renderSeveritySelect(overall || "MEDIUM", "fault-severity-disabled", true);
    }
    html += `</div>`;
    return html;
  }

  function createdByLabel(profile) {
    if (!profile) return "—";
    const roleLabels = {
      ADMIN: "مدیر",
      SUPERVISOR: "سرپرست",
      TECHNICIAN: "تعمیرکار",
      VIEWER: "مشاهده‌گر",
    };
    const role = roleLabels[profile.role] || profile.role || "";
    return `${profile.name || "—"}${role ? ` (${role})` : ""}`;
  }

  function renderTimeline(events) {
    if (!events || !events.length) {
      return `<div class="text-muted">رویدادی ثبت نشده است.</div>`;
    }
    return `<div class="repair-timeline">${events
      .map(
        (e, i) => `<div class="repair-timeline-item ${i < events.length - 1 ? "has-next" : ""}">
          <div class="repair-timeline-dot"></div>
          <div class="repair-timeline-body">
            <div class="repair-timeline-event">${escapeHtml(e.event)}</div>
            <div class="repair-timeline-desc">${escapeHtml(e.description)}</div>
            <div class="repair-timeline-time">${formatDateTime(e.created_at)}</div>
          </div>
        </div>`
      )
      .join("")}</div>`;
  }

  FMMS.ui = {
    badge,
    escapeHtml,
    formatDateTime,
    toast,
    vehicleLabel,
    categoryLabel,
    severityLabel,
    renderSeveritySelect,
    createdByLabel,
    renderDl,
    renderTable,
    openDetailModal,
    openDetailModalLoading,
    renderFaultSeverityBlock,
    renderTimeline,
  };

  // -----------------------------------------------------------------------
  // Session
  // -----------------------------------------------------------------------
  const ROLE_LABELS = {
    MANAGER: "مدیر",
    DRIVER: "راننده",
    DISTRIBUTION: "سرپرست توزیع",
    TRANSPORT: "سرپرست ترابری",
    WORKSHOP: "تعمیرکار",
  };

  function parseJwtUserId(token) {
    if (!token) return null;
    try {
      const part = token.split(".")[1];
      if (!part) return null;
      const json = atob(part.replace(/-/g, "+").replace(/_/g, "/"));
      const payload = JSON.parse(json);
      return payload.user_id || payload.sub || null;
    } catch (_) {
      return null;
    }
  }

  FMMS.session = {
    isAuthenticated: () => !!sessionStorage.getItem("fmms_access_token"),
    getEmail: () => sessionStorage.getItem("fmms_email") || "",
    getUserId: () =>
      sessionStorage.getItem("fmms_user_id") ||
      parseJwtUserId(sessionStorage.getItem("fmms_access_token")) ||
      "",
    getTechnicianId: () =>
      sessionStorage.getItem("fmms_technician_id") || FMMS.session.getUserId() || "",
    setTechnicianId: (id) => sessionStorage.setItem("fmms_technician_id", id),
    getRole: () => sessionStorage.getItem("fmms_role") || "MANAGER",
    setRole: (role) => sessionStorage.setItem("fmms_role", role),
    roleLabel: (role) => ROLE_LABELS[role] || role,
    logout: () => {
      sessionStorage.removeItem("fmms_access_token");
      sessionStorage.removeItem("fmms_refresh_token");
      sessionStorage.removeItem("fmms_email");
      sessionStorage.removeItem("fmms_user_id");
      sessionStorage.removeItem("fmms_technician_id");
      sessionStorage.removeItem("fmms_role");
    },
  };

  function showApp() {
    const loginScreen = document.getElementById("login-screen");
    const shell = document.getElementById("app-shell");
    if (loginScreen) loginScreen.style.display = "none";
    if (shell) shell.classList.add("active");
    const userEl = document.getElementById("topbar-user");
    if (userEl) userEl.textContent = FMMS.session.getEmail();
    const roleEl = document.getElementById("role-select");
    if (roleEl) roleEl.value = FMMS.session.getRole();
    if (FMMS.shell?.init) FMMS.shell.init();
  }

  function showLogin() {
    const shell = document.getElementById("app-shell");
    const loginScreen = document.getElementById("login-screen");
    if (shell) shell.classList.remove("active");
    if (loginScreen) loginScreen.style.display = "flex";
  }

  function wireLoginForm() {
    const form = document.getElementById("login-form");
    const errorBox = document.getElementById("login-error");
    const submitBtn = document.getElementById("login-submit");
    if (!form || !submitBtn) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (errorBox) errorBox.style.display = "none";
      const email = document.getElementById("login-email").value.trim();
      const password = document.getElementById("login-password").value;

      submitBtn.disabled = true;
      submitBtn.textContent = "در حال ورود…";
      try {
        const tokens = await FMMS.api.login(email, password);
        // Full response always logged, per debug requirement — even on success,
        // so it's easy to confirm the real backend answered (not mock data).
        console.log("[FMMS Auth] login response:", tokens);
        if (!tokens || !tokens.access) {
          throw new FMMS.ApiError("پاسخ ورود فاقد access token است.", 200, { endpoint: "/auth/token/", method: "POST", body: tokens });
        }
        sessionStorage.setItem("fmms_access_token", tokens.access);
        sessionStorage.setItem("fmms_refresh_token", tokens.refresh || "");
        sessionStorage.setItem("fmms_email", email);
        sessionStorage.setItem("fmms_role", "MANAGER");
        const userId = parseJwtUserId(tokens.access);
        if (userId) sessionStorage.setItem("fmms_user_id", userId);
        showApp();
      } catch (err) {
        console.error("[FMMS Auth] login failed:", {
          status: err.status,
          endpoint: err.endpoint,
          body: err.body,
          message: err.message,
        });
        let msg = err.message || "ورود ناموفق بود.";
        if (err.status === 401 && err.endpoint === "/auth/token/") {
          msg = "ایمیل یا رمز عبور اشتباه است. در حالت دمو (DEMO_MODE=true) هر مقداری کافی است.";
        }
        if (err.status === 0) {
          msg = err.message;
        }
        if (errorBox) {
          errorBox.textContent = msg;
          errorBox.style.display = "block";
        } else {
          FMMS.ui.toast(msg, "error");
        }
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "ورود";
      }
    });

    document.getElementById("logout-btn")?.addEventListener("click", () => {
      FMMS.session.logout();
      showLogin();
    });

    document.getElementById("role-select")?.addEventListener("change", (e) => {
      FMMS.session.setRole(e.target.value);
      FMMS.ui.toast(`نمای شبیه‌سازی به «${FMMS.session.roleLabel(e.target.value)}» تغییر کرد.`);
      FMMS.shell.applyRoleVisibility();
      FMMS.shell.navigate(FMMS.shell.getCurrentPage());
    });
  }

  function wireDebugPanel() {
    const toggle = document.getElementById("dbg-toggle");
    const body = document.getElementById("dbg-body");
    if (!toggle || !body) return;
    toggle.addEventListener("click", () => {
      const collapsed = body.style.display === "none";
      body.style.display = collapsed ? "block" : "none";
      toggle.textContent = collapsed ? "▾" : "▸";
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    wireLoginForm();
    wireDebugPanel();
    if (FMMS.session.isAuthenticated()) {
      showApp();
    }
  });
})(window.FMMS);
