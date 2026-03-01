import {
  getAnomalyChain,
  getArcSiteChain,
  getAstralRiftChain,
  getAnomaly,
  loadDataset,
  loadDatabankCategory,
  loadManifest,
} from "./data-client.js?v=__BUILD_VERSION__";
import { setLocale, t, getLocale } from "./i18n.js?v=__BUILD_VERSION__";

const SHORTCUT_STORAGE_KEY = "webui.shortcut.focus_search";
const DEFAULT_SHORTCUT = "Ctrl+K";
const MODULE_PANEL_MAP = {
  empire: "module-empire",
  events: "module-events",
  tech: "module-tech",
  databank: "module-databank",
  settings: "module-settings",
};

const state = {
  manifest: null,
  anomalies: {},
  events: {},
  arcSites: {},
  astralRifts: {},
  eventToEvents: {},
  databankIndex: [],
  databankCache: new Map(),
  searchIndex: [],
  searchLookup: new Map(),
  techSearchEntries: [],
  activeModule: "empire",
  activeEmpireTab: "government",
  activeEventsTab: "anomalies",
  activeTechTab: "all",
  activeAnomalyId: "",
  activeArcSiteId: "",
  activeAstralRiftId: "",
  focusedEventId: "",
  activeDatabankCategory: "",
  anomalyDlcKeys: [],
  anomalyDlcFilters: new Set(),
  shortcuts: {
    focusSearch: DEFAULT_SHORTCUT,
  },
  discoveries: {
    anomalies: new Set(),
    arc_sites: new Set(),
    astral_rifts: new Set(),
    event_chains: new Set(),
  },
  chainCache: new Map(),
};

const DISCOVERY_ORDER = [
  ["anomalies", "Anomalies"],
  ["arc_sites", "Arc Sites"],
  ["astral_rifts", "Astral Rifts"],
  ["event_chains", "Event Chains"],
];

const EVENT_CATEGORY_LABELS = {
  empire: "Empire",
  colony: "Colony",
  pre_ftl: "Pre-FTL",
  misc: "Misc",
};

const ANOMALY_SOURCE_LABELS = {
  ai: "AI",
  ancient_relics: "Ancient Relics",
  astral_planes: "Astral Planes",
  base_game: "Base Game",
  cosmic_storms: "Cosmic Storms",
  distant_stars: "Distant Stars",
  extreme_frontiers: "Extreme Frontiers",
  federations: "Federations",
  infernals: "Infernals",
  paragon: "Galactic Paragons",
  precursors: "Precursors",
  tutorial: "Tutorial",
  unplugged: "Unplugged",
};

const EVENT_TYPE_FALLBACK_IMAGE = {
  astral_rift_event: "../assets/stellaris/gfx/interface/icons/situation_log/situation_log_astral_rift.webp",
  country_event: "../assets/stellaris/gfx/interface/icons/message/message_event_generic.webp",
  event: "../assets/stellaris/gfx/interface/icons/message/message_event_generic.webp",
  espionage_operation_event: "../assets/stellaris/gfx/interface/icons/message/message_event_generic.webp",
  first_contact_event: "../assets/stellaris/gfx/interface/icons/message/message_event_generic.webp",
  fleet_event: "../assets/stellaris/gfx/interface/icons/message/message_event_generic.webp",
  leader_event: "../assets/stellaris/gfx/interface/icons/message/message_event_generic.webp",
  observer_event: "../assets/stellaris/gfx/interface/icons/message/message_event_generic.webp",
  planet_event: "../assets/stellaris/gfx/interface/icons/message/message_event_generic.webp",
  ship_event: "../assets/stellaris/gfx/interface/icons/message/message_event_generic.webp",
  situation_event: "../assets/stellaris/gfx/interface/icons/message/message_event_generic.webp",
  starbase_event: "../assets/stellaris/gfx/interface/icons/message/message_event_generic.webp",
  system_event: "../assets/stellaris/gfx/interface/icons/message/message_event_generic.webp",
};

function byId(id) {
  return document.getElementById(id);
}

