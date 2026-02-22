import { getAnomalyChain, getAnomaly, loadDataset, loadManifest, resolveImage } from "./data-client.js";
import { setLocale, t, getLocale } from "./i18n.js";

function byId(id) {
  return document.getElementById(id);
}

function clearNode(node) {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

function createImage(url, alt) {
  if (!url) {
    return null;
  }
  const img = document.createElement("img");
  img.src = url;
  img.alt = alt;
  img.loading = "lazy";
  return img;
}

function setStatus(message, level = "info") {
  const panel = byId("status-panel");
  panel.textContent = message || "";
  panel.className = `status-panel ${level}`;
}

async function renderAnomalyPanel(anomaly) {
  const panel = byId("anomaly-panel");
  clearNode(panel);

  const title = document.createElement("h2");
  title.textContent = `Anomaly: ${anomaly.id}`;
  panel.appendChild(title);

  const desc = document.createElement("p");
  desc.textContent = t(anomaly.desc_key);
  panel.appendChild(desc);

  const imageUrl = anomaly.image_asset ? `../assets/${anomaly.image_asset}` : await resolveImage(anomaly.picture_gfx);
  const image = createImage(imageUrl, anomaly.id);
  if (image) {
    panel.appendChild(image);
  }
}

async function renderEventsPanel(eventRecords) {
  const panel = byId("events-panel");
  clearNode(panel);

  const title = document.createElement("h2");
  title.textContent = `Events (${eventRecords.length})`;
  panel.appendChild(title);

  for (const eventRecord of eventRecords) {
    const card = document.createElement("article");
    card.className = "card";

    const heading = document.createElement("h3");
    heading.textContent = `${eventRecord.id} - ${t(eventRecord.title_key)}`;
    card.appendChild(heading);

    const descBlock = document.createElement("p");
    const descLines = (eventRecord.desc_keys || []).map((key) => t(key)).filter(Boolean);
    descBlock.textContent = descLines.join(" ");
    card.appendChild(descBlock);

    const optionKeys = eventRecord.option_name_keys || [];
    if (optionKeys.length > 0) {
      const optionsLabel = document.createElement("p");
      optionsLabel.className = "meta";
      optionsLabel.textContent = `Options: ${optionKeys.map((key) => t(key)).join(" | ")}`;
      card.appendChild(optionsLabel);
    }

    const gfxCandidates = eventRecord.picture_gfx_candidates || [];
    if (gfxCandidates.length > 0) {
      const url = await resolveImage(gfxCandidates[0]);
      const image = createImage(url, eventRecord.id);
      if (image) {
        card.appendChild(image);
      }
    }

    panel.appendChild(card);
  }
}

async function renderArcSitesPanel(arcSites) {
  const panel = byId("arc-sites-panel");
  clearNode(panel);

  const title = document.createElement("h2");
  title.textContent = `Linked Archaeological Sites (${arcSites.length})`;
  panel.appendChild(title);

  for (const site of arcSites) {
    const card = document.createElement("article");
    card.className = "card";

    const heading = document.createElement("h3");
    heading.textContent = site.id;
    card.appendChild(heading);

    const desc = document.createElement("p");
    const descLines = (site.desc_keys || []).map((key) => t(key)).filter(Boolean);
    desc.textContent = descLines.join(" ");
    card.appendChild(desc);

    const stages = document.createElement("ul");
    stages.className = "stage-list";
    for (const stage of site.stages || []) {
      const item = document.createElement("li");
      item.textContent = `Stage ${stage.stage_index}: event=${stage.event_id || "n/a"} difficulty=${stage.difficulty || "?"}`;
      stages.appendChild(item);
    }
    card.appendChild(stages);

    const imageUrl = site.image_asset ? `../assets/${site.image_asset}` : await resolveImage(site.picture_gfx);
    const image = createImage(imageUrl, site.id);
    if (image) {
      card.appendChild(image);
    }

    panel.appendChild(card);
  }
}

async function renderChain(anomalyId) {
  const chain = await getAnomalyChain(anomalyId);
  if (!chain) {
    setStatus(`No anomaly found for id: ${anomalyId}`, "warn");
    return;
  }

  await renderAnomalyPanel(chain.anomaly);
  await renderEventsPanel(chain.events || []);
  await renderArcSitesPanel(chain.arc_sites || []);
  setStatus(`Loaded ${chain.anomaly.id} with ${chain.events.length} events.`, "ok");
}

async function onLoadAnomalyClick() {
  const input = byId("anomaly-id-input");
  const anomalyId = (input.value || "").trim();
  if (!anomalyId) {
    setStatus("Enter an anomaly id first.", "warn");
    return;
  }
  setStatus("Loading chain...", "info");
  try {
    await renderChain(anomalyId);
  } catch (error) {
    setStatus(`Chain load failed: ${error.message}`, "error");
  }
}

async function onLocaleChange() {
  const select = byId("locale-select");
  await setLocale(select.value);

  const input = byId("anomaly-id-input");
  const currentId = (input.value || "").trim();
  if (currentId) {
    await renderChain(currentId);
  }

  setStatus(`Language set to ${getLocale()}.`, "info");
}

export async function initializeAnomalyView() {
  const manifest = await loadManifest();
  const anomalies = await loadDataset("anomalies");

  const meta = byId("manifest-meta");
  meta.textContent = `build=${manifest.build_id} schema=${manifest.schema_version}`;

  const localeSelect = byId("locale-select");
  clearNode(localeSelect);
  for (const locale of manifest.locales || []) {
    const option = document.createElement("option");
    option.value = locale;
    option.textContent = locale;
    if (locale === manifest.default_locale) {
      option.selected = true;
    }
    localeSelect.appendChild(option);
  }

  await setLocale(manifest.default_locale || "l_english");

  const datalist = byId("anomaly-id-list");
  clearNode(datalist);
  for (const anomalyId of Object.keys(anomalies).sort()) {
    const option = document.createElement("option");
    option.value = anomalyId;
    datalist.appendChild(option);
  }

  byId("load-anomaly-button").addEventListener("click", onLoadAnomalyClick);
  byId("locale-select").addEventListener("change", onLocaleChange);

  setStatus("Ready. Select an anomaly id and click Load Chain.", "info");
}

export async function preloadAnomaly(anomalyId) {
  const anomaly = await getAnomaly(anomalyId);
  if (anomaly) {
    byId("anomaly-id-input").value = anomalyId;
    await renderChain(anomalyId);
  }
}
