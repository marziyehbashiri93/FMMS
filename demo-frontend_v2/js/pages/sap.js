/**
 * Page: SAP (integration transaction log)
 */
window.FMMS = window.FMMS || {};
FMMS.pages = FMMS.pages || {};

(function (FMMS) {
  const OBJECT_TYPE_LABELS = {
    VEHICLE: "خودرو",
    FAULT: "خرابی",
    REPAIR_ORDER: "دستور تعمیر",
    PURCHASE_REQUISITION: "درخواست خرید",
    PURCHASE_ORDER: "سفارش خرید",
    INSPECTION_TEMPLATE: "قالب بازرسی",
  };

  function row(t) {
    return `<tr>
      <td>${OBJECT_TYPE_LABELS[t.object_type] || t.object_type}</td>
      <td>${FMMS.ui.badge(t.status)}</td>
      <td class="mono">${t.retry_count ?? 0} / ${t.max_retries ?? "—"}</td>
      <td>${t.error_message ? FMMS.ui.escapeHtml(t.error_message) : "—"}</td>
      <td>${FMMS.ui.formatDateTime(t.completed_at || t.updated_at)}</td>
    </tr>`;
  }

  async function render() {
    const tbody = document.getElementById("sap-tbody");
    tbody.innerHTML = `<tr><td colspan="5">در حال بارگذاری…</td></tr>`;
    try {
      const res = FMMS.api.asPage(await FMMS.api.listSapTransactions());
      tbody.innerHTML = res.results.length
        ? res.results.slice().reverse().map(row).join("")
        : `<tr><td colspan="5"><div class="empty-state"><div class="title">تراکنشی ثبت نشده</div></div></td></tr>`;
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5">${FMMS.ui.escapeHtml(err.message)}</td></tr>`;
      FMMS.ui.toast(err.message, "error");
    }
  }

  FMMS.pages.sap = { render };
})(window.FMMS);


document.addEventListener("DOMContentLoaded", () => {
  FMMS.pageBoot?.initPage("sap", () => FMMS.pages.sap?.render?.());
});