function clearNode(node) {
  if (!node) {
    return;
  }
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

function asArray(value) {
  if (Array.isArray(value)) {
    return value;
  }
  if (value === null || typeof value === "undefined") {
    return [];
  }
  return [value];
}

function uniqueStrings(values) {
  const seen = new Set();
  const out = [];
  for (const value of values) {
    if (typeof value !== "string" || value.length === 0 || seen.has(value)) {
      continue;
    }
    seen.add(value);
    out.push(value);
  }
  return out;
}

function normalizeAssetPath(path) {
  if (!path || typeof path !== "string") {
    return "";
  }
  const clean = path.replace(/\\/g, "/").replace(/^\/+/, "");
  if (clean.startsWith("../") || clean.startsWith("http://") || clean.startsWith("https://")) {
    return clean;
  }
  if (clean.startsWith("assets/")) {
    return `../${clean}`;
  }
  if (clean.startsWith("stellaris/")) {
    return `../assets/${clean}`;
  }
  return clean;
}

function getPrimaryAssetPath(candidates) {
  for (const candidate of asArray(candidates)) {
    const value = normalizeAssetPath(candidate);
    if (value) {
      return value;
    }
  }
  return "";
}

function getEventImagePath(eventRecord) {
  if (!eventRecord || typeof eventRecord !== "object") {
    return "";
  }
  const eventAsset = getPrimaryAssetPath(eventRecord.picture_asset_candidates);
  if (eventAsset) {
    return eventAsset;
  }
  const typeKey = String(eventRecord.event_type || "").toLowerCase();
  return EVENT_TYPE_FALLBACK_IMAGE[typeKey] || EVENT_TYPE_FALLBACK_IMAGE.country_event;
}

function computeChainPath(chain, selectedEventId) {
  const selected = String(selectedEventId || "").trim();
  if (!selected || !chain || !Array.isArray(chain.event_edges)) {
    return { nodeIds: new Set(), edgeKeys: new Set() };
  }

  const seeds = new Set(asArray(chain.seed_event_ids).filter(Boolean));
  const reverse = new Map();
  for (const edge of chain.event_edges) {
    if (!edge || !edge.from_event_id || !edge.to_event_id) {
      continue;
    }
    if (!reverse.has(edge.to_event_id)) {
      reverse.set(edge.to_event_id, []);
    }
    reverse.get(edge.to_event_id).push(edge.from_event_id);
  }

  const queue = [[selected]];
  const visited = new Set([selected]);
  let resolvedPath = [];

  while (queue.length > 0) {
    const path = queue.shift();
    const head = path[path.length - 1];
    const previous = reverse.get(head) || [];
    if (seeds.has(head) || previous.length === 0) {
      resolvedPath = path.slice().reverse();
      break;
    }
    for (const source of previous) {
      if (visited.has(source)) {
        continue;
      }
      visited.add(source);
      queue.push(path.concat(source));
    }
  }

  if (resolvedPath.length === 0) {
    resolvedPath = [selected];
  }

  const nodeIds = new Set(resolvedPath);
  const edgeKeys = new Set();
  for (let index = 0; index < resolvedPath.length - 1; index += 1) {
    const fromId = resolvedPath[index];
    const toId = resolvedPath[index + 1];
    edgeKeys.add(`${fromId}|${toId}`);
  }
  return { nodeIds, edgeKeys };
}

function isInteractiveTarget(target) {
  return Boolean(target && target.closest("button,a,input,select,textarea,label,[role='button']"));
}

function bindRowToggle(row, toggleFn, options = {}) {
  if (!row || typeof toggleFn !== "function") {
    return;
  }
  row.classList.add("row-toggle");
  const skipCellIndex = Number.isInteger(options.skipCellIndex) ? options.skipCellIndex : -1;
  row.addEventListener("click", (event) => {
    if (isInteractiveTarget(event.target)) {
      return;
    }
    if (skipCellIndex >= 0 && row.cells[skipCellIndex] && row.cells[skipCellIndex].contains(event.target)) {
      return;
    }
    toggleFn();
  });
}

function refreshTabIconStates() {
  for (const image of document.querySelectorAll("img[data-icon]")) {
    const owner = image.closest(".module-tab, .module-subtab");
    if (!owner) {
      continue;
    }
    const normal = image.dataset.icon || image.getAttribute("src");
    const hover = image.dataset.iconHover || image.dataset.iconSelected || normal;
    const selectedHover = image.dataset.iconSelectedHover || image.dataset.iconHover || image.dataset.iconSelected || normal;
    const selected = image.dataset.iconSelected || normal;
    const isActive = owner.classList.contains("is-active");
    const isHovered = owner.matches(":hover, :focus-within");
    const nextSrc = isActive ? (isHovered ? selectedHover : selected) : (isHovered ? hover : normal);
    if (nextSrc && image.getAttribute("src") !== nextSrc) {
      image.setAttribute("src", nextSrc);
    }
  }
}

function normalize(text) {
  return String(text || "").toLowerCase();
}

function titleCase(value) {
  return String(value || "")
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function localize(key) {
  if (!key) {
    return "";
  }
  const value = t(key);
  return value && value !== key ? value : "";
}

function localizeWithFallback(key, fallback = "") {
  return localize(key) || key || fallback;
}

function getAnomalySourceKey(anomaly) {
  const source = String((anomaly && anomaly.source_file) || "").toLowerCase();
  const suffix = source.match(/anomaly_categories_([a-z0-9_]+)\.txt$/);
  if (suffix) {
    return suffix[1];
  }
  return "base_game";
}

function getAnomalySourceLabel(sourceKey) {
  return ANOMALY_SOURCE_LABELS[sourceKey] || titleCase(sourceKey);
}

function getAnomalyTitle(anomaly) {
  if (!anomaly) {
    return "";
  }
  return localize(anomaly.name_key) || localize(anomaly.title_key) || localize(anomaly.id) || anomaly.id;
}

function getArcSiteTitle(site) {
  if (!site) {
    return "";
  }
  return localize(site.id) || site.id;
}

function getAstralRiftTitle(rift) {
  if (!rift) {
    return "";
  }
  return localize(rift.name_key) || localize(rift.id) || rift.id;
}

function getEventTitle(eventRecord) {
  if (!eventRecord) {
    return "";
  }
  const title = localize(eventRecord.title_key);
  if (title) {
    return title;
  }
  return localize(`${eventRecord.id}.name`) || eventRecord.id;
}

function getEventDesc(eventRecord) {
  if (!eventRecord) {
    return "";
  }
  const keys = asArray(eventRecord.desc_keys);
  const lines = keys.map((key) => localize(key) || key).filter(Boolean);
  return lines.join(" ");
}

function setStatus(message, level = "info") {
  const panel = byId("status-panel");
  if (!panel) {
    return;
  }
  panel.textContent = message || "";
  panel.className = `status-panel ${level}`;
}

function isSaved(type, id) {
  return Boolean(state.discoveries[type] && state.discoveries[type].has(id));
}

function toggleSaved(type, id) {
  const bucket = state.discoveries[type];
  if (!bucket) {
    return;
  }
  if (bucket.has(id)) {
    bucket.delete(id);
    setStatus(`Removed bookmark: ${id}`, "info");
  } else {
    bucket.add(id);
    setStatus(`Bookmarked: ${id}`, "ok");
  }
  renderDiscoveries();
}

function createBookmarkButton(type, id) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "bookmark-button";
  button.classList.toggle("is-saved", isSaved(type, id));
  button.title = isSaved(type, id) ? "Remove From Discoveries" : "Add To Discoveries";
  button.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    toggleSaved(type, id);
    rerenderCurrentPane();
  });

  const sprite = document.createElement("span");
  sprite.className = "bookmark-sprite";
  sprite.setAttribute("aria-hidden", "true");
  button.appendChild(sprite);
  return button;
}

function setModule(moduleId) {
  const resolved = Object.prototype.hasOwnProperty.call(MODULE_PANEL_MAP, moduleId) ? moduleId : "empire";
  state.activeModule = resolved;

  for (const tab of document.querySelectorAll(".module-tab")) {
    tab.classList.toggle("is-active", tab.dataset.module === resolved);
  }
  refreshTabIconStates();

  for (const [moduleKey, panelId] of Object.entries(MODULE_PANEL_MAP)) {
    const panel = byId(panelId);
    if (panel) {
      panel.classList.toggle("is-active", moduleKey === resolved);
    }
  }

  byId("empire-subnav").classList.toggle("is-hidden", resolved !== "empire");
  byId("events-subnav").classList.toggle("is-hidden", resolved !== "events");
  byId("tech-subnav").classList.toggle("is-hidden", resolved !== "tech");

  const settingsButton = byId("settings-tab-button");
  if (settingsButton) {
    settingsButton.classList.toggle("is-active", resolved === "settings");
  }

  if (resolved === "tech" && window.WebUISttNative && typeof window.WebUISttNative.ensureInitialized === "function") {
    window.WebUISttNative.ensureInitialized();
    applyTechTabToNative(state.activeTechTab);
    applyBioshipToggle();
    mirrorSearchToTech(byId("global-search").value || "");
    refreshTierTracker();
    refreshTechSearchEntries();
  }
}

function setEmpireTab(tabId) {
  state.activeEmpireTab = tabId;
  for (const button of document.querySelectorAll("[data-empire-tab]")) {
    button.classList.toggle("is-active", button.dataset.empireTab === tabId);
  }
  refreshTabIconStates();
  byId("empire-government-panel").classList.toggle("is-active", tabId === "government");
  byId("empire-discoveries-panel").classList.toggle("is-active", tabId === "discoveries");
  byId("empire-tech-panel").classList.toggle("is-active", tabId === "tech");
}

function setEventsTab(tabId) {
  state.activeEventsTab = tabId;
  for (const button of document.querySelectorAll("[data-events-tab]")) {
    button.classList.toggle("is-active", button.dataset.eventsTab === tabId);
  }
  refreshTabIconStates();
  for (const pane of document.querySelectorAll(".events-pane")) {
    pane.classList.toggle("is-active", pane.id === `events-pane-${tabId}`);
  }
}

function setTechTab(tabId) {
  const resolvedTab = tabId === "anomalies" ? "events" : tabId;
  state.activeTechTab = resolvedTab;
  for (const button of document.querySelectorAll("[data-tech-tab]")) {
    button.classList.toggle("is-active", button.dataset.techTab === resolvedTab);
  }
  refreshTabIconStates();
}

