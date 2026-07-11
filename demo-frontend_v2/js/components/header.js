window.FMMS = window.FMMS || {};

(function (FMMS) {
  function renderHeader(activePage) {
    const host = document.getElementById("app-header");
    if (!host) return;
    host.innerHTML = `<div class="topbar">
      <div class="topbar-brand">
        <div class="topbar-brand-mark">FM</div>
        <span>مرکز کنترل نگهداری و تعمیرات ناوگان </span>
      </div>
      <div class="toolbar_roles">
        <div class="topbar-role">
          <label for="role-select" class="topbar-user" style="margin-inline-end:2px;">مشاهده به‌عنوان</label>
          <select id="role-select" class="role-select">
            <option value="MANAGER">مدیر (دسترسی کامل)</option>
            <option value="DRIVER">راننده</option>
            <option value="DISTRIBUTION">سرپرست توزیع</option>
            <option value="TRANSPORT">سرپرست ترابری</option>
            <option value="WORKSHOP">تعمیرکار</option>
          </select>
        </div>
        <button class="btn btn-fmms-outline btn-sm topbar-logout" id="logout-btn">خروج</button>
      </div>
    </div>`;

    const roleEl = document.getElementById("role-select");
    if (roleEl) {
      roleEl.value = FMMS.session.getRole();
      roleEl.addEventListener("change", (e) => {
        FMMS.session.setRole(e.target.value);
        FMMS.ui.toast(`نمای شبیه‌سازی به «${FMMS.session.roleLabel(e.target.value)}» تغییر کرد.`);
        FMMS.components.sidebar.applyRoleVisibility(activePage);
      });
    }

    document.getElementById("logout-btn")?.addEventListener("click", () => {
      FMMS.session.logout();
      window.location.href = "../index.html";
    });
  }

  FMMS.components = FMMS.components || {};
  FMMS.components.header = { render: renderHeader };
})(window.FMMS);
