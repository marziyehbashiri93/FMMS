/**
 * FMMS Demo Frontend — API client.
 * All HTTP calls use FMMS_CONFIG.API_BASE_URL only.
 */
(function (global) {
  "use strict";

  var debugState = {
    authenticated: false,
    baseUrl: "",
    lastMethod: "",
    lastPath: "",
    lastStatus: null,
    lastResponse: null,
    lastError: null,
  };

  function getConfig() {
    if (!global.FMMS_CONFIG || !global.FMMS_CONFIG.API_BASE_URL) {
      throw new Error("تنظیمات API در config/env.js موجود نیست");
    }
    return global.FMMS_CONFIG;
  }

  function getToken() {
    return sessionStorage.getItem("fmms_access_token") || "";
  }

  function setTokens(access, refresh) {
    if (access) sessionStorage.setItem("fmms_access_token", access);
    if (refresh) sessionStorage.setItem("fmms_refresh_token", refresh);
    debugState.authenticated = Boolean(access);
  }

  function clearTokens() {
    sessionStorage.removeItem("fmms_access_token");
    sessionStorage.removeItem("fmms_refresh_token");
    debugState.authenticated = false;
  }

  function updateDebug(patch) {
    Object.assign(debugState, patch || {});
    debugState.baseUrl = getConfig().API_BASE_URL;
    debugState.authenticated = Boolean(getToken());
  }

  async function request(method, path, body, query) {
    var config = getConfig();
    var url = config.API_BASE_URL.replace(/\/$/, "") + path;
    if (query && typeof query === "object") {
      var params = new URLSearchParams();
      Object.keys(query).forEach(function (key) {
        if (query[key] !== undefined && query[key] !== null && query[key] !== "") {
          params.append(key, String(query[key]));
        }
      });
      var qs = params.toString();
      if (qs) url += (url.indexOf("?") >= 0 ? "&" : "?") + qs;
    }

    var headers = {
      Accept: "application/json",
      "Content-Type": "application/json",
    };
    var token = getToken();
    if (token) headers.Authorization = "Bearer " + token;

    updateDebug({
      lastMethod: method,
      lastPath: path,
      lastStatus: null,
      lastResponse: null,
      lastError: null,
    });

    var options = { method: method, headers: headers };
    if (body !== undefined && body !== null) {
      options.body = JSON.stringify(body);
    }

    var response;
    try {
      response = await fetch(url, options);
    } catch (err) {
      updateDebug({
        lastError: "خطای شبکه: " + String(err.message || err),
      });
      throw new Error("اتصال به سرویس برقرار نشد");
    }

    var payload = null;
    var text = await response.text();
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch (err) {
        payload = { raw: text };
      }
    }

    updateDebug({
      lastStatus: response.status,
      lastResponse: payload,
    });

    if (!response.ok) {
      var message =
        (payload && (payload.message || payload.detail || payload.error_code)) ||
        "خطای سرویس (" + response.status + ")";
      updateDebug({ lastError: String(message) });
      var error = new Error(String(message));
      error.status = response.status;
      error.payload = payload;
      throw error;
    }

    return payload;
  }

  function pageResults(payload) {
    if (!payload) return [];
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload.results)) return payload.results;
    return [];
  }

  var api = {
    getConfig: getConfig,
    getDebugState: function () {
      debugState.baseUrl = getConfig().API_BASE_URL;
      debugState.authenticated = Boolean(getToken());
      return Object.assign({}, debugState);
    },
    setTokens: setTokens,
    clearTokens: clearTokens,
    getToken: getToken,
    pageResults: pageResults,

    login: function (email, password) {
      return request("POST", "/auth/token/", {
        email: email,
        password: password,
      }).then(function (data) {
        setTokens(data.access, data.refresh);
        return data;
      });
    },

    listVehicles: function (query) {
      return request("GET", "/vehicles/", null, query || {});
    },

    getVehicle: function (id) {
      return request("GET", "/vehicles/" + id + "/");
    },

    deactivateVehicle: function (vehicleId) {
      return request("POST", "/vehicles/" + vehicleId + "/deactivate/", {});
    },

    listInspectionTemplates: function () {
      return request("GET", "/inspection-templates/");
    },

    createInspection: function (payload) {
      return request("POST", "/inspections/", payload);
    },

    submitInspection: function (inspectionId) {
      return request("POST", "/inspections/" + inspectionId + "/submit/", {});
    },

    listFaults: function (query) {
      return request("GET", "/faults/", null, query || {});
    },

    listOpenFaults: async function () {
      var direct = pageResults(await request("GET", "/faults/", null, {}));
      if (direct.length) {
        return direct;
      }

      var severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
      var all = [];
      var seen = {};
      for (var i = 0; i < severities.length; i++) {
        var page = await request("GET", "/faults/", null, {
          open_by_severity: severities[i],
        });
        pageResults(page).forEach(function (fault) {
          if (!seen[fault.id]) {
            seen[fault.id] = true;
            all.push(fault);
          }
        });
      }
      return all;
    },

    getFault: function (id) {
      return request("GET", "/faults/" + id + "/");
    },

    closeFault: function (faultId) {
      return request("POST", "/faults/" + faultId + "/close/", {});
    },

    listRepairOrders: function (vehicleId, status) {
      return request("GET", "/repair-orders/", null, {
        vehicle_id: vehicleId,
        status: status || undefined,
      });
    },

    getRepairOrder: function (id) {
      return request("GET", "/repair-orders/" + id + "/");
    },

    approveRepairOrder: function (orderId) {
      return request("POST", "/repair-orders/" + orderId + "/approve/", {});
    },

    assignWorkshop: function (orderId, workshopType) {
      return request("POST", "/repair-orders/" + orderId + "/assign-workshop/", {
        workshop_type: workshopType,
      });
    },
  };

  global.FMMSApi = api;
})(window);
