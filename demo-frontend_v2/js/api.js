/**
 * FMMS.api — single entry point for every network call in this demo.
 *
 * - In real mode (FMMS_CONFIG.DEMO_MODE = false) every call goes through
 *   fetch() to FMMS_CONFIG.API_BASE_URL, with the JWT attached automatically
 *   and every path/verb/body matching FMMS_API.yaml exactly.
 * - In demo mode the same call is served from an in-memory mock database
 *   (js/mock-data.js) with the same shapes, so page code never branches on
 *   DEMO_MODE.
 *
 * Page modules never call fetch() directly — they call FMMS.api.*
 */
window.FMMS = window.FMMS || {};

(function (FMMS) {
  const CFG = window.FMMS_CONFIG;

  class ApiError extends Error {
    constructor(message, status, details) {
      super(message);
      this.status = status;
      this.endpoint = details?.endpoint || null;
      this.method = details?.method || null;
      this.body = details?.body ?? null; // raw parsed response body, if any
      this.isNetworkError = details?.isNetworkError || false;
    }
  }

  // Small live-state object the debug panel (and console) read from.
  // Not persisted anywhere — purely in-memory for this tab.
  FMMS.debug = {
    lastCall: null, // "GET /vehicles/"
    lastMethod: null,
    lastUrl: null,
    lastStatus: null,
    lastError: null,
    demoMode: CFG.DEMO_MODE,
    apiBaseUrl: CFG.API_BASE_URL,
  };

  function updateDebugPanel() {
    const panel = document.getElementById("fmms-debug-panel");
    if (!panel) return;
    const d = FMMS.debug;
    const setText = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    };
    setText("dbg-demo-mode", d.demoMode ? "روشن (Mock Data)" : "خاموش (Backend واقعی)");
    const demoEl = document.getElementById("dbg-demo-mode");
    if (demoEl) demoEl.className = "dbg-value " + (d.demoMode ? "dbg-warn" : "dbg-ok");
    setText("dbg-base-url", d.apiBaseUrl);
    setText("dbg-last-call", d.lastCall || "—");
    setText("dbg-last-method", d.lastMethod || "—");
    setText("dbg-last-status", d.lastStatus == null ? "—" : d.lastStatus);
    const statusEl = document.getElementById("dbg-last-status");
    if (statusEl) {
      statusEl.className =
        "dbg-value " +
        (d.lastStatus && d.lastStatus >= 200 && d.lastStatus < 300 ? "dbg-ok" : d.lastStatus ? "dbg-warn" : "");
    }
    setText("dbg-last-error", d.lastError || "—");
  }

  function recordCall(method, path) {
    FMMS.debug.lastMethod = method;
    FMMS.debug.lastCall = `${method} ${path}`;
    FMMS.debug.lastUrl = CFG.DEMO_MODE ? null : CFG.API_BASE_URL + path;
    updateDebugPanel();
  }
  function recordStatus(status) {
    FMMS.debug.lastStatus = status;
    updateDebugPanel();
  }
  function recordError(message) {
    FMMS.debug.lastError = message;
    updateDebugPanel();
  }

  function personaMessageForStatus(status) {
    switch (status) {
      case 400:
        return "اطلاعات ارسالی نامعتبر است.";
      case 401:
        return "نشست شما منقضی شده است. لطفاً دوباره وارد شوید.";
      case 403:
        return "شما اجازه انجام این عملیات را ندارید.";
      case 404:
        return "مورد درخواستی یافت نشد.";
      case 409:
        return "این عملیات با وضعیت فعلی رکورد سازگار نیست.";
      default:
        if (status >= 500) return "خطای سرور. لطفاً بعداً تلاش کنید.";
        return "خطای ناشناخته رخ داد.";
    }
  }

  function getAccessToken() {
    return sessionStorage.getItem("fmms_access_token");
  }

  /** Normalize list responses — backend may return a page object or a bare array. */
  function asPage(data) {
    if (!data) return { count: 0, next: null, previous: null, results: [] };
    if (Array.isArray(data)) return { count: data.length, next: null, previous: null, results: data };
    if (Array.isArray(data.results)) {
      return {
        count: data.count ?? data.results.length,
        next: data.next ?? null,
        previous: data.previous ?? null,
        results: data.results,
      };
    }
    return { count: 0, next: null, previous: null, results: [] };
  }

  function buildUrl(path, query) {
    let url = CFG.API_BASE_URL + path;
    if (query && typeof query === "object") {
      const params = new URLSearchParams();
      Object.keys(query).forEach((key) => {
        const val = query[key];
        if (val !== undefined && val !== null && val !== "") params.append(key, String(val));
      });
      const qs = params.toString();
      if (qs) url += (url.includes("?") ? "&" : "?") + qs;
    }
    return url;
  }

  // ---------------------------------------------------------------------
  // Real network transport
  // ---------------------------------------------------------------------
  async function realRequest(path, { method = "GET", body, query } = {}) {
    const url = buildUrl(path, query);
    const headers = { "Content-Type": "application/json" };
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    recordCall(method, path);
    // eslint-disable-next-line no-console
    console.log(`[FMMS API] → ${method} ${url}`, body ? { body } : "");

    let res;
    const sendBody = body !== undefined || method === "POST" || method === "PUT" || method === "PATCH";
    try {
      res = await fetch(url, {
        method,
        headers,
        body: sendBody ? JSON.stringify(body ?? {}) : undefined,
      });
    } catch (networkErr) {
      // fetch() throws a generic TypeError for both "server unreachable" and
      // "blocked by CORS" — the browser deliberately hides the distinction.
      // We report both possibilities and point at DevTools → Network/Console,
      // where the real reason (connection refused vs. CORS preflight
      // rejection) is visible.
      const msg =
        "ارتباط با سرور برقرار نشد. یا Backend در دسترس نیست، یا درخواست به دلیل CORS مسدود شده است. جزئیات را در Console و تب Network مرورگر بررسی کنید.";
      console.error(`[FMMS API] ✗ ${method} ${url} — network/CORS error`, networkErr);
      recordStatus(0);
      recordError(`${method} ${path} → network/CORS error`);
      throw new ApiError(msg, 0, { endpoint: path, method, isNetworkError: true });
    }

    recordStatus(res.status);

    if (res.status === 204) {
      console.log(`[FMMS API] ← ${res.status} ${method} ${url} (no content)`);
      return null;
    }

    let data = null;
    try {
      data = await res.json();
    } catch (_) {
      /* empty or non-JSON body */
    }

    console.log(`[FMMS API] ← ${res.status} ${method} ${url}`, data);

    if (!res.ok) {
      const detail = {
        endpoint: path,
        method,
        status: res.status,
        body: data,
      };
      console.error(
        `[FMMS API] ✗ ${res.status} ${method} ${url}\n` +
          `  پاسخ: ${JSON.stringify(data)}\n` +
          (res.status === 403
            ? "  این یک خطای Permission است — نقش JWT فعلی برای این عملیات کافی نیست."
            : "")
      );
      recordError(`${method} ${path} → HTTP ${res.status}: ${JSON.stringify(data)}`);
      throw new ApiError(personaMessageForStatus(res.status), res.status, detail);
    }

    recordError(null);
    return data;
  }

  // ---------------------------------------------------------------------
  // Demo transport (js/mock-data.js)
  // ---------------------------------------------------------------------
  function paginated(list) {
    return { count: list.length, next: null, previous: null, results: list };
  }

  function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function recordMockEvent(repairOrderId, eventType, description) {
    const DB = window.FMMS_MOCK_DB;
    if (!DB.repairOrderEvents) DB.repairOrderEvents = [];
    DB.repairOrderEvents.push({
      repair_order_id: repairOrderId,
      event: eventType,
      description,
      created_at: new Date().toISOString(),
      created_by_id: null,
    });
  }

  async function mockRequest(path, { method = "GET", body, query } = {}) {
    recordCall(method, path);
    FMMS.debug.lastUrl = null;
    console.log(`[FMMS API][DEMO MODE] → ${method} ${path} — served from mock-data.js, NOT the real backend`, body ? { body } : "", query || "");
    await delay(220 + Math.random() * 200); // feel like a real network call
    const DB = window.FMMS_MOCK_DB;
    const uid = window.FMMS_MOCK_UID;
    const now = () => new Date().toISOString();

    const match = (pattern) => {
      const re = new RegExp("^" + pattern.replace(/:id/g, "([^/]+)") + "$");
      const m = path.match(re);
      return m ? m.slice(1) : null;
    };

    // ---- auth ----
    if (path === "/auth/token/" && method === "POST") {
      if (!body || !body.email || !body.password) {
        throw new ApiError("ایمیل و رمز عبور الزامی است.", 400);
      }
      return { access: "demo-access-token", refresh: "demo-refresh-token" };
    }

    // ---- vehicles ----
    if (path === "/vehicles/" && method === "GET") {
      let list = DB.vehicles.slice();
      if (query?.status) list = list.filter((v) => v.status === query.status);
      return paginated(list);
    }
    let m = match("/vehicles/:id/");
    if (m && method === "GET") {
      const v = DB.vehicles.find((x) => x.id === m[0]);
      if (!v) throw new ApiError("خودرو یافت نشد.", 404);
      return v;
    }
    m = match("/vehicles/:id/deactivate/");
    if (m && method === "POST") {
      const v = DB.vehicles.find((x) => x.id === m[0]);
      if (!v) throw new ApiError("خودرو یافت نشد.", 404);
      v.status = "INACTIVE";
      v.updated_at = now();
      return v;
    }
    m = match("/vehicles/:id/activate/");
    if (m && method === "POST") {
      const v = DB.vehicles.find((x) => x.id === m[0]);
      if (!v) throw new ApiError("خودرو یافت نشد.", 404);
      const open = DB.repairOrders.filter(
        (ro) =>
          ro.vehicle_id === m[0] &&
          !["COMPLETED", "CANCELLED", "ACCEPTED_BY_DRIVER", "REJECTED_BY_DRIVER"].includes(ro.status)
      );
      if (open.length) {
        throw new ApiError("Vehicle cannot be activated while repair orders are still open.", 409);
      }
      v.status = "ACTIVE";
      v.updated_at = now();
      return v;
    }

    // ---- inspection templates ----
    if (path === "/inspection-templates/" && method === "GET") {
      return paginated(DB.inspectionTemplates);
    }

    // ---- inspections ----
    if (path === "/inspections/" && method === "POST") {
      const inlineItems = Array.isArray(body.items) ? body.items : [];
      const rec = {
        id: uid("insp"),
        vehicle_id: body.vehicle_id,
        inspection_type: body.inspection_type,
        odometer_value: body.odometer_value,
        odometer_unit: body.odometer_unit,
        status: "DRAFT",
        inspected_at: body.inspected_at,
        created_at: now(),
        updated_at: now(),
        items: inlineItems.map((item) => ({
          id: uid("item"),
          category: item.category,
          description: item.description,
          result: item.result,
          notes: item.notes || null,
          severity: item.result === "FAIL" ? item.severity || "MEDIUM" : null,
        })),
        driver_id: body.driver_id || null,
        reviewed_by_id: null,
        review_notes: null,
        has_failures: inlineItems.some((i) => i.result === "FAIL"),
      };
      DB.inspections.push(rec);
      return rec;
    }
    m = match("/inspections/:id/items/");
    if (m && method === "POST") {
      const insp = DB.inspections.find((x) => x.id === m[0]);
      if (!insp) throw new ApiError("بازرسی یافت نشد.", 404);
      const item = {
        id: uid("item"),
        category: body.category,
        description: body.description,
        result: body.result,
        notes: body.notes || null,
        severity: body.result === "FAIL" ? body.severity || "MEDIUM" : null,
      };
      insp.items.push(item);
      if (body.result === "FAIL") insp.has_failures = true;
      insp.updated_at = now();
      return insp;
    }
    m = match("/inspections/:id/submit/");
    if (m && method === "POST") {
      const insp = DB.inspections.find((x) => x.id === m[0]);
      if (!insp) throw new ApiError("بازرسی یافت نشد.", 404);
      insp.status = "SUBMITTED";
      insp.updated_at = now();

      // Mirror backend behaviour: a failed checklist item raises a fault
      // and opens a repair order automatically.
      if (insp.has_failures) {
        const failed = insp.items.filter((i) => i.result === "FAIL");
        failed.forEach((fi) => {
          const itemSeverity = fi.severity || "MEDIUM";
          const fault = {
            id: uid("fault"),
            vehicle_id: insp.vehicle_id,
            code: "INSP-FAIL",
            description: fi.description,
            severity: itemSeverity,
            status: "OPEN",
            reported_by_id: insp.driver_id || "driver-demo",
            reported_at: now(),
            created_at: now(),
            updated_at: now(),
            inspection_id: insp.id,
            assigned_to_id: null,
            sap_notification_number: null,
            created_by: {
              id: "user-manager",
              name: "مدیر سیستم",
              role: "ADMIN",
            },
            items: [
              {
                id: uid("fitem"),
                component: fi.category,
                description: fi.description,
                severity: itemSeverity,
                inspection_item_id: fi.id,
              },
            ],
          };
          DB.faults.push(fault);

          const ro = {
            id: uid("ro"),
            vehicle_id: insp.vehicle_id,
            fault_id: fault.id,
            status: "CREATED",
            created_by_id: "system",
            created_at: now(),
            updated_at: now(),
            activities: [],
            parts: [],
            technician_id: null,
            assigned_at: null,
            sap_order_number: null,
            workshop_type: null,
            completed_at: null,
          };
          DB.repairOrders.push(ro);
          recordMockEvent(ro.id, "FAULT_CREATED", "خرابی از بازرسی ثبت شد.");
        });
      }
      return insp;
    }

    // ---- faults ----
    if (path === "/faults/" && method === "GET") {
      let list = DB.faults.slice();
      if (query?.vehicle_id) {
        list = list.filter((f) => f.vehicle_id === query.vehicle_id);
      } else if (query?.open_by_severity) {
        list = list.filter((f) => f.status !== "CLOSED" && f.severity === query.open_by_severity);
      }
      return paginated(list);
    }
    m = match("/faults/:id/");
    if (m && method === "GET") {
      const f = DB.faults.find((x) => x.id === m[0]);
      if (!f) throw new ApiError("خرابی یافت نشد.", 404);
      return f;
    }
    m = match("/faults/:id/close/");
    if (m && method === "POST") {
      const f = DB.faults.find((x) => x.id === m[0]);
      if (!f) throw new ApiError("خرابی یافت نشد.", 404);
      f.status = "CLOSED";
      f.updated_at = now();
      return f;
    }

    // ---- repair orders ----
    if (path === "/repair-orders/" && method === "GET") {
      let list = DB.repairOrders.slice();
      if (query?.vehicle_id) list = list.filter((r) => r.vehicle_id === query.vehicle_id);
      if (query?.status) list = list.filter((r) => r.status === query.status);
      return paginated(list);
    }
    m = match("/repair-orders/:id/");
    if (m && method === "GET") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      return ro;
    }
    m = match("/repair-orders/:id/approve/");
    if (m && method === "POST") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      ro.status = "APPROVED";
      ro.updated_at = now();
      recordMockEvent(ro.id, "TRANSPORT_APPROVED", "تایید ترابری انجام شد.");
      return { id: ro.id, status: ro.status, message: "تعمیر تایید شد.", workshop_type: ro.workshop_type };
    }
    m = match("/repair-orders/:id/assign-workshop/");
    if (m && method === "POST") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      ro.workshop_type = body.workshop_type;
      ro.workshop_id = body.workshop_id || null;
      ro.status = "WORKSHOP_ASSIGNED";
      ro.sap_order_number = ro.sap_order_number || "PM-" + Math.floor(700000 + Math.random() * 90000);
      ro.updated_at = now();
      recordMockEvent(ro.id, "WORKSHOP_ASSIGNED", "تعمیرگاه انتخاب شد.");
      return {
        id: ro.id,
        status: ro.status,
        message: "تعمیرگاه تخصیص یافت.",
        workshop_type: ro.workshop_type,
        workshop_id: ro.workshop_id,
      };
    }
    m = match("/repair-orders/:id/accept/");
    if (m && method === "POST") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      if (ro.workshop_type !== "INTERNAL" || ro.status !== "WORKSHOP_ASSIGNED") {
        throw new ApiError(`Cannot accept repair from '${ro.status}'.`, 422);
      }
      ro.status = "WAITING_WORKSHOP_CONFIRMATION";
      ro.updated_at = now();
      recordMockEvent(ro.id, "TECHNICIAN_ACCEPTED", "تعمیرکار تعمیر را پذیرفت.");
      return { id: ro.id, status: ro.status, message: "تعمیر پذیرفته شد.", workshop_type: ro.workshop_type };
    }
    m = match("/repair-orders/:id/reject/");
    if (m && method === "POST") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      if (ro.status !== "WORKSHOP_ASSIGNED") {
        throw new ApiError(`Cannot reject repair from '${ro.status}'.`, 422);
      }
      ro.status = "CANCELLED";
      ro.updated_at = now();
      const v = DB.vehicles.find((x) => x.id === ro.vehicle_id);
      if (v) {
        v.status = "ACTIVE";
        v.updated_at = now();
      }
      recordMockEvent(ro.id, "REPAIR_REJECTED", "تعمیر رد شد.");
      return { id: ro.id, status: ro.status, message: "تعمیر رد شد.", workshop_type: ro.workshop_type };
    }
    m = match("/repair-orders/:id/assign/");
    if (m && method === "POST") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      if (ro.status !== "WORKSHOP_ASSIGNED" && ro.status !== "CREATED") {
        throw new ApiError(
          `Cannot transition repair order from '${ro.status}' to 'ASSIGNED'.`,
          422
        );
      }
      ro.status = "ASSIGNED";
      ro.technician_id = body.technician_id;
      ro.assigned_at = now();
      ro.updated_at = now();
      return ro;
    }
    m = match("/repair-orders/:id/start/");
    if (m && method === "POST") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      if (
        !["ASSIGNED", "WORKSHOP_ASSIGNED", "WAITING_WORKSHOP_CONFIRMATION"].includes(ro.status)
      ) {
        throw new ApiError(
          `Cannot transition repair order from '${ro.status}' to 'IN_PROGRESS'.`,
          422
        );
      }
      ro.status = "IN_PROGRESS";
      ro.updated_at = now();
      const v = DB.vehicles.find((x) => x.id === ro.vehicle_id);
      if (v) {
        v.status = "UNDER_REPAIR";
        v.updated_at = now();
      }
      recordMockEvent(ro.id, "REPAIR_STARTED", "تعمیر شروع شد.");
      return ro;
    }
    m = match("/repair-orders/:id/timeline/");
    if (m && method === "GET") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      const events = (DB.repairOrderEvents || []).filter((e) => e.repair_order_id === m[0]);
      return events.map((e) => ({
        event: e.event,
        description: e.description,
        created_at: e.created_at,
        created_by_id: e.created_by_id,
      }));
    }
    m = match("/repair-orders/:id/activities/");
    if (m && method === "POST") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      ro.activities.push({
        id: uid("act"),
        description: body.description,
        labor_hours: body.labor_hours,
        performed_by_id: body.performed_by_id || "tech-demo",
        performed_at: body.performed_at || now(),
        notes: body.notes || null,
      });
      ro.updated_at = now();
      return ro;
    }
    m = match("/repair-orders/:id/parts/");
    if (m && method === "POST") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      ro.parts.push({
        id: uid("part"),
        material_number: body.material_number,
        quantity: body.quantity,
        unit_of_measure: body.unit_of_measure,
        goods_issue_id: null,
        posted_at: null,
      });
      ro.updated_at = now();
      return ro;
    }
    m = match("/repair-orders/:id/material-requests/");
    if (m && method === "POST") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      if (!DB.materialRequests) DB.materialRequests = [];
      const mr = {
        id: uid("mr"),
        repair_order_id: ro.id,
        status: "REQUESTED",
        created_by_id: "tech-demo",
        created_at: now(),
        updated_at: now(),
        items: (body.items || []).map((item) => ({
          id: uid("mri"),
          material_number: item.material_number,
          quantity: String(item.quantity),
          unit_of_measure: item.unit_of_measure,
        })),
      };
      DB.materialRequests.push(mr);
      recordMockEvent(ro.id, "MATERIAL_REQUESTED", "درخواست قطعه ثبت شد.");
      return mr;
    }
    m = match("/repair-orders/:id/invoice/");
    if (m && method === "POST") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      if (ro.workshop_type !== "EXTERNAL") {
        throw new ApiError("ثبت فاکتور فقط برای تعمیرگاه خارجی مجاز است.", 422);
      }
      if (ro.status !== "WAITING_TRANSPORT_FINAL_APPROVAL") {
        throw new ApiError(`Cannot upload external invoice from '${ro.status}'.`, 422);
      }
      if (!DB.externalInvoices) DB.externalInvoices = [];
      const inv = {
        id: uid("inv"),
        repair_order_id: ro.id,
        amount: body.amount,
        currency: body.currency || "IRR",
        status: "UPLOADED",
        created_by_id: "tech-demo",
        created_at: now(),
        updated_at: now(),
        vendor_id: body.vendor_id || null,
        document: body.document || null,
      };
      DB.externalInvoices.push(inv);
      recordMockEvent(ro.id, "INVOICE_UPLOADED", "فاکتور خارجی بارگذاری شد.");
      return inv;
    }
    m = match("/repair-orders/:id/complete/");
    if (m && method === "POST") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      if (ro.status !== "IN_PROGRESS") {
        throw new ApiError(`Cannot complete repair from '${ro.status}'.`, 422);
      }
      const pendingMr = (DB.materialRequests || []).filter(
        (mr) =>
          mr.repair_order_id === ro.id &&
          !["REJECTED", "STOCK_ISSUED", "RECEIVED"].includes(mr.status)
      );
      if (pendingMr.length) {
        throw new ApiError("Cannot complete repair order with pending material requests.", 409);
      }
      ro.status = "WAITING_DRIVER_CONFIRMATION";
      ro.completed_at = body?.completed_at || now();
      ro.updated_at = now();
      const v = DB.vehicles.find((x) => x.id === ro.vehicle_id);
      if (v) {
        v.status = "WAITING_DRIVER_CONFIRMATION";
        v.updated_at = now();
      }
      if (!DB.vehicleHandovers) DB.vehicleHandovers = [];
      DB.vehicleHandovers.push({
        id: uid("ho"),
        repair_order_id: ro.id,
        vehicle_id: ro.vehicle_id,
        status: "WAITING_DRIVER_CONFIRMATION",
        created_at: now(),
        updated_at: now(),
        comment: null,
        driver_id: null,
        confirmed_at: null,
      });
      recordMockEvent(ro.id, "REPAIR_COMPLETED", "تعمیر فنی تکمیل شد.");
      recordMockEvent(ro.id, "WAITING_DRIVER_CONFIRMATION", "منتظر تایید راننده.");
      return ro;
    }
    m = match("/repair-orders/:id/transport-handover-approve/");
    if (m && method === "POST") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      if (ro.status !== "WAITING_TRANSPORT_FINAL_APPROVAL") {
        throw new ApiError(`Cannot approve transport handover from '${ro.status}'.`, 422);
      }
      ro.status = "COMPLETED";
      ro.updated_at = now();
      const v = DB.vehicles.find((x) => x.id === ro.vehicle_id);
      if (v) {
        v.status = "ACTIVE";
        v.updated_at = now();
      }
      const fault = DB.faults.find((x) => x.id === ro.fault_id);
      if (fault && fault.status !== "CLOSED") {
        fault.status = "CLOSED";
        fault.updated_at = now();
      }
      recordMockEvent(ro.id, "TRANSPORT_HANDOVER_APPROVED", "تایید نهایی تحویل توسط ترابری.");
      return ro;
    }
    m = match("/repair-orders/:id/transport-handover-reject/");
    if (m && method === "POST") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      if (ro.status !== "WAITING_TRANSPORT_FINAL_APPROVAL") {
        throw new ApiError(`Cannot reject transport handover from '${ro.status}'.`, 422);
      }
      ro.status = "COMPLETED";
      ro.updated_at = now();
      DB.repairOrders.push({
        id: uid("ro"),
        vehicle_id: ro.vehicle_id,
        fault_id: ro.fault_id,
        status: "CREATED",
        created_by_id: "supervisor-demo",
        created_at: now(),
        updated_at: now(),
        activities: [],
        parts: [],
        technician_id: null,
      });
      const v = DB.vehicles.find((x) => x.id === ro.vehicle_id);
      if (v) {
        v.status = "UNDER_REPAIR";
        v.updated_at = now();
      }
      recordMockEvent(
        ro.id,
        "TRANSPORT_HANDOVER_REJECTED",
        body?.comment ? `رد تعمیر توسط ترابری (${body.comment})` : "رد تعمیر توسط ترابری."
      );
      return ro;
    }
    m = match("/repair-orders/:id/sync-sap/");
    if (m && method === "POST") {
      const ro = DB.repairOrders.find((x) => x.id === m[0]);
      if (!ro) throw new ApiError("دستور تعمیر یافت نشد.", 404);
      ro.sap_order_number = ro.sap_order_number || "PM-" + Math.floor(700000 + Math.random() * 90000);
      ro.updated_at = now();
      return ro;
    }

    // ---- material requests ----
    if (path === "/material-requests/" && method === "GET") {
      if (!DB.materialRequests) DB.materialRequests = [];
      return paginated(DB.materialRequests.slice());
    }
    m = match("/material-requests/:id/approve/");
    if (m && method === "POST") {
      if (!DB.materialRequests) DB.materialRequests = [];
      const mr = DB.materialRequests.find((x) => x.id === m[0]);
      if (!mr) throw new ApiError("درخواست قطعه یافت نشد.", 404);
      mr.status = "APPROVED";
      mr.updated_at = now();
      recordMockEvent(mr.repair_order_id, "MATERIAL_APPROVED", "درخواست قطعه تایید شد.");
      const available = window.FMMS_CONFIG?.MOCK_INVENTORY_AVAILABLE !== false;
      if (available) {
        mr.status = "STOCK_ISSUED";
        recordMockEvent(mr.repair_order_id, "STOCK_ISSUED", "قطعات از انبار صادر شد.");
      } else {
        mr.status = "PURCHASE_REQUIRED";
        if (!DB.purchaseRequisitions) DB.purchaseRequisitions = [];
        DB.purchaseRequisitions.push({
          id: uid("pr"),
          repair_order_id: mr.repair_order_id,
          material_request_id: mr.id,
          status: "DRAFT",
          requested_by_id: "supervisor-demo",
          created_at: now(),
          updated_at: now(),
          line_items: mr.items.map((item) => ({
            id: uid("prli"),
            material_number: item.material_number,
            quantity: item.quantity,
            unit_of_measure: item.unit_of_measure,
            description: "Material request auto-generated line item.",
          })),
        });
        recordMockEvent(mr.repair_order_id, "PURCHASE_REQUIRED", "نیاز به خرید قطعات.");
      }
      mr.updated_at = now();
      return mr;
    }
    m = match("/material-requests/:id/reject/");
    if (m && method === "POST") {
      if (!DB.materialRequests) DB.materialRequests = [];
      const mr = DB.materialRequests.find((x) => x.id === m[0]);
      if (!mr) throw new ApiError("درخواست قطعه یافت نشد.", 404);
      mr.status = "REJECTED";
      mr.updated_at = now();
      recordMockEvent(mr.repair_order_id, "MATERIAL_REJECTED", "درخواست قطعه رد شد.");
      return mr;
    }

    // ---- external invoices ----
    if (path === "/external-invoices/" && method === "GET") {
      if (!DB.externalInvoices) DB.externalInvoices = [];
      return paginated(DB.externalInvoices.slice());
    }
    m = match("/external-invoices/:id/approve/");
    if (m && method === "POST") {
      if (!DB.externalInvoices) DB.externalInvoices = [];
      const inv = DB.externalInvoices.find((x) => x.id === m[0]);
      if (!inv) throw new ApiError("فاکتور یافت نشد.", 404);
      inv.status = "APPROVED";
      inv.updated_at = now();
      const ro = DB.repairOrders.find((x) => x.id === inv.repair_order_id);
      if (ro) {
        ro.status = "COMPLETED";
        ro.updated_at = now();
        const fault = DB.faults.find((x) => x.id === ro.fault_id);
        if (fault && fault.status !== "CLOSED") {
          fault.status = "CLOSED";
          fault.updated_at = now();
        }
        const v = DB.vehicles.find((x) => x.id === ro.vehicle_id);
        if (v) {
          v.status = "ACTIVE";
          v.updated_at = now();
        }
      }
      recordMockEvent(inv.repair_order_id, "EXTERNAL_INVOICE_APPROVED", "فاکتور خارجی تایید و تعمیر نهایی شد.");
      return inv;
    }

    // ---- vehicle handovers ----
    if (path === "/vehicle-handovers/" && method === "GET") {
      if (!DB.vehicleHandovers) DB.vehicleHandovers = [];
      return paginated(DB.vehicleHandovers.slice());
    }
    m = match("/vehicle-handovers/:id/confirm/");
    if (m && method === "POST") {
      if (!DB.vehicleHandovers) DB.vehicleHandovers = [];
      const ho = DB.vehicleHandovers.find((x) => x.id === m[0]);
      if (!ho) throw new ApiError("تحویل خودرو یافت نشد.", 404);
      ho.status = body.accepted ? "ACCEPTED" : "REJECTED";
      ho.comment = body.comment || null;
      ho.confirmed_at = now();
      ho.updated_at = now();
      const ro = DB.repairOrders.find((x) => x.id === ho.repair_order_id);
      const v = DB.vehicles.find((x) => x.id === ho.vehicle_id);
      if (body.accepted) {
        if (ro) {
          ro.status = "WAITING_TRANSPORT_FINAL_APPROVAL";
          ro.updated_at = now();
        }
        if (v) {
          v.status = "WAITING_DRIVER_CONFIRMATION";
          v.updated_at = now();
        }
        recordMockEvent(ho.repair_order_id, "DRIVER_ACCEPTED", "راننده تحویل را تایید کرد.");
        recordMockEvent(ho.repair_order_id, "WAITING_TRANSPORT_FINAL_APPROVAL", "منتظر تایید نهایی ترابری.");
      } else {
        if (ro) {
          ro.status = "REJECTED_BY_DRIVER";
          ro.updated_at = now();
          DB.repairOrders.push({
            id: uid("ro"),
            vehicle_id: ro.vehicle_id,
            fault_id: ro.fault_id,
            status: "CREATED",
            created_by_id: "driver-demo",
            created_at: now(),
            updated_at: now(),
            activities: [],
            parts: [],
            technician_id: null,
            assigned_at: null,
            sap_order_number: null,
            workshop_type: null,
            workshop_id: null,
            completed_at: null,
          });
        }
        recordMockEvent(ho.repair_order_id, "DRIVER_REJECTED", "راننده تحویل را رد کرد.");
      }
      return ho;
    }

    // ---- purchase requisitions ----
    if (path === "/purchase-requisitions/" && method === "GET") {
      if (!DB.purchaseRequisitions) DB.purchaseRequisitions = [];
      let list = DB.purchaseRequisitions.slice();
      if (query?.repair_order_id) {
        list = list.filter((pr) => pr.repair_order_id === query.repair_order_id);
      }
      return paginated(list);
    }
    if (path === "/purchase-requisitions/" && method === "POST") {
      const pr = {
        id: uid("pr"),
        repair_order_id: body.repair_order_id,
        status: "DRAFT",
        requested_by_id: "tech-demo",
        created_at: now(),
        updated_at: now(),
        line_items: [],
      };
      if (!DB.purchaseRequisitions) DB.purchaseRequisitions = [];
      DB.purchaseRequisitions.push(pr);
      return pr;
    }
    m = match("/purchase-requisitions/:id/line-items/");
    if (m && method === "POST") {
      if (!DB.purchaseRequisitions) DB.purchaseRequisitions = [];
      const pr = DB.purchaseRequisitions.find((x) => x.id === m[0]);
      if (!pr) throw new ApiError("درخواست خرید یافت نشد.", 404);
      const line = {
        id: uid("prli"),
        material_number: body.material_number,
        quantity: body.quantity,
        unit_of_measure: body.unit_of_measure,
        description: body.description,
        estimated_amount: body.estimated_amount || null,
        currency: body.currency || null,
      };
      pr.line_items = pr.line_items || [];
      pr.line_items.push(line);
      pr.updated_at = now();
      return pr;
    }

    // ---- SAP ----
    if (path === "/sap-transactions/" && method === "GET") {
      return paginated(DB.sapTransactions);
    }

    throw new ApiError(`مسیر پیاده‌سازی نشده در حالت دمو: ${method} ${path}`, 501);
  }

  /**
   * Fetch every page from a paginated list endpoint.
   */
  async function fetchAllPages(path, query) {
    const all = [];
    let page = 1;
    const baseQuery = { ...(query || {}), page_size: 100 };
    while (true) {
      const res = asPage(await request(path, { query: { ...baseQuery, page } }));
      all.push(...res.results);
      if (!res.next || !res.results.length) break;
      page += 1;
      if (page > 50) break;
    }
    return { count: all.length, next: null, previous: null, results: all };
  }

  const VEHICLE_STATUSES = [
    "ACTIVE",
    "INACTIVE",
    "UNDER_REPAIR",
    "WAITING_DRIVER_CONFIRMATION",
    "SUSPENDED",
    "OUT_OF_SERVICE",
  ];

  async function listAllVehicles(status) {
    if (status) {
      const direct = asPage(
        await request("/vehicles/", { query: { status, page_size: 100 } })
      );
      if (direct.results.length >= (direct.count || direct.results.length) || !direct.next) {
        return direct;
      }
      return fetchAllPages("/vehicles/", { status });
    }

    // Backend returns only ACTIVE vehicles when status is omitted (list_active).
    // Aggregate every documented status so deactivated vehicles remain visible.
    const seen = new Set();
    const merged = [];
    for (const vehicleStatus of VEHICLE_STATUSES) {
      const page = await fetchAllPages("/vehicles/", { status: vehicleStatus });
      for (const vehicle of page.results) {
        if (seen.has(vehicle.id)) continue;
        seen.add(vehicle.id);
        merged.push(vehicle);
      }
    }
    return { count: merged.length, next: null, previous: null, results: merged };
  }

  /**
   * Aggregate all open severities when no filter is supplied.
   */
  async function listOpenFaults() {
    const direct = asPage(await request("/faults/", { query: {} }));
    if (direct.results.length) {
      return {
        ...direct,
        results: direct.results.filter((f) => f.status !== "CLOSED"),
      };
    }

    const severities = API_CAPABILITIES.severityLevels;
    const seen = {};
    const all = [];
    for (const severity of severities) {
      const page = asPage(
        await request("/faults/", { query: { open_by_severity: severity } })
      );
      page.results.forEach((fault) => {
        if (!seen[fault.id]) {
          seen[fault.id] = true;
          all.push(fault);
        }
      });
    }
    return { count: all.length, next: null, previous: null, results: all };
  }

  /**
   * All faults for one vehicle (includes CLOSED) via GET /faults/?vehicle_id=
   */
  async function listFaultsByVehicle(vehicleId) {
    return asPage(await request("/faults/", { query: { vehicle_id: vehicleId } }));
  }

  /**
   * Aggregate faults across fleet when history/closed/all views are needed.
   * YAML has no status filter — closed faults are fetched per vehicle_id.
   */
  async function listAllFaultsAggregated() {
    const direct = asPage(await request("/faults/", { query: {} }));
    if (direct.results.length) return direct;

    // Must include INACTIVE/UNDER_REPAIR vehicles — not only ACTIVE list_active().
    const vehicles = await listAllVehicles();
    const seen = {};
    const all = [];
    for (const vehicle of vehicles.results) {
      try {
        const page = await listFaultsByVehicle(vehicle.id);
        page.results.forEach((fault) => {
          if (!seen[fault.id]) {
            seen[fault.id] = true;
            all.push(fault);
          }
        });
      } catch (err) {
        if (err.status !== 404) throw err;
      }
    }
    return { count: all.length, next: null, previous: null, results: all };
  }

  /**
   * @param {'open'|'closed'|'all'|'vehicle'} mode
   */
  async function listFaultsFiltered(mode, vehicleId) {
    if (mode === "open") {
      return listOpenFaults();
    }
    if (mode === "vehicle") {
      if (!vehicleId) return { count: 0, next: null, previous: null, results: [] };
      return listFaultsByVehicle(vehicleId);
    }

    let page;
    if (CFG.DEMO_MODE) {
      page = asPage(await request("/faults/", { query: {} }));
      if (!page.results.length) page = await listAllFaultsAggregated();
    } else {
      page = await listAllFaultsAggregated();
    }

    if (mode === "closed") {
      const closed = page.results.filter((f) => f.status === "CLOSED");
      return { count: closed.length, next: null, previous: null, results: closed };
    }
    return page;
  }

  function vehicleIsInactive(vehicle) {
    if (!vehicle) return false;
    return ["INACTIVE", "OUT_OF_SERVICE", "SUSPENDED"].includes(vehicle.status);
  }

  /**
   * Faults that completed distribution (usable → CLOSED, unusable → OPEN + inactive vehicle).
   */
  function isDistributionComplete(fault, vehicle) {
    if (!fault) return false;
    if (fault.status === "CLOSED") return true;
    if (fault.status === "OPEN" && vehicleIsInactive(vehicle)) return true;
    return false;
  }

  async function listDistributionReadyFaults() {
    const [vehicles, faults] = await Promise.all([listAllVehicles(), listFaultsFiltered("all")]);
    const vehiclesById = Object.fromEntries(vehicles.results.map((v) => [v.id, v]));
    const ready = faults.results.filter((fault) =>
      isDistributionComplete(fault, vehiclesById[fault.vehicle_id])
    );
    return { vehiclesById, readyFaults: ready };
  }

  /**
   * Repair orders whose linked fault passed distribution — transport queue source.
   * Backend has no fleet-wide repair list; we query per vehicle_id then match fault_id.
   */
  async function listRepairOrdersAfterDistribution() {
    const { readyFaults } = await listDistributionReadyFaults();
    const readyFaultIds = new Set(readyFaults.map((f) => String(f.id)));
    const vehicleIds = [...new Set(readyFaults.map((f) => String(f.vehicle_id)))];

    if (!vehicleIds.length) {
      return { count: 0, next: null, previous: null, results: [] };
    }

    const seen = {};
    const all = [];
    const batchSize = 8;

    for (let offset = 0; offset < vehicleIds.length; offset += batchSize) {
      const batch = vehicleIds.slice(offset, offset + batchSize);
      const pages = await Promise.all(
        batch.map(async (vehicleId) => {
          try {
            return await fetchAllPages("/repair-orders/", { vehicle_id: vehicleId });
          } catch (err) {
            if (err.status === 404 || err.status === 403) {
              return { count: 0, next: null, previous: null, results: [] };
            }
            throw err;
          }
        })
      );

      pages.forEach((page) => {
        page.results.forEach((order) => {
          if (!readyFaultIds.has(String(order.fault_id))) return;
          if (!seen[order.id]) {
            seen[order.id] = true;
            all.push(order);
          }
        });
      });
    }

    all.sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at));
    return { count: all.length, next: null, previous: null, results: all };
  }

  /**
   * Collect vehicle UUIDs that may have repair orders (all statuses + fault fleet).
   */
  async function vehicleIdsForRepairOrderScan() {
    const ids = new Set();
    const add = (value) => {
      if (value !== undefined && value !== null && value !== "") ids.add(String(value));
    };

    const [vehicles, faults] = await Promise.all([listAllVehicles(), listFaultsFiltered("all")]);
    vehicles.results.forEach((vehicle) => add(vehicle.id));
    faults.results.forEach((fault) => add(fault.vehicle_id));
    return Array.from(ids);
  }

  /**
   * Backend requires vehicle_id for repair-order lists.
   * For dashboard/transport views, aggregate across the fleet.
   */
  async function listAllRepairOrders(status) {
    const vehicleIds = await vehicleIdsForRepairOrderScan();
    const seen = {};
    const all = [];
    const batchSize = 8;

    for (let offset = 0; offset < vehicleIds.length; offset += batchSize) {
      const batch = vehicleIds.slice(offset, offset + batchSize);
      const pages = await Promise.all(
        batch.map(async (vehicleId) => {
          try {
            return await fetchAllPages("/repair-orders/", {
              vehicle_id: vehicleId,
              status: status || undefined,
            });
          } catch (err) {
            if (err.status === 404 || err.status === 403) {
              return { count: 0, next: null, previous: null, results: [] };
            }
            throw err;
          }
        })
      );

      pages.forEach((page) => {
        page.results.forEach((order) => {
          if (!seen[order.id]) {
            seen[order.id] = true;
            all.push(order);
          }
        });
      });
    }

    all.sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at));
    return { count: all.length, next: null, previous: null, results: all };
  }

  // ---------------------------------------------------------------------
  // Public API surface
  // ---------------------------------------------------------------------
  async function request(path, opts) {
    if (!CFG.DEMO_MODE) return realRequest(path, opts);
    try {
      const data = await mockRequest(path, opts);
      recordStatus(200);
      recordError(null);
      return data;
    } catch (err) {
      recordStatus(err.status || 0);
      recordError(`[DEMO] ${(opts && opts.method) || "GET"} ${path} → ${err.message}`);
      throw err;
    }
  }

  document.addEventListener("DOMContentLoaded", updateDebugPanel);

  /** Documented API gaps — used by UI for demo-only / disabled features. */
  const API_CAPABILITIES = {
    vehicleActivate: true,
    repairTimeline: true,
    pmOrderCreate: false,
    pmOrderSyncSap: true,
    purchaseRequisition: true,
    materialRequest: true,
    vehicleHandover: true,
    transportHandoverApproval: true,
    transportHandoverReject: true,
    externalInvoice: true,
    workshopAcceptReject: true,
    faultReporterName: true,
    vehicleOdometer: false,
    severityLevels: ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
    severityScope: "both",
    faultSeverityEdit: false,
    faultListFilters: { vehicle_id: true, open_by_severity: true, status: false },
  };

  FMMS.ApiError = ApiError;
  FMMS.api = {
    asPage,
    capabilities: API_CAPABILITIES,
    login: (email, password) => request("/auth/token/", { method: "POST", body: { email, password } }),

    listVehicles: (query) => request("/vehicles/", { query: query || {} }),
    listAllVehicles,
    getVehicle: (id) => request(`/vehicles/${id}/`),
    deactivateVehicle: (id) => request(`/vehicles/${id}/deactivate/`, { method: "POST" }),
    activateVehicle: (id) => request(`/vehicles/${id}/activate/`, { method: "POST" }),

    listInspectionTemplates: () => request("/inspection-templates/"),
    createInspection: (payload) => request("/inspections/", { method: "POST", body: payload }),
    addInspectionItem: (id, payload) => request(`/inspections/${id}/items/`, { method: "POST", body: payload }),
    submitInspection: (id) => request(`/inspections/${id}/submit/`, { method: "POST" }),

    listFaults: (query) => request("/faults/", { query: query || {} }),
    listOpenFaults,
    listFaultsByVehicle,
    listAllFaultsAggregated,
    listFaultsFiltered,
    getFault: (id) => request(`/faults/${id}/`),
    closeFault: (id) => request(`/faults/${id}/close/`, { method: "POST" }),
    deactivateVehicleForFault: (vehicleId) => request(`/vehicles/${vehicleId}/deactivate/`, { method: "POST" }),

    listRepairOrders: (vehicleId, status) => {
      if (!vehicleId) return listAllRepairOrders(status);
      return request("/repair-orders/", { query: { vehicle_id: vehicleId, status: status || undefined } });
    },
    listAllRepairOrders,
    listRepairOrdersAfterDistribution,
    getRepairOrder: (id) => request(`/repair-orders/${id}/`),
    approveRepair: (id) => request(`/repair-orders/${id}/approve/`, { method: "POST" }),
    assignWorkshop: (id, workshopType, workshopId) =>
      request(`/repair-orders/${id}/assign-workshop/`, {
        method: "POST",
        body: {
          workshop_type: workshopType,
          ...(workshopId ? { workshop_id: workshopId } : {}),
        },
      }),
    acceptRepair: (id) => request(`/repair-orders/${id}/accept/`, { method: "POST" }),
    rejectRepair: (id) => request(`/repair-orders/${id}/reject/`, { method: "POST" }),
    assignTechnician: (id, technicianId) =>
      request(`/repair-orders/${id}/assign/`, { method: "POST", body: { technician_id: technicianId } }),
    startRepair: (id) => request(`/repair-orders/${id}/start/`, { method: "POST" }),
    getRepairTimeline: (id) => request(`/repair-orders/${id}/timeline/`),
    addRepairActivity: (id, payload) => request(`/repair-orders/${id}/activities/`, { method: "POST", body: payload }),
    addRepairPart: (id, payload) => request(`/repair-orders/${id}/parts/`, { method: "POST", body: payload }),
    completeRepair: (id, payload) =>
      request(`/repair-orders/${id}/complete/`, {
        method: "POST",
        body: payload || { completed_at: new Date().toISOString() },
      }),
    syncRepairSap: (id, payload) =>
      request(`/repair-orders/${id}/sync-sap/`, { method: "POST", body: payload }),

    createMaterialRequest: (repairOrderId, items) =>
      request(`/repair-orders/${repairOrderId}/material-requests/`, {
        method: "POST",
        body: { items },
      }),
    listMaterialRequests: (query) => request("/material-requests/", { query: query || {} }),
    approveMaterialRequest: (id) => request(`/material-requests/${id}/approve/`, { method: "POST" }),
    rejectMaterialRequest: (id) => request(`/material-requests/${id}/reject/`, { method: "POST" }),

    uploadExternalInvoice: (repairOrderId, payload) =>
      request(`/repair-orders/${repairOrderId}/invoice/`, { method: "POST", body: payload }),
    listExternalInvoices: (query) => request("/external-invoices/", { query: query || {} }),
    approveExternalInvoice: (id) => request(`/external-invoices/${id}/approve/`, { method: "POST" }),

    listVehicleHandovers: (query) => request("/vehicle-handovers/", { query: query || {} }),
    confirmVehicleHandover: (id, payload) =>
      request(`/vehicle-handovers/${id}/confirm/`, { method: "POST", body: payload }),
    transportHandoverApprove: (repairOrderId) =>
      request(`/repair-orders/${repairOrderId}/transport-handover-approve/`, { method: "POST" }),
    transportHandoverReject: (repairOrderId, payload) =>
      request(`/repair-orders/${repairOrderId}/transport-handover-reject/`, {
        method: "POST",
        body: payload || {},
      }),

    createPurchaseRequisition: (repairOrderId) =>
      request("/purchase-requisitions/", { method: "POST", body: { repair_order_id: repairOrderId } }),
    listPurchaseRequisitions: (repairOrderId) =>
      request("/purchase-requisitions/", { query: { repair_order_id: repairOrderId || undefined } }),
    addPurchaseRequisitionLineItem: (prId, payload) =>
      request(`/purchase-requisitions/${prId}/line-items/`, { method: "POST", body: payload }),

    listSapTransactions: () => request("/sap-transactions/"),
  };
})(window.FMMS);
