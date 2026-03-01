import { initializeAnomalyView, preloadAnomaly } from "./anomaly-view.js?v=__BUILD_VERSION__";

function getInitialAnomalyFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("anomaly");
}

async function start() {
  try {
    await initializeAnomalyView();
    const initial = getInitialAnomalyFromUrl();
    if (initial) {
      await preloadAnomaly(initial);
    }
  } catch (error) {
    const panel = document.getElementById("status-panel");
    if (panel) {
      panel.textContent = `Startup failed: ${error.message}`;
      panel.className = "status-panel error";
    }
    throw error;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  void start();
});
