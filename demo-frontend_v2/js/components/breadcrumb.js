window.FMMS = window.FMMS || {};

(function (FMMS) {
  const BC_HOME_ICON =
    '<svg class="bc-home-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5 12 4l9 6.5V19a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-8.5Z"/></svg>';

  function renderBreadcrumbHtml(parts) {
    return parts
      .map((part, i) => {
        const sep = i > 0 ? '<span class="bc-sep">/</span>' : "";
        const isLast = i === parts.length - 1;
        if (isLast) return `${sep}<span class="bc-current">${i === 0 ? BC_HOME_ICON : ""}${part}</span>`;
        if (i === 0) return `${sep}<a href="dashboard.html">${BC_HOME_ICON}${part}</a>`;
        return `${sep}<span>${part}</span>`;
      })
      .join("");
  }

  function renderWizard(steps, currentStep) {
    return `<div class="page-wizard-inner">${steps
      .map((label, i) => {
        const n = i + 1;
        const cls = n < currentStep ? "done" : n === currentStep ? "current" : "";
        const dot = n < currentStep ? "✓" : String(n);
        return `<div class="page-wizard-step ${cls}"><span class="page-wizard-dot">${dot}</span><span class="page-wizard-label">${label}</span></div>`;
      })
      .join("")}</div>`;
  }

  function renderPageChrome(pageId) {
    const cfg = FMMS.components.sidebar.pageConfig(pageId);
    const chrome = document.getElementById("app-page-chrome");
    if (!chrome || !cfg) return;
    chrome.style.display = "block";
    const titleEl = document.getElementById("page-chrome-title");
    if (titleEl) titleEl.textContent = cfg.title;
    const bcEl = document.getElementById("page-breadcrumb");
    if (bcEl) bcEl.innerHTML = renderBreadcrumbHtml(cfg.breadcrumb || []);
    const wizardEl = document.getElementById("page-chrome-wizard");
    if (!wizardEl) return;
    if (cfg.wizard?.length) {
      wizardEl.style.display = "block";
      wizardEl.innerHTML = renderWizard(cfg.wizard, cfg.wizardStep || 1);
    } else {
      wizardEl.style.display = "none";
      wizardEl.innerHTML = "";
    }
  }

  FMMS.components = FMMS.components || {};
  FMMS.components.breadcrumb = { render: renderPageChrome, renderWizard };
})(window.FMMS);
