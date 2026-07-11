/**
 * Page: بازرسی روزانه خودرو (Driver daily inspection)
 */
window.FMMS = window.FMMS || {};
FMMS.pages = FMMS.pages || {};

(function (FMMS) {
  let vehicles = [];
  let templates = [];
  let selectedVehicleId = "";
  let itemResults = {};
  let wired = false;
  let vehiclePickerModal = null;

  function setStep(step) {
    document.getElementById("driver-step-1").style.display = step === 1 ? "block" : "none";
    document.getElementById("driver-step-2").style.display = step === 2 ? "block" : "none";
    document.getElementById("driver-step-3").style.display = step === 3 ? "block" : "none";
    document.querySelectorAll("#inspection-wizard .page-wizard-step").forEach((stepEl) => {
      const n = Number(stepEl.dataset.step);
      stepEl.classList.toggle("current", n === step);
      stepEl.classList.toggle("done", n < step);
      const dot = stepEl.querySelector(".page-wizard-dot");
      if (dot) dot.textContent = n < step ? "✓" : String(n);
    });
  }

  function activeVehicles() {
    return vehicles.filter((v) => v.status === "ACTIVE");
  }

  function updateSelectedVehicleSummary() {
    const summary = document.getElementById("inspection-selected-vehicle");
    const hidden = document.getElementById("inspection-vehicle-id");
    if (!selectedVehicleId) {
      summary.textContent = "هنوز خودرویی انتخاب نشده است.";
      summary.classList.add("text-muted");
      hidden.value = "";
      return;
    }
    const v = vehicles.find((x) => x.id === selectedVehicleId);
    summary.textContent = v ? FMMS.ui.vehicleLabel(v) : selectedVehicleId;
    summary.classList.remove("text-muted");
    hidden.value = selectedVehicleId;
  }

  function updateStartButtonState() {
    const active = activeVehicles();
    const btn = document.getElementById("inspection-start-btn");
    const msg = document.getElementById("inspection-no-vehicle-msg");
    const openBtn = document.getElementById("inspection-open-vehicle-modal");

    if (!active.length) {
      msg.classList.remove("d-none");
      btn.disabled = true;
      openBtn.disabled = true;
      return;
    }
    msg.classList.add("d-none");
    openBtn.disabled = false;
    btn.disabled = !selectedVehicleId;
  }

  function isChecklistComplete() {
    if (!templates.length) return false;
    for (const t of templates) {
      const entry = itemResults[t.id];
      if (!entry?.result) return false;
      if (entry.result === "FAIL") {
        if (!entry.notes?.trim()) return false;
        if (!entry.severity) return false;
      }
    }
    return true;
  }

  function updateSubmitButtonState() {
    const btn = document.getElementById("inspection-submit-btn");
    if (!btn) return;
    btn.disabled = !isChecklistComplete();
  }

  function renderVehiclePickerTable() {
    const tbody = document.getElementById("vehicle-picker-tbody");
    const empty = document.getElementById("vehicle-picker-empty");
    const active = activeVehicles();

    if (!active.length) {
      tbody.innerHTML = "";
      empty.classList.remove("d-none");
      return;
    }
    empty.classList.add("d-none");
    tbody.innerHTML = active
      .map(
        (v) => `<tr>
      <td class="mono">${FMMS.ui.escapeHtml(v.plate_number)}</td>
      <td class="mono">${FMMS.ui.escapeHtml(v.sap_equipment_number || v.id)}</td>
      <td>${FMMS.ui.badge(v.status)}</td>
      <td><button type="button" class="btn btn-fmms-primary btn-sm" data-pick="${v.id}">انتخاب</button></td>
    </tr>`
      )
      .join("");

    tbody.querySelectorAll("[data-pick]").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedVehicleId = btn.dataset.pick;
        updateSelectedVehicleSummary();
        updateStartButtonState();
        vehiclePickerModal?.hide();
      });
    });
  }

  function openVehiclePicker() {
    if (!vehiclePickerModal) {
      vehiclePickerModal = new bootstrap.Modal(document.getElementById("vehicle-picker-modal"));
    }
    renderVehiclePickerTable();
    vehiclePickerModal.show();
  }

  function renderChecklist() {
    itemResults = {};
    const host = document.getElementById("inspection-checklist");
    host.innerHTML = templates
      .map(
        (t) => `
      <div class="checklist-row" data-template="${t.id}">
        <div class="checklist-row-main">
          <div>
            <div class="item-name">${FMMS.ui.escapeHtml(t.description)}</div>
            <div class="item-cat">${FMMS.ui.escapeHtml(t.category)}</div>
          </div>
          <div class="result-toggle">
            <button type="button" class="pass" data-result="PASS">سالم</button>
            <button type="button" class="fail" data-result="FAIL">خرابی</button>
          </div>
        </div>
        <div class="checklist-notes-wrap" hidden>
          <label class="checklist-notes-label required" for="notes-${t.id}">شرح خرابی</label>
          <textarea
            id="notes-${t.id}"
            class="form-control checklist-notes-input"
            rows="2"
            placeholder="شرح خرابی را بنویسید…"
          ></textarea>
          <div class="checklist-severity-wrap">
            <label class="checklist-notes-label required" for="severity-${t.id}">شدت خرابی</label>
            ${FMMS.ui.renderSeveritySelect("MEDIUM", `severity-${t.id}`)}
          </div>
        </div>
      </div>`
      )
      .join("");

    host.querySelectorAll(".checklist-row").forEach((row) => {
      const templateId = row.dataset.template;
      const notesWrap = row.querySelector(".checklist-notes-wrap");
      const notesInput = row.querySelector(".checklist-notes-input");
      const severitySelect = row.querySelector(".checklist-severity-select");

      row.querySelectorAll(".result-toggle button").forEach((btn) => {
        btn.addEventListener("click", () => {
          const result = btn.dataset.result;
          itemResults[templateId] = {
            result: result,
            notes: result === "FAIL" ? notesInput.value.trim() : "",
            severity: result === "FAIL" ? severitySelect.value : null,
          };
          row.querySelectorAll("button").forEach((b) => b.classList.remove("selected"));
          btn.classList.add("selected");
          row.classList.toggle("has-fail", result === "FAIL");
          notesWrap.hidden = result !== "FAIL";
          if (result !== "FAIL") {
            notesInput.value = "";
            severitySelect.value = "MEDIUM";
          }
          updateSubmitButtonState();
        });
      });

      notesInput.addEventListener("input", () => {
        if (itemResults[templateId]?.result === "FAIL") {
          itemResults[templateId].notes = notesInput.value.trim();
          updateSubmitButtonState();
        }
      });

      severitySelect.addEventListener("change", () => {
        if (itemResults[templateId]?.result === "FAIL") {
          itemResults[templateId].severity = severitySelect.value;
          updateSubmitButtonState();
        }
      });
    });

    updateSubmitButtonState();
  }

  async function startInspection() {
    if (!selectedVehicleId) return;
    const btn = document.getElementById("inspection-start-btn");
    btn.disabled = true;
    btn.textContent = "در حال آماده‌سازی…";
    try {
      if (!templates.length) {
        const res = await FMMS.api.listInspectionTemplates();
        templates = FMMS.api.asPage(res).results;
      }
      renderChecklist();
      setStep(2);
      document.getElementById("inspection-checklist").dataset.vehicleId = selectedVehicleId;
    } catch (err) {
      FMMS.ui.toast(err.message, "error");
    } finally {
      btn.textContent = "شروع بازرسی";
      updateStartButtonState();
    }
  }

  async function submitInspection() {
    const vehicleId = document.getElementById("inspection-checklist").dataset.vehicleId;
    if (!isChecklistComplete()) {
      FMMS.ui.toast("لطفاً همه موارد الزامی چک‌لیست را تکمیل کنید.", "error");
      return;
    }

    const btn = document.getElementById("inspection-submit-btn");
    btn.disabled = true;
    btn.textContent = "در حال ثبت…";
    try {
      const items = templates.map((t) => {
        const entry = itemResults[t.id];
        const isFail = entry.result === "FAIL";
        return {
          category: t.category,
          description: t.description,
          result: entry.result,
          notes: isFail ? entry.notes.trim() : null,
          severity: isFail ? entry.severity : null,
        };
      });

      const insp = await FMMS.api.createInspection({
        vehicle_id: vehicleId,
        inspection_type: "PRE_TRIP",
        odometer_value: 10000 + Math.floor(Math.random() * 50000),
        odometer_unit: "KM",
        inspected_at: new Date().toISOString(),
        items,
      });

      const submitted = await FMMS.api.submitInspection(insp.id);
      renderResult(submitted, vehicleId);
      setStep(3);
    } catch (err) {
      FMMS.ui.toast(err.message, "error");
    } finally {
      btn.textContent = "ثبت نتیجه بازرسی";
      updateSubmitButtonState();
    }
  }

  function renderResult(insp, vehicleId) {
    const v = vehicles.find((x) => x.id === vehicleId);
    const host = document.getElementById("inspection-result");
    if (!insp.has_failures) {
      host.innerHTML = `
        <div class="result-banner pass">
          <div>
            <h3>خودرو آماده استفاده است</h3>
            <p>بازرسی خودرو ${FMMS.ui.vehicleLabel(v)} با موفقیت انجام شد.</p>
          </div>
        </div>`;
    } else {
      const failedItems = insp.items.filter((i) => i.result === "FAIL");
      const failedList = failedItems
        .map((i) => {
          const note = i.notes ? ` — <span class="text-muted">${FMMS.ui.escapeHtml(i.notes)}</span>` : "";
          const severity = i.severity ? ` ${FMMS.ui.badge(i.severity)}` : "";
          return `<li>${FMMS.ui.escapeHtml(i.description)}${severity}${note}</li>`;
        })
        .join("");
      host.innerHTML = `
        <div class="result-banner fail">
          <div>
            <h3>خرابی ثبت شد و درخواست تعمیر ایجاد شد</h3>
            <p>موارد زیر در بازرسی خودرو ${FMMS.ui.vehicleLabel(v)} ناموفق بودند:</p>
            <ul>${failedList}</ul>
          </div>
        </div>`;
    }
  }

  async function loadVehicles() {
    const res = await FMMS.api.listAllVehicles();
    vehicles = res.results.filter((v) => v.status === "ACTIVE");
    if (selectedVehicleId && !vehicles.find((v) => v.id === selectedVehicleId)) {
      selectedVehicleId = "";
    }
    updateSelectedVehicleSummary();
    updateStartButtonState();
  }

  async function render() {
    try {
      await loadVehicles();
    } catch (err) {
      FMMS.ui.toast(err.message, "error");
      return;
    }

    if (!wired) {
      document.getElementById("inspection-open-vehicle-modal").addEventListener("click", openVehiclePicker);
      document.getElementById("inspection-start-btn").addEventListener("click", startInspection);
      document.getElementById("inspection-submit-btn").addEventListener("click", submitInspection);
      document.getElementById("inspection-restart-btn").addEventListener("click", () => {
        selectedVehicleId = "";
        updateSelectedVehicleSummary();
        updateStartButtonState();
        setStep(1);
      });
      wired = true;
    }
    setStep(1);
  }

  FMMS.pages.inspection = { render };
})(window.FMMS);
