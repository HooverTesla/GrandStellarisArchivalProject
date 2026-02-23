import { getAnomalyChain, getAnomaly, loadDataset, loadManifest, resolveImage } from "./data-client.js";
import { setLocale, t, getLocale } from "./i18n.js";

const state = {
  anomalies: {},
  events: {},
  arcSites: {},
  reverseEventToSources: {},
  searchIndex: [],
  searchLookup: new Map(),
  activeTechTab: "all",
  activeModule: "home",
};

const modulePanelMap = {
  home: "module-home",
  tech: "module-tech",
  anomalies: "module-anomalies",
  events: "module-events",
  "arc-sites": "module-arc-sites",
  "astral-rifts": "module-astral-rifts",
};

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

function normalize(text) {
  return String(text || "").toLowerCase();
}

function localize(key) {
  if (!key) {
    return "";
  }
  const value = t(key);
  return value && value !== key ? value : "";
}

function getEventTitle(eventRecord) {
  if (!eventRecord) {
    return "";
  }
  const titled = localize(eventRecord.title_key);
  if (titled) {
    return titled;
  }
  const fallbackKey = `${eventRecord.id}.name`;
  return localize(fallbackKey) || eventRecord.id;
}

function getEventDescriptionLines(eventRecord) {
  if (!eventRecord) {
    return [];
  }
  const keys = eventRecord.desc_keys || [];
  const localized = keys.map((key) => localize(key)).filter(Boolean);
  return localized.length > 0 ? localized : keys;
}

function getAnomalyTitle(anomaly) {
  if (!anomaly) {
    return "";
  }

  const named = localize(anomaly.name_key) || localize(anomaly.title_key) || localize(anomaly.id);
  if (named) {
    return named;
  }

  for (const eventId of anomaly.event_ids || []) {
    const eventTitle = getEventTitle(state.events[eventId]);
    if (eventTitle && eventTitle !== eventId) {
      return eventTitle;
    }
  }

  return anomaly.id;
}

function setAnomalySelection(anomalyId) {
  const select = byId("anomaly-select");
  if (!select) {
    return;
  }
  if (anomalyId && Object.prototype.hasOwnProperty.call(state.anomalies, anomalyId)) {
    select.value = anomalyId;
    return;
  }
  if (select.options.length > 0) {
    select.selectedIndex = 0;
  }
}

function setModule(moduleId) {
  const resolved = Object.prototype.hasOwnProperty.call(modulePanelMap, moduleId) ? moduleId : "home";
  state.activeModule = resolved;

  const moduleTabs = document.querySelectorAll(".module-tab");
  for (const tab of moduleTabs) {
    tab.classList.toggle("is-active", tab.dataset.module === resolved);
  }

  for (const [key, panelId] of Object.entries(modulePanelMap)) {
    const panel = byId(panelId);
    if (!panel) {
      continue;
    }
    panel.classList.toggle("is-active", key === resolved);
  }

  const techSubnav = byId("tech-subnav");
  if (techSubnav) {
    techSubnav.classList.toggle("is-hidden", resolved !== "tech");
  }

  if (resolved === "tech" && window.WebUISttNative && typeof window.WebUISttNative.ensureInitialized === "function") {
    window.WebUISttNative.ensureInitialized();
  }
}

function setupModuleTabs() {
  const moduleTabs = document.querySelectorAll(".module-tab");
  for (const tab of moduleTabs) {
    tab.addEventListener("click", () => {
      const moduleId = tab.dataset.module || "home";
      setModule(moduleId);

      if (moduleId === "tech" && window.WebUISttNative && typeof window.WebUISttNative.setTab === "function") {
        window.WebUISttNative.setTab(state.activeTechTab);
        const searchInput = byId("global-search");
        if (searchInput) {
          mirrorSearchToTech(searchInput.value || "");
        }
      }
    });
  }
}