function applyTechTabToNative(tabId) {
  if (!window.WebUISttNative || typeof window.WebUISttNative.setTab !== "function") {
    return;
  }
  const resolvedTab = tabId === "events" ? "anomalies" : tabId;
  window.WebUISttNative.setTab(resolvedTab || "all");
}

function mirrorSearchToTech(term) {
  if (state.activeModule !== "tech") {
    return;
  }
  if (!window.WebUISttNative || typeof window.WebUISttNative.applySearchTerm !== "function") {
    return;
  }
  window.WebUISttNative.applySearchTerm(term || "");
}

function applyBioshipToggle() {
  const toggle = byId("tech-bioship-toggle");
  if (!toggle || !window.WebUISttNative || typeof window.WebUISttNative.setBioshipMode !== "function") {
    return;
  }
  window.WebUISttNative.setBioshipMode(toggle.checked ? "bio" : "all");
}

function refreshTierTracker() {
  const container = byId("tech-tier-tracker");
  if (!container) {
    return;
  }
  clearNode(container);
  if (!window.WebUISttNative || typeof window.WebUISttNative.getTierSummary !== "function") {
    return;
  }
  const summary = window.WebUISttNative.getTierSummary();
  const iconPath = "../assets/stellaris/gfx/interface/anomaly/discovery_level_icon.webp";
  for (const area of ["physics", "society", "engineering"]) {
    const areaSummary = summary && summary[area];
    if (!areaSummary) {
      continue;
    }
    const chip = document.createElement("span");
    chip.className = "tier-chip";
    const icon = document.createElement("img");
    icon.src = iconPath;
    icon.alt = `${area} tier`;
    chip.appendChild(icon);
    const text = document.createElement("span");
    const tierLabel = areaSummary.current_tier > 0 ? `T${areaSummary.current_tier}` : "Starting";
    text.textContent = `${titleCase(area)} ${tierLabel} ${areaSummary.completed_in_tier}/${areaSummary.total_in_tier}`;
    chip.appendChild(text);
    container.appendChild(chip);
  }
}

function refreshTechSearchEntries() {
  if (!window.WebUISttNative || typeof window.WebUISttNative.getSearchEntries !== "function") {
    return;
  }
  state.techSearchEntries = asArray(window.WebUISttNative.getSearchEntries());
  buildSearchIndex();
}

function renderAnomalyFilters() {
  const container = byId("anomaly-dlc-filters");
  if (!container) {
    return;
  }
  clearNode(container);
  for (const sourceKey of state.anomalyDlcKeys) {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = state.anomalyDlcFilters.has(sourceKey);
    input.addEventListener("change", () => {
      if (input.checked) {
        state.anomalyDlcFilters.add(sourceKey);
      } else {
        state.anomalyDlcFilters.delete(sourceKey);
      }
      renderAnomalyTable();
    });
    const text = document.createElement("span");
    text.textContent = getAnomalySourceLabel(sourceKey);
    label.appendChild(input);
    label.appendChild(text);
    container.appendChild(label);
  }
}

function makeFlow(chain, cacheKey) {
  const wrapper = document.createElement("div");
  wrapper.className = "chain-flow";
  if (!chain || !Array.isArray(chain.events) || chain.events.length === 0) {
    const empty = document.createElement("p");
    empty.className = "meta";
    empty.textContent = "No chain data available.";
    wrapper.appendChild(empty);
    return wrapper;
  }

  const selected = state.chainCache.get(cacheKey) || "";
  const highlighted = computeChainPath(chain, selected);
  const eventMap = new Map(chain.events.map((item) => [item.id, item]));

  for (const eventRecord of chain.events) {
    const node = document.createElement("article");
    node.className = "chain-node";
    node.addEventListener("click", (event) => {
      if (isInteractiveTarget(event.target)) {
        return;
      }
      state.chainCache.set(cacheKey, eventRecord.id);
      rerenderCurrentPane();
    });
    if (highlighted.nodeIds.has(eventRecord.id)) {
      node.classList.add("is-path-node");
    }
    if (selected && selected === eventRecord.id) {
      node.classList.add("is-selected");
    }

    const header = document.createElement("div");
    header.className = "chain-node-header";
    const preview = document.createElement("img");
    preview.className = "chain-node-image";
    preview.src = getEventImagePath(eventRecord);
    preview.alt = eventRecord.event_type ? `${eventRecord.event_type} image` : "Event image";
    preview.loading = "lazy";
    preview.decoding = "async";
    header.appendChild(preview);

    const titleWrap = document.createElement("div");
    titleWrap.className = "chain-node-titlewrap";
    const title = document.createElement("h5");
    title.className = "chain-node-title";
    title.textContent = getEventTitle(eventRecord);
    const idMeta = document.createElement("p");
    idMeta.className = "chain-node-id";
    idMeta.textContent = eventRecord.id;
    titleWrap.appendChild(title);
    titleWrap.appendChild(idMeta);
    header.appendChild(titleWrap);
    node.appendChild(header);

    const desc = document.createElement("p");
    desc.className = "chain-node-desc";
    desc.textContent = getEventDesc(eventRecord) || "No localized description.";
    node.appendChild(desc);

    const options = asArray(eventRecord.options);
    if (options.length > 0) {
      const list = document.createElement("div");
      list.className = "chain-options";
      for (const option of options) {
        if (!option || typeof option !== "object") {
          continue;
        }
        const line = document.createElement("div");
        line.className = "chain-option-line";
        const idx = document.createElement("span");
        idx.className = "chain-option-index";
        idx.textContent = `#${option.index || "?"}`;
        line.appendChild(idx);

        const text = document.createElement("span");
        text.className = "chain-option-text";
        text.textContent = localize(option.name_key) || option.name_key || "Unnamed option";
        line.appendChild(text);

        const followups = uniqueStrings(asArray(option.followup_event_ids)).filter((id) => eventMap.has(id));
        if (followups.length > 0) {
          line.appendChild(document.createTextNode(" -> "));
          followups.forEach((eventId, idxPos) => {
            const jump = document.createElement("button");
            jump.type = "button";
            jump.className = "chain-path-link";
            if (selected === eventId || highlighted.edgeKeys.has(`${eventRecord.id}|${eventId}`)) {
              jump.classList.add("is-active");
            }
            jump.textContent = getEventTitle(eventMap.get(eventId));
            jump.addEventListener("click", () => {
              state.chainCache.set(cacheKey, eventId);
              rerenderCurrentPane();
            });
            line.appendChild(jump);
            if (idxPos < followups.length - 1) {
              line.appendChild(document.createTextNode(", "));
            }
          });
        }
        list.appendChild(line);
      }
      node.appendChild(list);
    }

    wrapper.appendChild(node);
  }
  return wrapper;
}

function getFilteredAnomalies() {
  return Object.values(state.anomalies)
    .filter((anomaly) => state.anomalyDlcFilters.has(getAnomalySourceKey(anomaly)))
    .sort((a, b) => getAnomalyTitle(a).localeCompare(getAnomalyTitle(b)) || a.id.localeCompare(b.id));
}

