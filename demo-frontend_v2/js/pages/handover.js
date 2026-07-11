/**
 * Page: تایید تحویل خودرو (Driver vehicle handover confirmation)
 * Separate from daily inspection — only post-repair confirmation.
 */
window.FMMS = window.FMMS || {};
FMMS.pages = FMMS.pages || {};

(function (FMMS) {
  async function render() {
    const listEl = document.getElementById("handover-list");
    if (!listEl) return;

    if (!FMMS.api.capabilities.vehicleHandover) {
      listEl.innerHTML = `<div class="demo-only-msg">API تحویل خودرو در این نسخه موجود نیست.</div>`;
      return;
    }

    listEl.innerHTML = `<div class="text-muted py-3">در حال بارگذاری…</div>`;

    try {
      const [handoversPage, vehiclesPage] = await Promise.all([
        FMMS.api.listVehicleHandovers(),
        FMMS.api.listAllVehicles(),
      ]);
      const handovers = FMMS.api.asPage(handoversPage).results;
      const vehiclesById = Object.fromEntries(vehiclesPage.results.map((v) => [v.id, v]));
      const waiting = handovers.filter((h) => h.status === "WAITING_DRIVER_CONFIRMATION");

      if (!waiting.length) {
        listEl.innerHTML = `<div class="empty-state"><div class="title">خودرویی منتظر تایید تحویل نیست</div><div>پس از اتمام تعمیر، خودروهای آماده تحویل اینجا نمایش داده می‌شوند.</div></div>`;
        return;
      }

      listEl.innerHTML = waiting
        .map((ho) => {
          const v = vehiclesById[ho.vehicle_id];
          return `<div class="card-fmms p-3 mb-3 driver-handover-card" data-ho-id="${ho.id}">
            <div class="mb-2"><span class="text-muted">خودرو:</span> <strong>${FMMS.ui.vehicleLabel(v)}</strong></div>
            <div class="mb-3"><span class="text-muted">وضعیت:</span> تعمیر انجام شده</div>
            <div class="d-flex flex-wrap gap-2">
              <button type="button" class="btn btn-fmms-success btn-sm" data-action="accept-ho">تایید تحویل</button>
              <button type="button" class="btn btn-fmms-danger btn-sm" data-action="reject-ho">رد تحویل</button>
            </div>
            <div class="mt-3 d-none" data-reject-form>
              <label class="form-label small">شرح مشکل</label>
              <textarea class="form-control mb-2" rows="2" data-reject-comment placeholder="شرح مشکل باقی‌مانده…"></textarea>
              <button type="button" class="btn btn-fmms-danger btn-sm" data-action="submit-reject">ثبت رد تحویل</button>
            </div>
          </div>`;
        })
        .join("");

      listEl.querySelectorAll("[data-ho-id]").forEach((card) => {
        const id = card.dataset.hoId;
        card.querySelector('[data-action="accept-ho"]')?.addEventListener("click", async (e) => {
          e.currentTarget.disabled = true;
          try {
            await FMMS.api.confirmVehicleHandover(id, { accepted: true, comment: "OK" });
            FMMS.ui.toast("تحویل تایید شد — منتظر تایید نهایی واحد ترابری.");
            await render();
          } catch (err) {
            FMMS.ui.toast(err.message, "error");
            e.currentTarget.disabled = false;
          }
        });
        card.querySelector('[data-action="reject-ho"]')?.addEventListener("click", () => {
          card.querySelector("[data-reject-form]")?.classList.remove("d-none");
        });
        card.querySelector('[data-action="submit-reject"]')?.addEventListener("click", async (e) => {
          const comment = card.querySelector("[data-reject-comment]")?.value.trim() || "";
          if (!comment) {
            FMMS.ui.toast("شرح مشکل الزامی است.", "error");
            return;
          }
          e.currentTarget.disabled = true;
          try {
            await FMMS.api.confirmVehicleHandover(id, { accepted: false, comment });
            FMMS.ui.toast("تحویل رد شد — درخواست تعمیر جدید ثبت شد.");
            await render();
          } catch (err) {
            FMMS.ui.toast(err.message, "error");
            e.currentTarget.disabled = false;
          }
        });
      });
    } catch (err) {
      listEl.innerHTML = `<div class="text-danger">${FMMS.ui.escapeHtml(err.message)}</div>`;
      FMMS.ui.toast(err.message, "error");
    }
  }

  FMMS.pages.handover = { render };
})(window.FMMS);


document.addEventListener("DOMContentLoaded", () => {
  FMMS.pageBoot?.initPage("handover", () => FMMS.pages.handover?.render?.());
});
