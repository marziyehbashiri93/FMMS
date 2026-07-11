window.FMMS = window.FMMS || {};

(function (FMMS) {
  function renderToastHost() {
    const root = document.getElementById("toast-root");
    if (root && !document.getElementById("toast-host")) {
      root.innerHTML = '<div class="toast-fmms-host" id="toast-host"></div>';
    }
  }

  FMMS.components = FMMS.components || {};
  FMMS.components.toast = { render: renderToastHost };
})(window.FMMS);