async function renderAnomalyTable() {
  const tbody = byId("anomaly-table-body");
  if (!tbody) {
    return;
  }
  clearNode(tbody);

  const anomalies = getFilteredAnomalies();
  if (anomalies.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.className = "meta";
    cell.textContent = "No anomalies match the current filter.";
    row.appendChild(cell);
    tbody.appendChild(row);
    return;
  }

  for (const anomaly of anomalies) {
    const row = document.createElement("tr");
    const toggleAnomaly = () => {
      state.activeAnomalyId = state.activeAnomalyId === anomaly.id ? "" : anomaly.id;
      void renderAnomalyTable();
    };

    const saveCell = document.createElement("td");
    saveCell.appendChild(createBookmarkButton("anomalies", anomaly.id));
    row.appendChild(saveCell);

    const titleCell = document.createElement("td");
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "collapsible-toggle";
    toggle.textContent = getAnomalyTitle(anomaly);
    toggle.addEventListener("click", toggleAnomaly);
    titleCell.appendChild(toggle);
    const sourceMeta = document.createElement("div");
    sourceMeta.className = "meta";
    sourceMeta.textContent = getAnomalySourceLabel(getAnomalySourceKey(anomaly));
    titleCell.appendChild(sourceMeta);
    row.appendChild(titleCell);

    const levelCell = document.createElement("td");
    levelCell.textContent = String(anomaly.level || "?");
    row.appendChild(levelCell);

    const uniqueCell = document.createElement("td");
    uniqueCell.textContent = anomaly.max_once || anomaly.max_once_global ? "Unique" : "Repeatable";
    row.appendChild(uniqueCell);

    const eventsCell = document.createElement("td");
    eventsCell.textContent = String(asArray(anomaly.event_ids).length);
    row.appendChild(eventsCell);
    bindRowToggle(row, toggleAnomaly, { skipCellIndex: 0 });
    tbody.appendChild(row);

    if (state.activeAnomalyId === anomaly.id) {
      const detailRow = document.createElement("tr");
      const detailCell = document.createElement("td");
      detailCell.colSpan = 5;
      const chainHolder = document.createElement("div");
      chainHolder.className = "chain-card-body";
      chainHolder.textContent = "Loading anomaly chain...";
      detailCell.appendChild(chainHolder);
      detailRow.appendChild(detailCell);
      tbody.appendChild(detailRow);

      const chain = await getAnomalyChain(anomaly.id);
      clearNode(chainHolder);
      const summary = document.createElement("p");
      summary.className = "meta";
      summary.textContent = `${getAnomalyTitle(anomaly)} (${anomaly.id})`;
      chainHolder.appendChild(summary);
      const desc = document.createElement("p");
      desc.textContent = localize(anomaly.desc_key) || anomaly.desc_key || "No localized description.";
      chainHolder.appendChild(desc);
      chainHolder.appendChild(makeFlow(chain, `anomaly:${anomaly.id}`));
    }
  }
}
async function renderArcSiteTable() {
  const tbody = byId("arc-sites-table-body");
  if (!tbody) {
    return;
  }
  clearNode(tbody);
  const sites = Object.values(state.arcSites).sort((a, b) => getArcSiteTitle(a).localeCompare(getArcSiteTitle(b)) || a.id.localeCompare(b.id));

  for (const site of sites) {
    const row = document.createElement("tr");
    const toggleSite = () => {
      state.activeArcSiteId = state.activeArcSiteId === site.id ? "" : site.id;
      void renderArcSiteTable();
    };

    const saveCell = document.createElement("td");
    saveCell.appendChild(createBookmarkButton("arc_sites", site.id));
    row.appendChild(saveCell);

    const titleCell = document.createElement("td");
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "collapsible-toggle";
    toggle.textContent = getArcSiteTitle(site);
    toggle.addEventListener("click", toggleSite);
    titleCell.appendChild(toggle);
    row.appendChild(titleCell);

    const rewardsCell = document.createElement("td");
    rewardsCell.textContent = `${asArray(site.stages).length} stage rewards`;
    row.appendChild(rewardsCell);

    const spawnCell = document.createElement("td");
    spawnCell.textContent = site.source_file || "Data unavailable";
    row.appendChild(spawnCell);

    bindRowToggle(row, toggleSite, { skipCellIndex: 0 });
    tbody.appendChild(row);

    if (state.activeArcSiteId === site.id) {
      const detailRow = document.createElement("tr");
      const detailCell = document.createElement("td");
      detailCell.colSpan = 4;
      const chainHolder = document.createElement("div");
      chainHolder.className = "chain-card-body";
      chainHolder.textContent = "Loading arc site chain...";
      detailCell.appendChild(chainHolder);
      detailRow.appendChild(detailCell);
      tbody.appendChild(detailRow);

      const chain = await getArcSiteChain(site.id);
      clearNode(chainHolder);
      const summary = document.createElement("p");
      summary.className = "meta";
      summary.textContent = `${getArcSiteTitle(site)} (${site.id})`;
      chainHolder.appendChild(summary);
      chainHolder.appendChild(makeFlow(chain, `arc:${site.id}`));
    }
  }
}

async function renderAstralRiftTable() {
  const tbody = byId("astral-rifts-table-body");
  if (!tbody) {
    return;
  }
  clearNode(tbody);
  const rifts = Object.values(state.astralRifts).sort((a, b) => getAstralRiftTitle(a).localeCompare(getAstralRiftTitle(b)) || a.id.localeCompare(b.id));

  for (const rift of rifts) {
    const row = document.createElement("tr");
    const toggleRift = () => {
      state.activeAstralRiftId = state.activeAstralRiftId === rift.id ? "" : rift.id;
      void renderAstralRiftTable();
    };

    const saveCell = document.createElement("td");
    saveCell.appendChild(createBookmarkButton("astral_rifts", rift.id));
    row.appendChild(saveCell);

    const titleCell = document.createElement("td");
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "collapsible-toggle";
    toggle.textContent = getAstralRiftTitle(rift);
    toggle.addEventListener("click", toggleRift);
    titleCell.appendChild(toggle);
    row.appendChild(titleCell);

    const outcomesCell = document.createElement("td");
    outcomesCell.textContent = `${asArray(rift.event_ids).length} known chain events`;
    row.appendChild(outcomesCell);

    const flagsCell = document.createElement("td");
    const rewards = asArray(rift.relic_rewards).map((reward) => localize(reward) || reward);
    flagsCell.textContent = rewards.length > 0 ? rewards.join(", ") : asArray(rift.flags).join(", ") || "None";
    row.appendChild(flagsCell);

    bindRowToggle(row, toggleRift, { skipCellIndex: 0 });
    tbody.appendChild(row);

    if (state.activeAstralRiftId === rift.id) {
      const detailRow = document.createElement("tr");
      const detailCell = document.createElement("td");
      detailCell.colSpan = 4;
      const chainHolder = document.createElement("div");
      chainHolder.className = "chain-card-body";
      chainHolder.textContent = "Loading astral rift chain...";
      detailCell.appendChild(chainHolder);
      detailRow.appendChild(detailCell);
      tbody.appendChild(detailRow);

      const chain = await getAstralRiftChain(rift.id);
      clearNode(chainHolder);
      const summary = document.createElement("p");
      summary.className = "meta";
      summary.textContent = `${getAstralRiftTitle(rift)} (${rift.id})`;
      chainHolder.appendChild(summary);
      if (rewards.length > 0) {
        const rewardLine = document.createElement("p");
        rewardLine.className = "meta";
        rewardLine.textContent = `Potential rewards: ${rewards.join(", ")}`;
        chainHolder.appendChild(rewardLine);
      }
      chainHolder.appendChild(makeFlow(chain, `rift:${rift.id}`));
    }
  }
}

