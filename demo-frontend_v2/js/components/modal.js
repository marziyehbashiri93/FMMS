window.FMMS = window.FMMS || {};

(function (FMMS) {
  function renderModals() {
    const root = document.getElementById("modal-root");
    if (!root || root.dataset.ready === "1") return;
    root.dataset.ready = "1";
    root.innerHTML = `
      <div class="modal fade" id="repair-action-modal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered modal-fmms-wide">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title" id="repair-action-modal-title">عملیات</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="repair-action-modal-body"></div>
            <div class="modal-footer">
              <button type="button" class="btn btn-fmms-outline" data-bs-dismiss="modal">انصراف</button>
              <button type="button" class="btn btn-fmms-primary" id="repair-action-modal-confirm">ثبت</button>
            </div>
          </div>
        </div>
      </div>
      <div class="modal fade" id="timeline-modal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered modal-fmms-wide">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title" id="timeline-modal-title">تاریخچه تعمیر</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="timeline-modal-body"></div>
            <div class="modal-footer">
              <button type="button" class="btn btn-fmms-outline" data-bs-dismiss="modal">بستن</button>
            </div>
          </div>
        </div>
      </div>
      <div class="modal fade" id="detail-modal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered modal-fmms-wide modal-dialog-scrollable">
          <div class="modal-content">
            <div class="modal-header">
              <div class="detail-modal-heading">
                <h5 class="modal-title" id="detail-modal-title">جزئیات</h5>
                <p class="detail-modal-subtitle d-none" id="detail-modal-subtitle"></p>
              </div>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="detail-modal-body"></div>
            <div class="modal-footer" id="detail-modal-footer">
              <button type="button" class="btn btn-fmms-outline" data-bs-dismiss="modal" id="detail-modal-dismiss">بستن</button>
            </div>
          </div>
        </div>
      </div>
      <div class="modal fade" id="vehicle-picker-modal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered modal-fmms-wide">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">انتخاب خودرو فعال</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <div id="vehicle-picker-empty" class="empty-state d-none">
                <div class="title">خودروی فعال برای شروع بازرسی یافت نشد.</div>
              </div>
              <div class="table-fmms-wrap">
                <table class="table-fmms">
                  <thead><tr><th>پلاک</th><th>شماره خودرو / کد تجهیز</th><th>وضعیت</th><th>عملیات</th></tr></thead>
                  <tbody id="vehicle-picker-tbody"></tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>`;
  }

  function renderDebugPanel() {
    const root = document.getElementById("debug-root");
    if (!root || document.getElementById("fmms-debug-panel")) return;
    root.innerHTML = `<div id="fmms-debug-panel">
      <div class="dbg-head"><span>Debug</span><button type="button" id="dbg-toggle" aria-label="toggle">▾</button></div>
      <div class="dbg-body" id="dbg-body">
        <div class="dbg-row"><span class="dbg-key">DEMO_MODE</span><span class="dbg-value" id="dbg-demo-mode">—</span></div>
        <div class="dbg-row"><span class="dbg-key">API_BASE_URL</span><span class="dbg-value mono" id="dbg-base-url">—</span></div>
        <div class="dbg-row"><span class="dbg-key">آخرین درخواست</span><span class="dbg-value mono" id="dbg-last-call">—</span></div>
        <div class="dbg-row"><span class="dbg-key">آخرین متد</span><span class="dbg-value mono" id="dbg-last-method">—</span></div>
        <div class="dbg-row"><span class="dbg-key">آخرین کد وضعیت</span><span class="dbg-value mono" id="dbg-last-status">—</span></div>
        <div class="dbg-row"><span class="dbg-key">آخرین خطا</span><span class="dbg-value mono" id="dbg-last-error">—</span></div>
      </div>
    </div>`;
  }

  FMMS.components = FMMS.components || {};
  FMMS.components.modal = { render: renderModals, renderDebugPanel };
})(window.FMMS);