async function renderAnomalyPanel(anomaly) {
  const panel = byId("anomaly-panel");
  clearNode(panel);

  const title = document.createElement("h2");
  title.textContent = `Anomaly: ${getAnomalyTitle(anomaly)}`;
  panel.appendChild(title);

  const idMeta = document.createElement("p");
  idMeta.className = "meta";
  idMeta.textContent = anomaly.id;
  panel.appendChild(idMeta);

  const desc = document.createElement("p");
  desc.textContent = localize(anomaly.desc_key) || anomaly.desc_key || "No localized anomaly description found.";
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

  if (eventRecords.length === 0) {
    const empty = document.createElement("p");
    empty.className = "meta";
    empty.textContent = "No linked events.";
    panel.appendChild(empty);
    return;
  }

  for (const eventRecord of eventRecords) {
    const card = document.createElement("article");
    card.className = "card";

    const heading = document.createElement("h3");
    heading.textContent = getEventTitle(eventRecord);
    card.appendChild(heading);

    const idMeta = document.createElement("p");
    idMeta.className = "meta";
    idMeta.textContent = eventRecord.id;
    card.appendChild(idMeta);

    const descBlock = document.createElement("p");
    descBlock.textContent = getEventDescriptionLines(eventRecord).join(" ");
    card.appendChild(descBlock);

    const optionKeys = eventRecord.option_name_keys || [];
    if (optionKeys.length > 0) {
      const optionsLabel = document.createElement("p");
      optionsLabel.className = "meta";
      optionsLabel.textContent = `Options: ${optionKeys.map((key) => localize(key) || key).join(" | ")}`;
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

  if (arcSites.length === 0) {
    const empty = document.createElement("p");
    empty.className = "meta";
    empty.textContent = "No linked archaeological sites.";
    panel.appendChild(empty);
    return;
  }

  for (const site of arcSites) {
    const card = document.createElement("article");
    card.className = "card";

    const heading = document.createElement("h3");
    heading.textContent = localize(site.id) || site.id;
    card.appendChild(heading);

    const idMeta = document.createElement("p");
    idMeta.className = "meta";
    idMeta.textContent = site.id;
    card.appendChild(idMeta);

    const desc = document.createElement("p");
    const descLines = (site.desc_keys || []).map((key) => localize(key) || key);
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
    return false;
  }

  await renderAnomalyPanel(chain.anomaly);
  await renderEventsPanel(chain.events || []);
  await renderArcSitesPanel(chain.arc_sites || []);
  setStatus(`Loaded ${getAnomalyTitle(chain.anomaly)} (${chain.anomaly.id}) with ${chain.events.length} events.`, "ok");
  return true;
}

function resolveEventSources(eventId, maxNodes = 800) {
  const queue = [eventId];
  const visited = new Set();
  const anomalyIds = new Set();
  const arcSiteIds = new Set();

  while (queue.length > 0 && visited.size < maxNodes) {
    const current = queue.shift();
    if (!current || visited.has(current)) {
      continue;
    }
    visited.add(current);

    const source = state.reverseEventToSources[current];
    if (!source) {
      continue;
    }

    for (const anomalyId of source.from_anomalies || []) {
      anomalyIds.add(anomalyId);
    }
    for (const siteId of source.from_arc_sites || []) {
      arcSiteIds.add(siteId);
    }
    for (const parentEventId of source.from_events || []) {
      if (!visited.has(parentEventId)) {
        queue.push(parentEventId);
      }
    }
  }

  return {
    anomalyIds: [...anomalyIds].sort(),
    arcSiteIds: [...arcSiteIds].sort(),
  };
}

async function renderEventOnly(eventId, arcSiteIds = []) {
  const eventRecord = state.events[eventId];
  if (!eventRecord) {
    setStatus(`No event found for id: ${eventId}`, "warn");
    return;
  }

  const anomalyPanel = byId("anomaly-panel");
  clearNode(anomalyPanel);

  const title = document.createElement("h2");
  title.textContent = "Event Match";
  anomalyPanel.appendChild(title);

  const body = document.createElement("p");
  body.textContent = `No direct anomaly source was found for ${eventId}. Showing event data only.`;
  anomalyPanel.appendChild(body);

  await renderEventsPanel([eventRecord]);

  const linkedArcSites = arcSiteIds.map((siteId) => state.arcSites[siteId]).filter(Boolean);
  await renderArcSitesPanel(linkedArcSites);
  setStatus(`Loaded event ${eventId} without a direct anomaly source.`, "warn");
}

function buildSearchIndex() {
  state.searchIndex = [];
  state.searchLookup.clear();

  for (const anomaly of Object.values(state.anomalies)) {
    const title = getAnomalyTitle(anomaly);
    const desc = localize(anomaly.desc_key) || anomaly.desc_key || "";
    const eventIds = anomaly.event_ids || [];
    const eventTitles = eventIds.map((eventId) => getEventTitle(state.events[eventId])).join(" ");
    const display = `Anomaly: ${title} (${anomaly.id})`;
    const searchText = normalize([
      anomaly.id,
      title,
      desc,
      anomaly.desc_key || "",
      eventIds.join(" "),
      eventTitles,
    ].join(" "));

    const record = {
      type: "anomaly",
      id: anomaly.id,
      title,
      display,
      idNorm: normalize(anomaly.id),
      titleNorm: normalize(title),
      searchText,
    };
    state.searchIndex.push(record);
  }

  for (const eventRecord of Object.values(state.events)) {
    const title = getEventTitle(eventRecord);
    const desc = getEventDescriptionLines(eventRecord).join(" ");
    const optionText = (eventRecord.option_name_keys || []).map((key) => localize(key) || key).join(" ");
    const display = `Event: ${title} (${eventRecord.id})`;
    const searchText = normalize([
      eventRecord.id,
      title,
      eventRecord.title_key || "",
      desc,
      (eventRecord.desc_keys || []).join(" "),
      (eventRecord.option_name_keys || []).join(" "),
      optionText,
      eventRecord.event_type || "",
    ].join(" "));

    const record = {
      type: "event",
      id: eventRecord.id,
      title,
      display,
      idNorm: normalize(eventRecord.id),
      titleNorm: normalize(title),
      searchText,
    };
    state.searchIndex.push(record);
  }

  for (const arcSite of Object.values(state.arcSites)) {
    const title = localize(arcSite.id) || arcSite.id;
    const desc = (arcSite.desc_keys || []).map((key) => localize(key) || key).join(" ");
    const display = `Archaeological Site: ${title} (${arcSite.id})`;
    const searchText = normalize([
      arcSite.id,
      title,
      desc,
      (arcSite.desc_keys || []).join(" "),
      (arcSite.stages || []).map((stage) => stage.event_id || "").join(" "),
    ].join(" "));

    const record = {
      type: "arc-site",
      id: arcSite.id,
      title,
      display,
      idNorm: normalize(arcSite.id),
      titleNorm: normalize(title),
      searchText,
    };
    state.searchIndex.push(record);
  }

  const moduleEntries = [
    { id: "home", title: "Home" },
    { id: "tech", title: "Tech" },
    { id: "anomalies", title: "Anomalies" },
    { id: "events", title: "Events" },
    { id: "arc-sites", title: "Archaeological Sites" },
    { id: "astral-rifts", title: "Astral Rifts" },
  ];
  for (const entry of moduleEntries) {
    state.searchIndex.push({
      type: "module",
      id: entry.id,
      title: entry.title,
      display: `Module: ${entry.title}`,
      idNorm: normalize(entry.id),
      titleNorm: normalize(entry.title),
      searchText: normalize(`${entry.id} ${entry.title}`),
    });
  }
}

function rankSearchMatches(query, limit = 30) {
  const needle = normalize(query).trim();
  if (!needle) {
    return [];
  }

  const matches = [];
  for (const item of state.searchIndex) {
    if (!item.searchText.includes(needle)) {
      continue;
    }
    const startsWithId = item.idNorm.startsWith(needle);
    const startsWithTitle = item.titleNorm.startsWith(needle);
    const inTitle = item.titleNorm.includes(needle);
    const score = (startsWithId ? 0 : 40) + (startsWithTitle ? 0 : 20) + (inTitle ? 0 : 10);
    matches.push({ item, score });
  }

  matches.sort((a, b) => a.score - b.score || a.item.type.localeCompare(b.item.type) || a.item.id.localeCompare(b.item.id));
  return matches.slice(0, limit).map((entry) => entry.item);
}

function refreshSearchSuggestions() {
  const datalist = byId("global-search-list");
  clearNode(datalist);
  state.searchLookup.clear();

  const query = (byId("global-search").value || "").trim();
  if (!query) {
    return;
  }

  const suggestions = rankSearchMatches(query, 30);
  for (const suggestion of suggestions) {
    state.searchLookup.set(suggestion.display, suggestion);
    const option = document.createElement("option");
    option.value = suggestion.display;
    datalist.appendChild(option);
  }
}

async function searchAndLoad(query) {
  const trimmed = (query || "").trim();
  if (!trimmed) {
    setStatus("Type an anomaly or event query first.", "warn");
    return;
  }

  const directSelection = state.searchLookup.get(trimmed);
  let match = directSelection || null;

  if (!match && Object.prototype.hasOwnProperty.call(state.anomalies, trimmed)) {
    match = { type: "anomaly", id: trimmed };
  }
  if (!match && Object.prototype.hasOwnProperty.call(state.events, trimmed)) {
    match = { type: "event", id: trimmed };
  }
  if (!match) {
    const ranked = rankSearchMatches(trimmed, 1);
    match = ranked[0] || null;
  }

  if (!match) {
    setStatus(`No matching anomaly/event/site/module for "${trimmed}". Tech filtering is still applied in the Tech tab.`, "warn");
    return;
  }

  if (match.type === "module") {
    setModule(match.id);
    setStatus(`Switched to ${match.title}.`, "info");
    return;
  }

  if (match.type === "anomaly") {
    setAnomalySelection(match.id);
    setModule("anomalies");
    await renderChain(match.id);
    return;
  }

  if (match.type === "arc-site") {
    const site = state.arcSites[match.id];
    if (site) {
      setModule("arc-sites");
      await renderArcSitesPanel([site]);
      setStatus(`Loaded archaeological site ${match.id}.`, "ok");
      return;
    }
  }

  const source = resolveEventSources(match.id);
  if (source.anomalyIds.length > 0) {
    const anomalyId = source.anomalyIds[0];
    setAnomalySelection(anomalyId);
    setModule("events");
    await renderChain(anomalyId);
    setStatus(`Matched event ${match.id}. Loaded related anomaly ${anomalyId}.`, "ok");
    return;
  }

  setModule("events");
  await renderEventOnly(match.id, source.arcSiteIds);
}

function rebuildAnomalySelect(selectedId = "") {
  const select = byId("anomaly-select");
  clearNode(select);

  const items = Object.values(state.anomalies)
    .map((anomaly) => ({ id: anomaly.id, title: getAnomalyTitle(anomaly) }))
    .sort((a, b) => a.title.localeCompare(b.title) || a.id.localeCompare(b.id));

  for (const item of items) {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.title;
    select.appendChild(option);
  }

  setAnomalySelection(selectedId || (items[0] && items[0].id) || "");
}

async function onLoadAnomalyClick() {
  const anomalyId = (byId("anomaly-select").value || "").trim();
  if (!anomalyId) {
    setStatus("Select an anomaly first.", "warn");
    return;
  }
  setStatus("Loading chain...", "info");
  try {
    setModule("anomalies");
    await renderChain(anomalyId);
  } catch (error) {
    setStatus(`Chain load failed: ${error.message}`, "error");
  }
}

async function onLocaleChange() {
  const select = byId("locale-select");
  const activeAnomalyId = (byId("anomaly-select").value || "").trim();
  await setLocale(select.value);

  rebuildAnomalySelect(activeAnomalyId);
  buildSearchIndex();
  refreshSearchSuggestions();

  if (activeAnomalyId) {
    await renderChain(activeAnomalyId);
  }

  setStatus(`Language set to ${getLocale()}.`, "info");
}

function setTechSubtab(tabId) {
  state.activeTechTab = tabId;
  const buttons = document.querySelectorAll(".tech-subtab");
  for (const button of buttons) {
    button.classList.toggle("is-active", button.dataset.techTab === tabId);
  }
}

function applyTechTabToNative(tabId) {
  if (!window.WebUISttNative || typeof window.WebUISttNative.setTab !== "function") {
    return;
  }
  const mapped = tabId === "events" ? "anomalies" : tabId;
  window.WebUISttNative.setTab(mapped);
}

function mirrorSearchToTech(term) {
  if (state.activeModule !== "tech") {
    return;
  }
  if (!window.WebUISttNative || typeof window.WebUISttNative.applySearchTerm !== "function") {
    return;
  }
  window.WebUISttNative.applySearchTerm(term);
}

function setupTechSubnav() {
  const nav = byId("tech-subnav");
  if (!nav) {
    return;
  }
  const buttons = nav.querySelectorAll(".tech-subtab");

  for (const button of buttons) {
    button.addEventListener("click", () => {
      const tabId = button.dataset.techTab || "all";
      setTechSubtab(tabId);
      applyTechTabToNative(tabId);
    });
  }

  let dragging = false;
  let startX = 0;
  let startScrollLeft = 0;

  nav.addEventListener("mousedown", (event) => {
    if (event.button !== 0) {
      return;
    }
    dragging = true;
    nav.classList.add("is-dragging");
    startX = event.pageX;
    startScrollLeft = nav.scrollLeft;
  });

  window.addEventListener("mouseup", () => {
    dragging = false;
    nav.classList.remove("is-dragging");
  });

  window.addEventListener("mousemove", (event) => {
    if (!dragging) {
      return;
    }
    event.preventDefault();
    nav.scrollLeft = startScrollLeft - (event.pageX - startX);
  });

  nav.addEventListener("wheel", (event) => {
    if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) {
      return;
    }
    nav.scrollLeft += event.deltaY;
    event.preventDefault();
  }, { passive: false });
}

async function onSearchCommit() {
  const input = byId("global-search");
  await searchAndLoad(input.value || "");
}

export async function initializeAnomalyView() {
  const [manifest, anomalies, events, arcSites, reverseEventToSources] = await Promise.all([
    loadManifest(),
    loadDataset("anomalies"),
    loadDataset("events"),
    loadDataset("arcSites"),
    loadDataset("reverseEventToSources"),
  ]);

  state.anomalies = anomalies;
  state.events = events;
  state.arcSites = arcSites;
  state.reverseEventToSources = reverseEventToSources;

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
  rebuildAnomalySelect();
  buildSearchIndex();
  setupModuleTabs();
  setupTechSubnav();
  setTechSubtab("all");
  setModule("home");

  byId("load-anomaly-button").addEventListener("click", onLoadAnomalyClick);
  byId("locale-select").addEventListener("change", () => {
    void onLocaleChange();
  });
  byId("global-search").addEventListener("input", (event) => {
    refreshSearchSuggestions();
    mirrorSearchToTech(event.target.value || "");
  });
  byId("global-search").addEventListener("change", refreshSearchSuggestions);
  byId("global-search").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      void onSearchCommit();
    }
  });

  setStatus("Ready. Search anomalies, events, archaeological sites, or module tabs by ID/localized text.", "info");
}

export async function preloadAnomaly(anomalyId) {
  const anomaly = await getAnomaly(anomalyId);
  if (anomaly) {
    setAnomalySelection(anomalyId);
    setModule("anomalies");
    await renderChain(anomalyId);
  }
}