function buildEventListByCategory(category) {
  return Object.values(state.events)
    .filter((eventRecord) => {
      if (!eventRecord || eventRecord.event_category !== category) {
        return false;
      }
      const source = String(eventRecord.source_file || "").toLowerCase();
      return !source.includes("anomaly_events");
    })
    .sort((a, b) => getEventTitle(a).localeCompare(getEventTitle(b)) || a.id.localeCompare(b.id));
}

function buildEventChainFromSeed(seedEventId) {
  const seedNamespace = String(seedEventId || "").split(".")[0];
  const queue = [{ id: seedEventId, depth: 0 }];
  const visited = new Set();
  while (queue.length > 0 && visited.size < 120) {
    const current = queue.shift();
    if (!current || !current.id || visited.has(current.id)) {
      continue;
    }
    visited.add(current.id);
    if (current.depth >= 14) {
      continue;
    }
    const currentNamespace = String(current.id).split(".")[0];
    for (const nextId of asArray(state.eventToEvents[current.id])) {
      if (typeof nextId !== "string" || visited.has(nextId)) {
        continue;
      }
      const nextNamespace = String(nextId).split(".")[0];
      if (nextNamespace !== currentNamespace && nextNamespace !== seedNamespace) {
        continue;
      }
      queue.push({ id: nextId, depth: current.depth + 1 });
    }
  }
  const eventIds = [...visited].sort();
  return {
    event_ids: eventIds,
    events: eventIds.map((id) => state.events[id]).filter(Boolean),
  };
}

function renderEventsPanel() {
  const container = byId("events-categories");
  if (!container) {
    return;
  }
  clearNode(container);

  if (state.focusedEventId && state.events[state.focusedEventId]) {
    const focused = document.createElement("section");
    focused.className = "event-category-section";
    const heading = document.createElement("h3");
    heading.className = "event-category-header";
    heading.textContent = `Focused Event: ${state.focusedEventId}`;
    focused.appendChild(heading);
    const body = document.createElement("div");
    body.className = "event-category-body";
    body.appendChild(createBookmarkButton("event_chains", state.focusedEventId));
    body.appendChild(makeFlow(buildEventChainFromSeed(state.focusedEventId), `event:${state.focusedEventId}`));
    focused.appendChild(body);
    container.appendChild(focused);
  }

  for (const category of ["empire", "colony", "pre_ftl", "misc"]) {
    const events = buildEventListByCategory(category);
    const section = document.createElement("section");
    section.className = "event-category-section";
    const heading = document.createElement("h3");
    heading.className = "event-category-header";
    heading.textContent = `${EVENT_CATEGORY_LABELS[category]} (${events.length})`;
    section.appendChild(heading);

    const body = document.createElement("div");
    body.className = "event-category-body";
    for (const eventRecord of events.slice(0, 24)) {
      const card = document.createElement("article");
      card.className = "chain-card";
      card.addEventListener("click", (event) => {
        if (isInteractiveTarget(event.target)) {
          return;
        }
        state.focusedEventId = eventRecord.id;
        renderEventsPanel();
      });
      const header = document.createElement("div");
      header.className = "chain-card-header";
      const left = document.createElement("div");
      const title = document.createElement("h4");
      title.textContent = getEventTitle(eventRecord);
      const idMeta = document.createElement("p");
      idMeta.className = "chain-card-meta";
      idMeta.textContent = eventRecord.id;
      left.appendChild(title);
      left.appendChild(idMeta);
      header.appendChild(left);

      const right = document.createElement("div");
      right.appendChild(createBookmarkButton("event_chains", eventRecord.id));
      const open = document.createElement("button");
      open.type = "button";
      open.className = "inline-button";
      open.textContent = "Open";
      open.addEventListener("click", () => {
        state.focusedEventId = eventRecord.id;
        renderEventsPanel();
      });
      right.appendChild(open);
      header.appendChild(right);

      card.appendChild(header);
      body.appendChild(card);
    }
    section.appendChild(body);
    container.appendChild(section);
  }
}

function resolveDiscoveryTitle(type, id) {
  if (type === "anomalies") {
    return getAnomalyTitle(state.anomalies[id]) || id;
  }
  if (type === "arc_sites") {
    return getArcSiteTitle(state.arcSites[id]) || id;
  }
  if (type === "astral_rifts") {
    return getAstralRiftTitle(state.astralRifts[id]) || id;
  }
  if (type === "event_chains") {
    return getEventTitle(state.events[id]) || id;
  }
  return id;
}

function openDiscovery(type, id) {
  if (type === "anomalies") {
    setModule("events");
    setEventsTab("anomalies");
    state.activeAnomalyId = id;
    void renderAnomalyTable();
    return;
  }
  if (type === "arc_sites") {
    setModule("events");
    setEventsTab("arc-sites");
    state.activeArcSiteId = id;
    void renderArcSiteTable();
    return;
  }
  if (type === "astral_rifts") {
    setModule("events");
    setEventsTab("astral-rifts");
    state.activeAstralRiftId = id;
    void renderAstralRiftTable();
    return;
  }
  if (type === "event_chains") {
    setModule("events");
    setEventsTab("events");
    state.focusedEventId = id;
    renderEventsPanel();
  }
}

function renderDiscoveries() {
  const container = byId("discoveries-groups");
  if (!container) {
    return;
  }
  clearNode(container);

  for (const [type, title] of DISCOVERY_ORDER) {
    const block = document.createElement("section");
    block.className = "discoveries-group";
    const heading = document.createElement("h3");
    heading.textContent = title;
    block.appendChild(heading);

    const ids = [...state.discoveries[type]].sort();
    if (ids.length === 0) {
      const empty = document.createElement("div");
      empty.className = "discoveries-empty";
      empty.textContent = "No saved entries.";
      block.appendChild(empty);
    } else {
      const table = document.createElement("table");
      table.className = "databank-table";
      const head = document.createElement("thead");
      head.innerHTML = "<tr><th>Remove</th><th>Entry</th><th>ID</th></tr>";
      table.appendChild(head);
      const body = document.createElement("tbody");
      for (const id of ids) {
        const row = document.createElement("tr");
        const remove = document.createElement("td");
        remove.appendChild(createBookmarkButton(type, id));
        row.appendChild(remove);
        const entry = document.createElement("td");
        const jump = document.createElement("button");
        jump.type = "button";
        jump.className = "collapsible-toggle";
        jump.textContent = resolveDiscoveryTitle(type, id);
        jump.addEventListener("click", () => openDiscovery(type, id));
        entry.appendChild(jump);
        row.appendChild(entry);
        const idCell = document.createElement("td");
        idCell.textContent = id;
        row.appendChild(idCell);
        bindRowToggle(row, () => openDiscovery(type, id), { skipCellIndex: 0 });
        body.appendChild(row);
      }
      table.appendChild(body);
      block.appendChild(table);
    }

    container.appendChild(block);
  }
}

