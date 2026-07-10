/**
 * FMMS Demo — runtime configuration
 * -----------------------------------
 * This is the ONLY file that should contain the backend base URL or the
 * demo-mode switch. Every other file reads from window.FMMS_CONFIG.
 *
 * To connect this demo to a real backend:
 *   1. Set API_BASE_URL to the real API root (must include /api/v1).
 *   2. Set DEMO_MODE to false.
 * Nothing else in the codebase needs to change — js/api.js already speaks
 * the real FMMS REST contract (see FMMS_API.yaml).
 */
window.FMMS_CONFIG = {
  API_BASE_URL: "http://localhost:8000/api/v1",
  // DEMO_MODE=true uses mock data; false connects to FMMS_CONFIG.API_BASE_URL
  DEMO_MODE: false,
};
