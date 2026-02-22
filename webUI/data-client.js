const DATA_ROOT = "../assets/data/v1";

const DATASET_PATHS = {
  anomalies: "entities/anomalies.json",
  events: "entities/events.json",
  arcSites: "entities/arc_sites.json",
  anomalyToEvents: "chains/anomaly_to_events.json",
  arcSiteToEvents: "chains/arc_site_to_events.json",
  eventToEvents: "chains/event_to_events.json",
  reverseEventToSources: "chains/reverse_event_to_sources.json",
  gfxMap: "media/gfx_map.json",
  frameRects: "media/frame_rects.json",
};

const memo = new Map();

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok) {
    throw new Error(`Failed to fetch ${path} (${response.status})`);
  }
  return response.json();
}

export async function loadManifest() {
  const key = "manifest";
  if (!memo.has(key)) {
    memo.set(key, fetchJson(`${DATA_ROOT}/manifest.json`));
  }
  return memo.get(key);
}

export async function loadDataset(name) {
  const rel = DATASET_PATHS[name];
  if (!rel) {
    throw new Error(`Unknown dataset name: ${name}`);
  }

  const key = `dataset:${name}`;
  if (!memo.has(key)) {
    memo.set(key, fetchJson(`${DATA_ROOT}/${rel}`));
  }
  return memo.get(key);
}

export async function loadLocale(localeCode) {
  const key = `locale:${localeCode}`;
  if (!memo.has(key)) {
    memo.set(key, fetchJson(`${DATA_ROOT}/i18n/${localeCode}/narrative.json`));
  }
  return memo.get(key);
}

export async function resolveImage(gfxId) {
  if (!gfxId) {
    return null;
  }
  const gfxMap = await loadDataset("gfxMap");
  const entry = gfxMap[gfxId];
  if (!entry || !entry.image_asset) {
    return null;
  }
  return `../assets/${entry.image_asset}`;
}

export async function getAnomaly(id) {
  const anomalies = await loadDataset("anomalies");
  return anomalies[id] || null;
}

function computeEventClosure(seedEventIds, eventToEventsMap, maxNodes = 500) {
  const visited = new Set();
  const queue = [...seedEventIds];

  while (queue.length > 0 && visited.size < maxNodes) {
    const current = queue.shift();
    if (!current || visited.has(current)) {
      continue;
    }
    visited.add(current);
    const next = eventToEventsMap[current] || [];
    for (const eventId of next) {
      if (!visited.has(eventId)) {
        queue.push(eventId);
      }
    }
  }

  return [...visited];
}

export async function getAnomalyChain(anomalyId) {
  const [
    anomalies,
    events,
    arcSites,
    anomalyToEvents,
    eventToEvents,
    arcSiteToEvents,
  ] = await Promise.all([
    loadDataset("anomalies"),
    loadDataset("events"),
    loadDataset("arcSites"),
    loadDataset("anomalyToEvents"),
    loadDataset("eventToEvents"),
    loadDataset("arcSiteToEvents"),
  ]);

  const anomaly = anomalies[anomalyId] || null;
  if (!anomaly) {
    return null;
  }

  const seedEvents = anomalyToEvents[anomalyId] || anomaly.event_ids || [];
  const eventClosure = computeEventClosure(seedEvents, eventToEvents, 500);
  const eventRecords = eventClosure.map((id) => events[id]).filter(Boolean);

  const closureSet = new Set(eventClosure);
  const linkedArcSiteIds = Object.keys(arcSiteToEvents)
    .filter((siteId) => (arcSiteToEvents[siteId] || []).some((eventId) => closureSet.has(eventId)))
    .sort();
  const linkedArcSites = linkedArcSiteIds.map((id) => arcSites[id]).filter(Boolean);

  return {
    anomaly,
    seed_event_ids: [...seedEvents].sort(),
    event_ids: [...eventClosure].sort(),
    events: eventRecords,
    linked_arc_site_ids: linkedArcSiteIds,
    arc_sites: linkedArcSites,
  };
}

export { DATA_ROOT, DATASET_PATHS };