function renderDatabankLanding() {
  const tileGrid = byId("databank-tile-grid");
  if (!tileGrid) {
    return;
  }
  clearNode(tileGrid);

  const hoverList = byId("databank-hover-categories");
  if (hoverList) {
    clearNode(hoverList);
  }

  for (const category of state.databankIndex) {
    const tile = document.createElement("button");
    tile.type = "button";
    tile.className = "databank-tile";
    tile.addEventListener("click", () => {
      void openDatabankCategory(category.slug);
    });
    const title = document.createElement("h3");
    title.textContent = category.label;
    const meta = document.createElement("p");
    meta.textContent = category.available
      ? `${category.entry_count} entries`
      : "Dataset unavailable in current Forge export";
    tile.appendChild(title);
    tile.appendChild(meta);
    tileGrid.appendChild(tile);

    if (hoverList) {
      const li = document.createElement("li");
      li.textContent = `${category.label} (${category.entry_count})`;
      hoverList.appendChild(li);
    }
  }
}

async function openDatabankCategory(slug) {
  if (!slug) {
    return;
  }
  state.activeDatabankCategory = slug;
  byId("databank-landing").classList.add("is-hidden");
  byId("databank-detail").classList.remove("is-hidden");

  const category = state.databankIndex.find((entry) => entry.slug === slug);
  byId("databank-detail-title").textContent = category ? category.label : titleCase(slug);

  let entries = state.databankCache.get(slug);
  if (!entries) {
    entries = await loadDatabankCategory(slug);
    state.databankCache.set(slug, entries);
  }

  const content = byId("databank-detail-content");
  clearNode(content);

  if (!Array.isArray(entries) || entries.length === 0) {
    const empty = document.createElement("p");
    empty.className = "meta";
    empty.textContent = category && !category.available
      ? "Forge does not currently provide this dataset. Placeholder page is active."
      : "No entries available.";
    content.appendChild(empty);
    return;
  }

  const table = document.createElement("table");
  table.className = "databank-table";
  const head = document.createElement("thead");
  head.innerHTML = "<tr><th>Name</th><th>Description</th><th>Tags</th><th>Source</th></tr>";
  table.appendChild(head);

  const body = document.createElement("tbody");
  for (const entry of entries) {
    const row = document.createElement("tr");
    const nameCell = document.createElement("td");
    nameCell.textContent = localize(entry.name_key) || entry.name_key || entry.id;
    row.appendChild(nameCell);

    const descCell = document.createElement("td");
    descCell.textContent = localize(entry.desc_key) || entry.desc_key || "No localized description available.";
    row.appendChild(descCell);

    const tagsCell = document.createElement("td");
    tagsCell.textContent = asArray(entry.tags).join(", ");
    row.appendChild(tagsCell);

    const sourceCell = document.createElement("td");
    sourceCell.textContent = entry.source_dataset || entry.source_file || "n/a";
    row.appendChild(sourceCell);

    body.appendChild(row);
  }

  table.appendChild(body);
  content.appendChild(table);
}

function closeDatabankCategory() {
  state.activeDatabankCategory = "";
  byId("databank-detail").classList.add("is-hidden");
  byId("databank-landing").classList.remove("is-hidden");
}
function buildSearchIndex() {
  state.searchIndex = [];
  state.searchLookup.clear();

  const modules = [
    { id: "empire", title: "Empire" },
    { id: "events", title: "Events" },
    { id: "tech", title: "Tech" },
    { id: "databank", title: "Databank" },
    { id: "settings", title: "Settings" },
  ];
  for (const moduleEntry of modules) {
    state.searchIndex.push({
      type: "module",
      id: moduleEntry.id,
      title: moduleEntry.title,
      display: `Module: ${moduleEntry.title}`,
      module: moduleEntry.id,
      pane: "",
      idNorm: normalize(moduleEntry.id),
      titleNorm: normalize(moduleEntry.title),
      termText: normalize(`${moduleEntry.id} ${moduleEntry.title}`),
      localizedText: "",
      searchText: normalize(`${moduleEntry.id} ${moduleEntry.title}`),
    });
  }

  for (const anomaly of Object.values(state.anomalies)) {
    const title = getAnomalyTitle(anomaly);
    state.searchIndex.push({
      type: "anomaly",
      id: anomaly.id,
      title,
      display: `Anomaly: ${title} (${anomaly.id})`,
      module: "events",
      pane: "anomalies",
      idNorm: normalize(anomaly.id),
      titleNorm: normalize(title),
      termText: normalize(`${anomaly.id} ${anomaly.desc_key || ""} ${asArray(anomaly.event_ids).join(" ")}`),
      localizedText: normalize(`${title} ${localize(anomaly.desc_key) || ""}`),
      searchText: normalize(`${anomaly.id} ${title} ${localize(anomaly.desc_key) || ""}`),
    });
  }

  for (const eventRecord of Object.values(state.events)) {
    const title = getEventTitle(eventRecord);
    state.searchIndex.push({
      type: "event",
      id: eventRecord.id,
      title,
      display: `Event: ${title} (${eventRecord.id})`,
      module: "events",
      pane: "events",
      idNorm: normalize(eventRecord.id),
      titleNorm: normalize(title),
      termText: normalize(`${eventRecord.id} ${eventRecord.title_key || ""} ${asArray(eventRecord.option_name_keys).join(" ")}`),
      localizedText: normalize(`${title} ${getEventDesc(eventRecord)}`),
      searchText: normalize(`${eventRecord.id} ${title} ${getEventDesc(eventRecord)}`),
    });
  }

  for (const site of Object.values(state.arcSites)) {
    const title = getArcSiteTitle(site);
    state.searchIndex.push({
      type: "arc-site",
      id: site.id,
      title,
      display: `Arc Site: ${title} (${site.id})`,
      module: "events",
      pane: "arc-sites",
      idNorm: normalize(site.id),
      titleNorm: normalize(title),
      termText: normalize(`${site.id} ${asArray(site.desc_keys).join(" ")}`),
      localizedText: normalize(title),
      searchText: normalize(`${site.id} ${title}`),
    });
  }

  for (const rift of Object.values(state.astralRifts)) {
    const title = getAstralRiftTitle(rift);
    state.searchIndex.push({
      type: "astral-rift",
      id: rift.id,
      title,
      display: `Astral Rift: ${title} (${rift.id})`,
      module: "events",
      pane: "astral-rifts",
      idNorm: normalize(rift.id),
      titleNorm: normalize(title),
      termText: normalize(`${rift.id} ${rift.name_key || ""} ${asArray(rift.flags).join(" ")}`),
      localizedText: normalize(`${title} ${asArray(rift.relic_rewards).join(" ")}`),
      searchText: normalize(`${rift.id} ${title} ${asArray(rift.relic_rewards).join(" ")}`),
    });
  }

  for (const category of state.databankIndex) {
    state.searchIndex.push({
      type: "databank-category",
      id: category.slug,
      title: category.label,
      display: `Databank: ${category.label}`,
      module: "databank",
      pane: category.slug,
      idNorm: normalize(category.slug),
      titleNorm: normalize(category.label),
      termText: normalize(`${category.slug} ${category.label}`),
      localizedText: "",
      searchText: normalize(`${category.slug} ${category.label}`),
    });
  }

  for (const techEntry of state.techSearchEntries) {
    if (!techEntry || !techEntry.id) {
      continue;
    }
    const title = techEntry.title || techEntry.id;
    state.searchIndex.push({
      type: "tech",
      id: techEntry.id,
      title,
      display: `Tech: ${title} (${techEntry.id})`,
      module: "tech",
      pane: techEntry.area || "all",
      idNorm: normalize(techEntry.id),
      titleNorm: normalize(title),
      termText: normalize(`${techEntry.id} ${techEntry.area || ""}`),
      localizedText: normalize(`${title} ${techEntry.search_text || ""}`),
      searchText: normalize(`${techEntry.id} ${title} ${techEntry.search_text || ""}`),
      techArea: techEntry.area || "all",
    });
  }
}

