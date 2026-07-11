/**
 * Page: تایید نهایی تعمیرات (Transport final repair approval)
 *
 * Lists repair orders waiting for final transport approval.
 * Approve/reject: POST /repair-orders/{id}/transport-handover-approve|reject/
 */
window.FMMS = window.FMMS || {};
FMMS.pages = FMMS.pages || {};

(function (FMMS) {
  let vehiclesById = {};
  let handoversByRepairOrder = {};

  function workshopTypeLabel(type) {
    if (type === "INTERNAL") return "تعمیرگاه داخلی";
    if (type === "EXTERNAL") return "تعمیرگاه خارجی";
    return "—";
  }

  function isPendingTransportReview(order) {
    return order.status === "WAITING_TRANSPORT_FINAL_APPROVAL" && order.workshop_type !== "EXTERNAL";
  }

  async function ensureVehicles() {
    const res = await FMMS.api.listAllVehicles();
    vehiclesById = Object.fromEntries(res.results.map((v) => [v.id, v]));
  }

  async function loadHandoversIndex() {
    handoversByRepairOrder = {};
    const page = FMMS.api.asPage(await FMMS.api.listVehicleHandovers());
    page.results.forEach((ho) => {
      if (ho.status === "ACCEPTED") {
        handoversByRepairOrder[ho.repair_order_id] = ho;
      }
    });
  }

  async function loadPendingOrders() {
    await ensureVehicles();
    await loadHandoversIndex();
    const page = await FMMS.api.listAllRepairOrders("WAITING_TRANSPORT_FINAL_APPROVAL");
    return page.results.filter(isPendingTransportReview);
  }

  function renderActivitiesTable(activities) {
    if (!activities?.length) {
      return `<div class="text-muted small">فعالیت ثبت‌شده‌ای وجود ندارد.</div>`;
    }
    const rows = activities.map(
      (act) => `<tr>
        <td>${FMMS.ui.escapeHtml(act.description)}</td>
        <td class="mono">${FMMS.ui.escapeHtml(act.labor_hours)}</td>
        <td>${FMMS.ui.formatDateTime(act.performed_at)}</td>
        <td>${act.notes ? FMMS.ui.escapeHtml(act.notes) : "—"}</td>
      </tr>`
    );
    return FMMS.ui.renderTable(["شرح", "نفر-ساعت", "زمان", "یادداشت"], rows);
  }

  function renderPartsTable(parts) {
    if (!parts?.length) {
      return `<div class="text-muted small">قطعه‌ای ثبت نشده است.</div>`;
    }
    const rows = parts.map(
      (part) => `<tr>
        <td class="mono">${FMMS.ui.escapeHtml(part.material_number)}</td>
        <td>${FMMS.ui.escapeHtml(part.quantity)}</td>
        <td>${FMMS.ui.escapeHtml(part.unit_of_measure)}</td>
      </tr>`
    );
    return FMMS.ui.renderTable(["شماره قطعه", "تعداد", "واحد"], rows);
  }

  function renderDriverConfirmation(handover) {
    if (!handover) {
      return `<div class="text-muted small">رکورد تحویل راننده یافت نشد.</div>`;
    }
    const rows = [
      ["نتیجه راننده", handover.status === "ACCEPTED" ? "تایید تحویل" : FMMS.ui.badge(handover.status)],
      ["زمان تایید", handover.confirmed_at ? FMMS.ui.formatDateTime(handover.confirmed_at) : "—"],
      ["توضیح راننده", handover.comment ? FMMS.ui.escapeHtml(handover.comment) : "—"],
    ];
    return FMMS.ui.renderDl(rows);
  }

  function actionAvailabilityNotice() {
    return "";
  }

  function hideDetailModal() {
    bootstrap.Modal.getInstance(document.getElementById("detail-modal"))?.hide();
  }

  async function approveOrder(orderId) {
    if (FMMS.api.capabilities.transportHandoverApproval) {
      await FMMS.api.transportHandoverApprove(orderId);
      FMMS.ui.toast("تایید نهایی تعمیر ثبت شد.");
      return true;
    }
    FMMS.ui.toast("API تایید ترابری در دسترس نیست.", "error");
    return false;
  }

  async function rejectOrder(orderId, comment) {
    if (FMMS.api.capabilities.transportHandoverReject) {
      await FMMS.api.transportHandoverReject(orderId, comment ? { comment } : {});
      FMMS.ui.toast("رد تعمیر ثبت شد.");
      return true;
    }
    FMMS.ui.toast("API رد تعمیر ترابری در دسترس نیست.", "error");
    return false;
  }

  async function showDetail(order) {
    FMMS.ui.openDetailModalLoading("جزئیات تایید نهایی تعمیرات");
    try {
      await ensureVehicles();
      const [fullOrder, timeline, handover] = await Promise.all([
        FMMS.api.getRepairOrder(order.id),
        FMMS.api.getRepairTimeline(order.id).catch(() => []),
        Promise.resolve(handoversByRepairOrder[order.id] || null),
      ]);

      let vehicle = vehiclesById[fullOrder.vehicle_id];
      if (!vehicle) {
        try {
          vehicle = await FMMS.api.getVehicle(fullOrder.vehicle_id);
          vehiclesById[vehicle.id] = vehicle;
        } catch (_) {
          vehicle = null;
        }
      }

      const vehicleRows = [
        ["خودرو", vehicle ? FMMS.ui.vehicleLabel(vehicle) : `<span class="mono">${fullOrder.vehicle_id}</span>`],
        ["پلاک", vehicle ? `<span class="mono">${FMMS.ui.escapeHtml(vehicle.plate_number)}</span>` : "—"],
        ["VIN", vehicle ? `<span class="mono">${FMMS.ui.escapeHtml(vehicle.vin)}</span>` : "—"],
        ["وضعیت خودرو", vehicle ? FMMS.ui.badge(vehicle.status) : "—"],
        ["دسته", vehicle?.category ? FMMS.ui.escapeHtml(vehicle.category) : "—"],
      ];

      const orderRows = [
        ["شناسه دستور", `<span class="mono">${FMMS.ui.escapeHtml(fullOrder.id)}</span>`],
        ["وضعیت", FMMS.ui.badge(fullOrder.status)],
        ["نوع تعمیر", fullOrder.workshop_type ? workshopTypeLabel(fullOrder.workshop_type) : "—"],
        ["تعمیرگاه", fullOrder.workshop_id ? `<span class="mono">${FMMS.ui.escapeHtml(fullOrder.workshop_id)}</span>` : "—"],
        ["اتمام تعمیر", fullOrder.completed_at ? FMMS.ui.formatDateTime(fullOrder.completed_at) : "—"],
        ["شماره PM", fullOrder.sap_order_number ? `<span class="mono">${FMMS.ui.escapeHtml(fullOrder.sap_order_number)}</span>` : "—"],
      ];

      const labeledTimeline = timeline.map((e) => ({
        ...e,
        event: e.event,
      }));

      const body =
        actionAvailabilityNotice() +
        `<div class="modal-section"><div class="modal-section-title">اطلاعات خودرو</div>${FMMS.ui.renderDl(vehicleRows)}</div>` +
        `<div class="modal-section"><div class="modal-section-title">دستور تعمیر</div>${FMMS.ui.renderDl(orderRows)}</div>` +
        `<div class="modal-section"><div class="modal-section-title">نتیجه تایید راننده</div>${renderDriverConfirmation(handover)}</div>` +
        `<div class="modal-section"><div class="modal-section-title">فعالیت‌های تعمیر</div>${renderActivitiesTable(fullOrder.activities)}</div>` +
        `<div class="modal-section"><div class="modal-section-title">قطعات مصرفی</div>${renderPartsTable(fullOrder.parts)}</div>` +
        `<div class="modal-section"><div class="modal-section-title">تاریخچه</div>${FMMS.ui.renderTimeline(labeledTimeline)}</div>` +
        `<div class="transport-detail-actions">
          <p class="small text-muted mb-2">پس از بررسی تعمیر و تایید راننده، تایید نهایی ترابری را ثبت کنید.</p>
          <div class="d-flex flex-wrap gap-2">
            <button type="button" class="btn btn-fmms-success btn-sm" id="transport-ho-approve">تایید نهایی تعمیر</button>
            <button type="button" class="btn btn-fmms-danger btn-sm" id="transport-ho-reject">رد تعمیر</button>
          </div>
        </div>`;

      const titlePlate = vehicle?.plate_number || fullOrder.id.slice(0, 8);
      FMMS.ui.openDetailModal(`تایید نهایی تعمیرات · ${titlePlate}`, body);

      document.getElementById("transport-ho-approve")?.addEventListener("click", async (e) => {
        const btn = e.currentTarget;
        btn.disabled = true;
        try {
          if (await approveOrder(fullOrder.id)) {
            hideDetailModal();
            await render();
          } else {
            btn.disabled = false;
          }
        } catch (err) {
          FMMS.ui.toast(err.message, "error");
          btn.disabled = false;
        }
      });

      document.getElementById("transport-ho-reject")?.addEventListener("click", async (e) => {
        const btn = e.currentTarget;
        btn.disabled = true;
        try {
          if (await rejectOrder(fullOrder.id)) {
            hideDetailModal();
            await render();
          } else {
            btn.disabled = false;
          }
        } catch (err) {
          FMMS.ui.toast(err.message, "error");
          btn.disabled = false;
        }
      });
    } catch (err) {
      FMMS.ui.openDetailModal("خطا", `<div class="text-danger">${FMMS.ui.escapeHtml(err.message)}</div>`);
    }
  }

  function tableRow(order) {
    const v = vehiclesById[order.vehicle_id];
    return `<tr data-ro-id="${order.id}">
      <td>${FMMS.ui.vehicleLabel(v)}</td>
      <td class="mono">${FMMS.ui.escapeHtml(order.sap_order_number || order.id.slice(0, 8))}</td>
      <td>${order.workshop_id ? `<span class="mono">${FMMS.ui.escapeHtml(order.workshop_id)}</span>` : "—"}</td>
      <td>${order.workshop_type ? workshopTypeLabel(order.workshop_type) : "—"}</td>
      <td>${FMMS.ui.badge(order.status)}</td>
      <td>
        <div class="d-flex flex-wrap gap-1 align-items-center">
          <button type="button" class="btn btn-fmms-outline btn-sm" data-action="detail">مشاهده جزئیات</button>
          <button type="button" class="btn btn-fmms-success btn-sm" data-action="approve">تایید نهایی تعمیر</button>
          <button type="button" class="btn btn-fmms-danger btn-sm" data-action="reject">رد تعمیر</button>
        </div>
      </td>
    </tr>`;
  }

  function wireTableActions(orders) {
    const tbody = document.getElementById("transport-handover-tbody");
    if (!tbody) return;
    tbody.querySelectorAll("[data-ro-id]").forEach((tr) => {
      const id = tr.dataset.roId;
      const order = orders.find((o) => o.id === id);
      if (!order) return;

      tr.querySelector('[data-action="detail"]')?.addEventListener("click", () => showDetail(order));

      tr.querySelector('[data-action="approve"]')?.addEventListener("click", async (e) => {
        const btn = e.currentTarget;
        btn.disabled = true;
        try {
          if (await approveOrder(order.id)) await render();
          else btn.disabled = false;
        } catch (err) {
          FMMS.ui.toast(err.message, "error");
          btn.disabled = false;
        }
      });

      tr.querySelector('[data-action="reject"]')?.addEventListener("click", async (e) => {
        const btn = e.currentTarget;
        if (!window.confirm("آیا از رد تعمیر این خودرو اطمینان دارید؟")) return;
        btn.disabled = true;
        try {
          if (await rejectOrder(order.id)) await render();
          else btn.disabled = false;
        } catch (err) {
          FMMS.ui.toast(err.message, "error");
          btn.disabled = false;
        }
      });
    });
  }

  async function render() {
    const tbody = document.getElementById("transport-handover-tbody");
    const hint = document.getElementById("transport-handover-hint");
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="6" class="text-muted py-4 text-center">در حال بارگذاری…</td></tr>`;
    if (hint) {
      hint.textContent =
        "صف خودروهایی که راننده تحویل را تایید کرده و منتظر تایید نهایی ترابری هستند — GET /repair-orders/?status=WAITING_TRANSPORT_FINAL_APPROVAL";
    }

    try {
      const orders = await loadPendingOrders();
      if (!orders.length) {
        tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state py-4"><div class="title">خودرویی منتظر تایید نهایی تعمیرات نیست</div><div>پس از تایید راننده، دستورات «منتظر تایید نهایی ترابری» اینجا نمایش داده می‌شوند.</div></div></td></tr>`;
        return;
      }

      tbody.innerHTML = orders.map(tableRow).join("");
      wireTableActions(orders);
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-danger py-3">${FMMS.ui.escapeHtml(err.message)}</td></tr>`;
      FMMS.ui.toast(err.message, "error");
    }
  }

  FMMS.pages.transportHandover = { render };
})(window.FMMS);
