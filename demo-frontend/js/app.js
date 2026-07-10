/**
 * FMMS Demo Frontend — UI rendering and event wiring only.
 */
(function () {
  "use strict";

  var STAGE_INDEX = {
    login: 0,
    vehicle: 1,
    inspection: 2,
    fault: 3,
    distribution: 4,
    transport_approve: 5,
    workshop: 6,
  };

  var STATUS_FA = {
    OPEN: "باز",
    CLOSED: "بسته",
    CREATED: "ایجاد شده",
    APPROVED: "تأیید شده",
    WORKSHOP_ASSIGNED: "تعمیرگاه تعیین شد",
    IN_PROGRESS: "در حال انجام",
    COMPLETED: "تکمیل شده",
    ACTIVE: "فعال",
    OUT_OF_SERVICE: "خارج از سرویس",
    INACTIVE: "غیرفعال",
  };

  var SEVERITY_FA = {
    CRITICAL: "بحرانی",
    HIGH: "بالا",
    MEDIUM: "متوسط",
    LOW: "پایین",
  };

  var CHECKLIST_FA = {
    "Seat belt": "کمربند ایمنی",
    "Front light": "چراغ جلو",
    Refrigerator: "یخچال",
    "Safety equipment": "تجهیزات ایمنی",
  };

  function $(id) {
    return document.getElementById(id);
  }

  function show(el, visible) {
    if (!el) return;
    el.classList.toggle("d-none", !visible);
  }

  function setText(el, text) {
    if (el) el.textContent = text || "—";
  }

  function showAlert(el, text, visible) {
    if (!el) return;
    el.textContent = text || "";
    show(el, visible && Boolean(text));
  }

  function translateStatus(value) {
    return STATUS_FA[value] || value || "—";
  }

  function translateSeverity(value) {
    return SEVERITY_FA[value] || value || "—";
  }

  function translateChecklistLabel(value) {
    return CHECKLIST_FA[value] || value || "آیتم بازرسی";
  }

  function vehicleLabel(vehicle) {
    if (!vehicle) return "—";
    return (vehicle.plate_number || vehicle.vin || vehicle.id || "—").toString();
  }

  function findVehicle(vehicles, id) {
    return (vehicles || []).find(function (v) {
      return v.id === id;
    });
  }

  function stageIndex(stage) {
    return STAGE_INDEX[stage] !== undefined ? STAGE_INDEX[stage] : 0;
  }

  function renderWorkflowStages(state) {
    var host = $("workflow-stages");
    if (!host) return;
    host.innerHTML = "";
    var current = stageIndex(state.stage);
    state.stages.forEach(function (step, index) {
      var li = document.createElement("li");
      li.className = "workflow-step";
      if (index < current) li.classList.add("done");
      if (index === current) li.classList.add("current");
      li.textContent = step.label;
      host.appendChild(li);
    });
  }

  function renderPageNav(state) {
    document.querySelectorAll("[data-page-nav]").forEach(function (btn) {
      var page = btn.getAttribute("data-page-nav");
      btn.classList.toggle("active", state.page === page);
    });
  }

  function renderDebug() {
    var dbg = FMMSApi.getDebugState();
    setText($("dbg-auth"), dbg.authenticated ? "وارد شده" : "وارد نشده");
    setText($("dbg-url"), dbg.baseUrl || "—");
    setText(
      $("dbg-request"),
      dbg.lastMethod && dbg.lastPath ? dbg.lastMethod + " " + dbg.lastPath : "—"
    );
    setText($("dbg-status"), dbg.lastStatus !== null ? String(dbg.lastStatus) : "—");
    setText($("dbg-error"), dbg.lastError || "—");
    var pre = $("dbg-response");
    if (pre) {
      pre.textContent = dbg.lastResponse ? JSON.stringify(dbg.lastResponse, null, 2) : "—";
    }
  }

  function renderVehicleSelect(state) {
    var select = $("vehicle-select");
    if (!select) return;
    var vehicles = state.driver.vehicles || [];
    select.innerHTML = "";
    if (!vehicles.length) {
      var empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "خودرویی یافت نشد";
      select.appendChild(empty);
      return;
    }
    vehicles.forEach(function (vehicle) {
      var opt = document.createElement("option");
      opt.value = vehicle.id;
      opt.textContent = vehicleLabel(vehicle);
      if (vehicle.id === state.driver.selectedVehicleId) opt.selected = true;
      select.appendChild(opt);
    });
  }

  function renderChecklist(state) {
    var host = $("checklist-host");
    if (!host) return;
    host.innerHTML = "";
    var checklist = state.driver.checklist || [];
    if (!checklist.length) {
      host.innerHTML =
        '<p class="text-muted mb-0">قالب چک‌لیست یافت نشد. ابتدا داده‌ها را از سرویس بارگذاری کنید.</p>';
      return;
    }

    checklist.forEach(function (item, index) {
      var row = document.createElement("div");
      row.className = "checklist-item" + (item.result === "FAIL" ? " fail" : "");

      var title = document.createElement("div");
      title.className = "fw-semibold mb-2";
      title.textContent = translateChecklistLabel(item.description || item.category);
      row.appendChild(title);

      var controls = document.createElement("div");
      controls.className = "d-flex flex-wrap gap-3 align-items-center mb-2";

      var passId = "chk-pass-" + index;
      var failId = "chk-fail-" + index;

      controls.innerHTML =
        '<div class="form-check">' +
        '<input class="form-check-input" type="radio" name="result-' +
        index +
        '" id="' +
        passId +
        '" value="PASS"' +
        (item.result === "PASS" ? " checked" : "") +
        ">" +
        '<label class="form-check-label" for="' +
        passId +
        '">سالم</label>' +
        "</div>" +
        '<div class="form-check">' +
        '<input class="form-check-input" type="radio" name="result-' +
        index +
        '" id="' +
        failId +
        '" value="FAIL"' +
        (item.result === "FAIL" ? " checked" : "") +
        ">" +
        '<label class="form-check-label" for="' +
        failId +
        '">خراب</label>' +
        "</div>";
      row.appendChild(controls);

      var notesWrap = document.createElement("div");
      notesWrap.className = item.result === "FAIL" ? "" : "d-none";
      var notesLabel = document.createElement("label");
      notesLabel.className = "form-label";
      notesLabel.textContent = "توضیح خرابی";
      notesWrap.appendChild(notesLabel);
      var notes = document.createElement("textarea");
      notes.className = "form-control";
      notes.rows = 2;
      notes.value = item.notes || "";
      notesWrap.appendChild(notes);
      row.appendChild(notesWrap);

      row.querySelectorAll('input[type="radio"]').forEach(function (radio) {
        radio.addEventListener("change", function () {
          FMMSWorkflow.setChecklistItem(index, {
            result: radio.value,
            notes: radio.value === "FAIL" ? notes.value : "",
          });
        });
      });
      notes.addEventListener("input", function () {
        FMMSWorkflow.setChecklistItem(index, { notes: notes.value });
      });

      host.appendChild(row);
    });
  }

  function renderDriverResult(state) {
    var driver = state.driver;
    showAlert($("driver-message"), driver.message, true);
    showAlert($("driver-error"), driver.error, true);
    var canSubmit = Boolean(driver.inspectionId) && !driver.inspectionResult;
    var submitBtn = $("btn-submit-inspection");
    if (submitBtn) submitBtn.disabled = !canSubmit;
    show($("btn-go-distribution"), driver.inspectionResult === "FAIL");
  }

  function renderFaults(state) {
    var host = $("faults-host");
    var detailHost = $("fault-detail-host");
    if (!host || !detailHost) return;

    host.innerHTML = "";
    var faults = state.distribution.openFaults || [];
    if (!faults.length) {
      host.innerHTML = '<p class="text-muted mb-0">خرابی بازی برای نمایش وجود ندارد.</p>';
      detailHost.innerHTML = "";
      return;
    }

    faults.forEach(function (fault) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        "fault-item" +
        (fault.id === state.distribution.selectedFaultId ? " active" : "");
      btn.textContent =
        (fault.description || fault.code || "خرابی") +
        " — " +
        translateSeverity(fault.severity);
      btn.addEventListener("click", function () {
        FMMSWorkflow.selectDistributionFault(fault.id);
      });
      host.appendChild(btn);
    });

    var selected = state.distribution.selectedFault;
    if (!selected) {
      detailHost.innerHTML = "";
      return;
    }

    var vehicle = findVehicle(state.distribution.vehicles, selected.vehicle_id);
    detailHost.innerHTML =
      '<table class="detail-table">' +
      "<tr><th>خودرو</th><td>" +
      vehicleLabel(vehicle) +
      "</td></tr>" +
      "<tr><th>شرح خرابی</th><td>" +
      (selected.description || selected.code || "—") +
      "</td></tr>" +
      "<tr><th>وضعیت</th><td>" +
      translateStatus(selected.status) +
      "</td></tr>" +
      "</table>";
  }

  function renderDistributionResult(state) {
    showAlert($("distribution-message"), state.distribution.message, true);
    showAlert($("distribution-error"), state.distribution.error, true);
  }

  function renderRepair(state) {
    var host = $("repair-detail-host");
    if (!host) return;
    var order = state.transport.repairOrder;
    if (!order) {
      host.innerHTML =
        '<p class="text-muted mb-0">دستور تعمیر مرتبط یافت نشد. دکمه «بارگذاری دستور تعمیر» را بزنید.</p>';
      return;
    }
    var vehicle = findVehicle(state.transport.vehicles, order.vehicle_id);
    var workshopLabel = "—";
    if (order.workshop_type === "INTERNAL") workshopLabel = "تعمیرگاه داخلی";
    if (order.workshop_type === "EXTERNAL") workshopLabel = "تعمیرگاه بیرونی";

    host.innerHTML =
      '<table class="detail-table">' +
      "<tr><th>خودرو</th><td>" +
      vehicleLabel(vehicle) +
      "</td></tr>" +
      "<tr><th>شناسه دستور</th><td class='ltr-field'>" +
      (order.id || "—") +
      "</td></tr>" +
      "<tr><th>وضعیت</th><td>" +
      translateStatus(order.status) +
      "</td></tr>" +
      "<tr><th>نوع تعمیرگاه</th><td>" +
      workshopLabel +
      "</td></tr>" +
      "</table>";
  }

  function renderTransportResult(state) {
    showAlert($("transport-message"), state.transport.message, true);
    showAlert($("transport-error"), state.transport.error, true);
  }

  function render(state) {
    var authenticated = state.authenticated;
    show($("screen-login"), !authenticated);
    show($("screen-workflow"), authenticated);
    show($("btn-logout"), authenticated);
    show($("nav-user"), authenticated);

    if (!authenticated) {
      renderDebug();
      return;
    }

    var driver = state.driver;
    var vehicle = findVehicle(driver.vehicles, driver.selectedVehicleId);
    var stageLabel =
      (state.stages.find(function (s) {
        return s.id === state.stage;
      }) || {}).label || "—";

    setText($("nav-user"), state.session && state.session.email ? state.session.email : "");
    setText($("ops-stage"), stageLabel);
    setText($("ops-vehicle"), vehicleLabel(vehicle));
    setText(
      $("ops-inspection-result"),
      driver.inspectionResult === "PASS"
        ? "سالم"
        : driver.inspectionResult === "FAIL"
          ? "دارای خرابی"
          : "—"
    );

    renderWorkflowStages(state);
    renderPageNav(state);

    show($("panel-driver"), state.page === FMMSWorkflow.PAGES.driver);
    show($("panel-distribution"), state.page === FMMSWorkflow.PAGES.distribution);
    show($("panel-transport"), state.page === FMMSWorkflow.PAGES.transport);

    renderVehicleSelect(state);
    renderChecklist(state);
    renderDriverResult(state);
    renderFaults(state);
    renderDistributionResult(state);
    renderRepair(state);
    renderTransportResult(state);
    renderDebug();
  }

  function withDriverError(action) {
    FMMSWorkflow.clearDriverError();
    return action().catch(function (err) {
      FMMSWorkflow.setDriverError(err.message || "خطای نامشخص رخ داد");
    });
  }

  function withDistributionError(action) {
    FMMSWorkflow.clearDistributionError();
    return action().catch(function (err) {
      FMMSWorkflow.setDistributionError(err.message || "خطای نامشخص رخ داد");
    });
  }

  function withTransportError(action) {
    FMMSWorkflow.clearTransportError();
    return action().catch(function (err) {
      FMMSWorkflow.setTransportError(err.message || "خطای نامشخص رخ داد");
    });
  }

  function bindEvents() {
    $("btn-login").addEventListener("click", function () {
      var email = $("login-email").value.trim();
      var password = $("login-password").value;
      showAlert($("login-alert"), "", false);
      withDriverError(async function () {
        if (!email || !password) throw new Error("ایمیل و رمز عبور الزامی است");
        await FMMSWorkflow.login(email, password);
        await FMMSWorkflow.loadDriverData();
      }).catch(function (err) {
        showAlert($("login-alert"), err.message || "ورود ناموفق بود", true);
        renderDebug();
      });
    });

    $("btn-logout").addEventListener("click", function () {
      FMMSWorkflow.logout();
    });

    document.querySelectorAll("[data-page-nav]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        FMMSWorkflow.goToPage(btn.getAttribute("data-page-nav"));
      });
    });

    $("btn-reload-data").addEventListener("click", function () {
      withDriverError(function () {
        return FMMSWorkflow.loadDriverData();
      });
    });

    $("btn-select-vehicle").addEventListener("click", function () {
      var id = $("vehicle-select").value;
      if (!id) return;
      FMMSWorkflow.selectVehicle(id);
    });

    $("vehicle-select").addEventListener("change", function () {
      FMMSWorkflow.selectVehicle($("vehicle-select").value);
    });

    $("btn-create-inspection").addEventListener("click", function () {
      withDriverError(function () {
        return FMMSWorkflow.createInspection({
          odometer_value: Number($("insp-odometer").value || 0),
          inspection_type: "PRE_TRIP",
        });
      });
    });

    $("btn-submit-inspection").addEventListener("click", function () {
      withDriverError(function () {
        return FMMSWorkflow.submitDriverInspection();
      });
    });

    $("btn-go-distribution").addEventListener("click", function () {
      FMMSWorkflow.goToPage(FMMSWorkflow.PAGES.distribution);
      withDistributionError(function () {
        return FMMSWorkflow.loadDistributionFaults();
      });
    });

    document.querySelectorAll("[data-page-nav='distribution']").forEach(function (btn) {
      btn.addEventListener("click", function () {
        withDistributionError(function () {
          return FMMSWorkflow.loadDistributionFaults();
        });
      });
    });

    $("btn-refresh-faults").addEventListener("click", function () {
      withDistributionError(function () {
        return FMMSWorkflow.loadDistributionFaults();
      });
    });

    $("btn-close-fault").addEventListener("click", function () {
      withDistributionError(function () {
        return FMMSWorkflow.closeFaultAsUsable();
      });
    });

    $("btn-deactivate-vehicle").addEventListener("click", function () {
      withDistributionError(function () {
        return FMMSWorkflow.deactivateVehicleForRepair();
      });
    });

    $("btn-refresh-repair").addEventListener("click", function () {
      withTransportError(function () {
        return FMMSWorkflow.loadTransportRepairOrder();
      });
    });

    $("btn-approve-repair").addEventListener("click", function () {
      withTransportError(function () {
        return FMMSWorkflow.approveRepair();
      });
    });

    $("btn-workshop-internal").addEventListener("click", function () {
      withTransportError(function () {
        return FMMSWorkflow.assignWorkshop("INTERNAL");
      });
    });

    $("btn-workshop-external").addEventListener("click", function () {
      withTransportError(function () {
        return FMMSWorkflow.assignWorkshop("EXTERNAL");
      });
    });
  }

  FMMSWorkflow.onChange(render);
  bindEvents();
  render(FMMSWorkflow.getState());

  if (FMMSApi.getToken()) {
    withDriverError(function () {
      return FMMSWorkflow.loadDriverData();
    });
  }
})();