function rankMatches(query, limit = 30) {
  const needle = normalize(query).trim();
  if (!needle) {
    return [];
  }
  const terms = needle.split(/\s+/).filter(Boolean);
  const matches = [];

  for (const item of state.searchIndex) {
    if (!terms.every((term) => item.searchText.includes(term))) {
      continue;
    }

    let score = 60;
    if (item.idNorm === needle) {
      score -= 50;
    } else if (item.idNorm.startsWith(needle)) {
      score -= 32;
    } else if (item.titleNorm === needle) {
      score -= 30;
    } else if (item.titleNorm.startsWith(needle)) {
      score -= 22;
    } else if (item.titleNorm.includes(needle)) {
      score -= 10;
    }

    if (terms.every((term) => item.termText.includes(term))) {
      score -= 7;
    } else {
      score += 5;
    }

    if (item.module === state.activeModule) {
      score -= 6;
    }
    if (state.activeModule === "events" && item.pane === state.activeEventsTab) {
      score -= 4;
    }
    if (state.activeModule === "tech" && item.type === "tech") {
      score -= 4;
    }

    matches.push({ item, score });
  }

  matches.sort((a, b) => a.score - b.score || a.item.type.localeCompare(b.item.type) || a.item.id.localeCompare(b.item.id));
  return matches.slice(0, limit).map((entry) => entry.item);
}

function refreshSearchSuggestions() {
  const datalist = byId("global-search-list");
  clearNode(datalist);
  state.searchLookup.clear();
  const input = byId("global-search");
  const query = (input.value || "").trim();
  if (!query) {
    return;
  }
  for (const item of rankMatches(query, 30)) {
    state.searchLookup.set(item.display, item);
    const option = document.createElement("option");
    option.value = item.display;
    datalist.appendChild(option);
  }
}

async function navigateSearchResult(item) {
  if (!item) {
    return false;
  }
  if (item.type === "module") {
    setModule(item.id);
    return true;
  }
  if (item.type === "anomaly") {
    setModule("events");
    setEventsTab("anomalies");
    state.activeAnomalyId = item.id;
    await renderAnomalyTable();
    return true;
  }
  if (item.type === "event") {
    setModule("events");
    setEventsTab("events");
    state.focusedEventId = item.id;
    renderEventsPanel();
    return true;
  }
  if (item.type === "arc-site") {
    setModule("events");
    setEventsTab("arc-sites");
    state.activeArcSiteId = item.id;
    await renderArcSiteTable();
    return true;
  }
  if (item.type === "astral-rift") {
    setModule("events");
    setEventsTab("astral-rifts");
    state.activeAstralRiftId = item.id;
    await renderAstralRiftTable();
    return true;
  }
  if (item.type === "databank-category") {
    setModule("databank");
    await openDatabankCategory(item.id);
    return true;
  }
  if (item.type === "tech") {
    setModule("tech");
    setTechTab(item.techArea || "all");
    applyTechTabToNative(item.techArea || "all");
    if (window.WebUISttNative && typeof window.WebUISttNative.focusTech === "function") {
      window.WebUISttNative.focusTech(item.id, { focusChain: true, scroll: true });
    }
    return true;
  }
  return false;
}

async function commitSearch() {
  const input = byId("global-search");
  const query = (input.value || "").trim();
  if (!query) {
    setStatus("Type a search query first.", "warn");
    return;
  }

  let item = state.searchLookup.get(query) || null;
  if (!item) {
    const ranked = rankMatches(query, 1);
    item = ranked[0] || null;
  }
  if (!item) {
    setStatus(`No match found for \"${query}\".`, "warn");
    return;
  }

  await navigateSearchResult(item);
  setStatus(`Loaded ${item.display}.`, "ok");
}

function rerenderCurrentPane() {
  if (state.activeModule === "events") {
    if (state.activeEventsTab === "anomalies") {
      void renderAnomalyTable();
    } else if (state.activeEventsTab === "arc-sites") {
      void renderArcSiteTable();
    } else if (state.activeEventsTab === "astral-rifts") {
      void renderAstralRiftTable();
    } else {
      renderEventsPanel();
    }
  }
}

function getShortcutFromEvent(event) {
  const parts = [];
  if (event.ctrlKey) {
    parts.push("Ctrl");
  }
  if (event.altKey) {
    parts.push("Alt");
  }
  if (event.shiftKey) {
    parts.push("Shift");
  }
  if (event.metaKey) {
    parts.push("Meta");
  }

  let key = String(event.key || "");
  if (key.length === 1) {
    key = key.toUpperCase();
  } else {
    key = key.toUpperCase();
  }
  if (["CONTROL", "SHIFT", "ALT", "META"].includes(key)) {
    return "";
  }
  if (key.startsWith("ARROW")) {
    key = key.replace("ARROW", "");
  }

  parts.push(key);
  return parts.join("+");
}

function setupShortcuts() {
  const input = byId("shortcut-focus-search");
  const clear = byId("shortcut-focus-search-clear");
  if (!input || !clear) {
    return;
  }

  const stored = localStorage.getItem(SHORTCUT_STORAGE_KEY);
  state.shortcuts.focusSearch = stored || DEFAULT_SHORTCUT;
  input.value = state.shortcuts.focusSearch;

  input.addEventListener("keydown", (event) => {
    event.preventDefault();
    const shortcut = getShortcutFromEvent(event);
    if (!shortcut) {
      return;
    }
    state.shortcuts.focusSearch = shortcut;
    input.value = shortcut;
    localStorage.setItem(SHORTCUT_STORAGE_KEY, shortcut);
    setStatus(`Shortcut updated: Focus Search = ${shortcut}`, "ok");
  });

  clear.addEventListener("click", () => {
    state.shortcuts.focusSearch = DEFAULT_SHORTCUT;
    input.value = DEFAULT_SHORTCUT;
    localStorage.setItem(SHORTCUT_STORAGE_KEY, DEFAULT_SHORTCUT);
    setStatus(`Shortcut reset: Focus Search = ${DEFAULT_SHORTCUT}`, "info");
  });

  window.addEventListener("keydown", (event) => {
    const active = document.activeElement;
    const typing = active && active.closest("input,textarea,[contenteditable='true']");
    if (typing && active !== input) {
      return;
    }

    const pressed = getShortcutFromEvent(event);
    if (!pressed || pressed !== state.shortcuts.focusSearch) {
      return;
    }

    event.preventDefault();
    const searchInput = byId("global-search");
    if (searchInput) {
      searchInput.focus();
      searchInput.select();
    }
  });
}

function setupHandlers() {
  for (const tabOwner of document.querySelectorAll(".module-tab, .module-subtab")) {
    tabOwner.addEventListener("mouseenter", refreshTabIconStates);
    tabOwner.addEventListener("mouseleave", refreshTabIconStates);
    tabOwner.addEventListener("focusin", refreshTabIconStates);
    tabOwner.addEventListener("focusout", refreshTabIconStates);
  }

  for (const tab of document.querySelectorAll(".module-tab")) {
    tab.addEventListener("click", () => {
      setModule(tab.dataset.module || "empire");
    });
  }

  const settingsButton = byId("settings-tab-button");
  if (settingsButton) {
    settingsButton.addEventListener("click", () => setModule("settings"));
  }

  for (const button of document.querySelectorAll("[data-empire-tab]")) {
    button.addEventListener("click", () => setEmpireTab(button.dataset.empireTab || "government"));
  }

  for (const button of document.querySelectorAll("[data-events-tab]")) {
    button.addEventListener("click", () => setEventsTab(button.dataset.eventsTab || "anomalies"));
  }

  for (const button of document.querySelectorAll("[data-tech-tab]")) {
    button.addEventListener("click", () => {
      const techTab = button.dataset.techTab || "all";
      setTechTab(techTab);
      applyTechTabToNative(techTab);
    });
  }

  const bioshipToggle = byId("tech-bioship-toggle");
  if (bioshipToggle) {
    bioshipToggle.addEventListener("change", applyBioshipToggle);
  }

  const clearTechFocus = byId("tech-clear-focus");
  if (clearTechFocus) {
    clearTechFocus.addEventListener("click", () => {
      if (window.WebUISttNative && typeof window.WebUISttNative.clearChainFocus === "function") {
        window.WebUISttNative.clearChainFocus();
      }
    });
  }

  const localeSelect = byId("locale-select");
  if (localeSelect) {
    localeSelect.addEventListener("change", async () => {
      await setLocale(localeSelect.value);
      buildSearchIndex();
      refreshSearchSuggestions();
      await renderAnomalyTable();
      await renderArcSiteTable();
      await renderAstralRiftTable();
      renderEventsPanel();
      renderDiscoveries();
      renderDatabankLanding();
      if (state.activeDatabankCategory) {
        await openDatabankCategory(state.activeDatabankCategory);
      }
      setStatus(`Language set to ${getLocale()}.`, "info");
    });
  }

  const search = byId("global-search");
  if (search) {
    search.addEventListener("input", () => {
      refreshSearchSuggestions();
      mirrorSearchToTech(search.value || "");
    });
    search.addEventListener("change", refreshSearchSuggestions);
    search.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        void commitSearch();
      }
    });
  }

  const back = byId("databank-back");
  if (back) {
    back.addEventListener("click", closeDatabankCategory);
  }

  const anomalyFilterToggle = byId("anomaly-filter-toggle");
  const anomalyFilterMenu = byId("anomaly-filter-menu");
  if (anomalyFilterToggle && anomalyFilterMenu) {
    anomalyFilterToggle.addEventListener("click", () => anomalyFilterMenu.classList.toggle("is-hidden"));
    document.addEventListener("click", (event) => {
      if (anomalyFilterMenu.classList.contains("is-hidden")) {
        return;
      }
      if (!anomalyFilterMenu.contains(event.target) && event.target !== anomalyFilterToggle) {
        anomalyFilterMenu.classList.add("is-hidden");
      }
    });
  }

  document.addEventListener("contextmenu", (event) => {
    if (event.target && event.target.closest("input,textarea,[contenteditable='true']")) {
      return;
    }
    event.preventDefault();
  });

  window.addEventListener("stt:ready", () => {
    refreshTechSearchEntries();
    refreshTierTracker();
  });
  window.addEventListener("stt:research-updated", refreshTierTracker);
  window.addEventListener("stt:search-index-updated", refreshTechSearchEntries);

  setupShortcuts();
  refreshTabIconStates();
}

function populateAscensionGrid() {
  const grid = byId("ascension-perk-grid");
  if (!grid) {
    return;
  }
  clearNode(grid);
  for (let index = 0; index < 8; index += 1) {
    const cell = document.createElement("div");
    cell.className = "ap-grid-item";
    grid.appendChild(cell);
  }
}

export async function initializeAnomalyView() {
  const [manifest, anomalies, events, arcSites, astralRifts, eventToEvents, databankIndex] = await Promise.all([
    loadManifest(),
    loadDataset("anomalies"),
    loadDataset("events"),
    loadDataset("arcSites"),
    loadDataset("astralRifts"),
    loadDataset("eventToEvents"),
    loadDataset("databankIndex"),
  ]);

  state.manifest = manifest;
  state.anomalies = anomalies;
  state.events = events;
  state.arcSites = arcSites;
  state.astralRifts = astralRifts;
  state.eventToEvents = eventToEvents;
  state.databankIndex = asArray(databankIndex);

  const localeSelect = byId("locale-select");
  if (localeSelect) {
    clearNode(localeSelect);
    for (const locale of asArray(manifest.locales)) {
      const option = document.createElement("option");
      option.value = locale;
      option.textContent = locale;
      if (locale === manifest.default_locale) {
        option.selected = true;
      }
      localeSelect.appendChild(option);
    }
  }

  await setLocale(manifest.default_locale || "l_english");

  const meta = byId("manifest-meta");
  if (meta) {
    meta.textContent = `build=${manifest.build_id} schema=${manifest.schema_version}`;
  }

  state.anomalyDlcKeys = [...new Set(Object.values(state.anomalies).map((anomaly) => getAnomalySourceKey(anomaly)))]
    .sort((a, b) => getAnomalySourceLabel(a).localeCompare(getAnomalySourceLabel(b)));
  state.anomalyDlcFilters = new Set(state.anomalyDlcKeys);

  setupHandlers();
  renderAnomalyFilters();
  await renderAnomalyTable();
  await renderArcSiteTable();
  await renderAstralRiftTable();
  renderEventsPanel();
  renderDiscoveries();
  renderDatabankLanding();
  populateAscensionGrid();

  buildSearchIndex();
  refreshSearchSuggestions();

  setEmpireTab("government");
  setEventsTab("anomalies");
  setTechTab("all");
  closeDatabankCategory();
  setModule("empire");

  setStatus("Ready. Search across modules, data pages, and tech nodes.", "info");
}

export async function preloadAnomaly(anomalyId) {
  const anomaly = await getAnomaly(anomalyId);
  if (!anomaly) {
    return;
  }
  setModule("events");
  setEventsTab("anomalies");
  state.activeAnomalyId = anomalyId;
  await renderAnomalyTable();
}
