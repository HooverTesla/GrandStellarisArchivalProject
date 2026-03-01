const DATA_ROOT = "../assets/data/v1";

const DATASET_PATHS = {
  anomalies: "entities/anomalies.json",
  events: "entities/events.json",
  arcSites: "entities/arc_sites.json",
  astralRifts: "entities/astral_rifts.json",
  techPrerequisites: "entities/tech_prerequisites.json",
  databankIndex: "entities/databank_index.json",
  anomalyToEvents: "chains/anomaly_to_events.json",
  arcSiteToEvents: "chains/arc_site_to_events.json",
  astralRiftToEvents: "chains/astral_rift_to_events.json",
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

function normalizeList(value) {
  if (Array.isArray(value)) {
    return value;
  }
  if (value === null || typeof value === "undefined") {
    return [];
  }
  return [value];
}

function uniqueStrings(values) {
  const out = [];
  const seen = new Set();
  for (const value of values) {
    if (typeof value !== "string" || value.length === 0 || seen.has(value)) {
      continue;
    }
    seen.add(value);
    out.push(value);
  }
  return out;
}

function getEventNamespace(eventId) {
  const value = String(eventId || "");
  const idx = value.indexOf(".");
  return idx > 0 ? value.slice(0, idx) : value;
}

function buildEventClosure(seedEventIds, eventToEventsMap, options = {}) {
  const maxNodes = Number(options.maxNodes || 240);
  const maxDepth = Number(options.maxDepth || 18);
  const namespaceRestricted = options.namespaceRestricted !== false;

  const seedIds = uniqueStrings(seedEventIds);
  const seedNamespaces = new Set(seedIds.map((id) => getEventNamespace(id)));
  const queue = seedIds.map((id) => ({ id, depth: 0 }));
  const visited = new Set();

  while (queue.length > 0 && visited.size < maxNodes) {
    const current = queue.shift();
    if (!current || !current.id || visited.has(current.id)) {
      continue;
    }
    visited.add(current.id);
    if (current.depth >= maxDepth) {
      continue;
    }

    const currentNamespace = getEventNamespace(current.id);
    const nextIds = normalizeList(eventToEventsMap[current.id]);
    for (const nextId of nextIds) {
      if (typeof nextId !== "string" || visited.has(nextId)) {
        continue;
      }
      if (namespaceRestricted) {
        const nextNamespace = getEventNamespace(nextId);
        const namespaceMatch = nextNamespace === currentNamespace || seedNamespaces.has(nextNamespace);
        if (!namespaceMatch) {
          continue;
        }
      }
      queue.push({ id: nextId, depth: current.depth + 1 });
    }
  }

  return [...visited];
}

function buildOptionEdges(eventRecordsMap) {
  const edges = [];
  const seen = new Set();

  for (const eventRecord of Object.values(eventRecordsMap)) {
    if (!eventRecord || typeof eventRecord !== "object") {
      continue;
    }
    const from = eventRecord.id;
    if (typeof from !== "string") {
      continue;
    }

    for (const option of normalizeList(eventRecord.options)) {
      if (!option || typeof option !== "object") {
        continue;
      }
      const optionIndex = Number(option.index || 0);
      for (const to of normalizeList(option.followup_event_ids)) {
        if (typeof to !== "string") {
          continue;
        }
        const edgeId = `${from}|${optionIndex}|${to}`;
        if (seen.has(edgeId)) {
          continue;
        }
        seen.add(edgeId);
        edges.push({
          from_event_id: from,
          to_event_id: to,
          via_option_index: optionIndex > 0 ? optionIndex : null,
        });
      }
    }
  }

  return edges;
}

function buildFallbackEdges(eventIds, eventToEventsMap) {
  const edges = [];
  const seen = new Set();
  const inClosure = new Set(eventIds);
  for (const from of eventIds) {
    for (const to of normalizeList(eventToEventsMap[from])) {
      if (typeof to !== "string" || !inClosure.has(to)) {
        continue;
      }
      const edgeId = `${from}|${to}`;
      if (seen.has(edgeId)) {
        continue;
      }
      seen.add(edgeId);
      edges.push({
        from_event_id: from,
        to_event_id: to,
        via_option_index: null,
      });
    }
  }
  return edges;
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

export async function loadDatabankCategory(slug) {
  const clean = String(slug || "").trim().toLowerCase();
  if (!clean) {
    throw new Error("Databank category slug is required.");
  }
  const key = `databank:${clean}`;
  if (!memo.has(key)) {
    memo.set(key, fetchJson(`${DATA_ROOT}/entities/databank/${clean}.json`));
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

export async function getArcSite(id) {
  const arcSites = await loadDataset("arcSites");
  return arcSites[id] || null;
}

export async function getAstralRift(id) {
  const rifts = await loadDataset("astralRifts");
  return rifts[id] || null;
}

export async function getTechPrerequisiteRecord(id) {
  const techMap = await loadDataset("techPrerequisites");
  return techMap[id] || null;
}

export async function getAnomalyChain(anomalyId, options = {}) {
  const [anomalies, events, arcSites, anomalyToEvents, eventToEvents, arcSiteToEvents] = await Promise.all([
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

  const seedEvents = uniqueStrings(normalizeList(anomalyToEvents[anomalyId]).concat(normalizeList(anomaly.event_ids)));
  const eventIds = buildEventClosure(seedEvents, eventToEvents, {
    maxNodes: options.maxNodes || 240,
    maxDepth: options.maxDepth || 18,
    namespaceRestricted: options.namespaceRestricted !== false,
  }).sort();

  const eventRecords = eventIds.map((id) => events[id]).filter(Boolean);
  const eventRecordMap = {};
  for (const record of eventRecords) {
    eventRecordMap[record.id] = record;
  }

  const closureSet = new Set(eventIds);
  const linkedArcSiteIds = Object.keys(arcSiteToEvents)
    .filter((siteId) => normalizeList(arcSiteToEvents[siteId]).some((eventId) => closureSet.has(eventId)))
    .sort();
  const linkedArcSites = linkedArcSiteIds.map((id) => arcSites[id]).filter(Boolean);

  const optionEdges = buildOptionEdges(eventRecordMap).filter((edge) => closureSet.has(edge.to_event_id));
  const edges = optionEdges.length > 0 ? optionEdges : buildFallbackEdges(eventIds, eventToEvents);

  return {
    anomaly,
    seed_event_ids: seedEvents,
    event_ids: eventIds,
    events: eventRecords,
    event_edges: edges,
    linked_arc_site_ids: linkedArcSiteIds,
    arc_sites: linkedArcSites,
  };
}

export async function getArcSiteChain(siteId, options = {}) {
  const [arcSites, events, arcSiteToEvents, eventToEvents] = await Promise.all([
    loadDataset("arcSites"),
    loadDataset("events"),
    loadDataset("arcSiteToEvents"),
    loadDataset("eventToEvents"),
  ]);

  const arcSite = arcSites[siteId] || null;
  if (!arcSite) {
    return null;
  }

  const stageEvents = uniqueStrings(
    normalizeList(arcSiteToEvents[siteId]).concat(
      normalizeList(arcSite.stages).map((stage) => stage && stage.event_id).filter(Boolean),
    ),
  );
  const eventIds = buildEventClosure(stageEvents, eventToEvents, {
    maxNodes: options.maxNodes || 200,
    maxDepth: options.maxDepth || 16,
    namespaceRestricted: options.namespaceRestricted !== false,
  }).sort();
  const eventRecords = eventIds.map((id) => events[id]).filter(Boolean);
  const eventRecordMap = {};
  for (const record of eventRecords) {
    eventRecordMap[record.id] = record;
  }
  const optionEdges = buildOptionEdges(eventRecordMap);

  return {
    arc_site: arcSite,
    seed_event_ids: stageEvents,
    event_ids: eventIds,
    events: eventRecords,
    event_edges: optionEdges.length > 0 ? optionEdges : buildFallbackEdges(eventIds, eventToEvents),
  };
}

export async function getAstralRiftChain(riftId, options = {}) {
  const [astralRifts, events, riftToEvents, eventToEvents] = await Promise.all([
    loadDataset("astralRifts"),
    loadDataset("events"),
    loadDataset("astralRiftToEvents"),
    loadDataset("eventToEvents"),
  ]);

  const rift = astralRifts[riftId] || null;
  if (!rift) {
    return null;
  }

  const seedEvents = uniqueStrings(
    normalizeList(riftToEvents[riftId]).concat(normalizeList(rift.event_ids)),
  );
  const eventIds = buildEventClosure(seedEvents, eventToEvents, {
    maxNodes: options.maxNodes || 260,
    maxDepth: options.maxDepth || 20,
    namespaceRestricted: options.namespaceRestricted !== false,
  }).sort();
  const eventRecords = eventIds.map((id) => events[id]).filter(Boolean);
  const eventRecordMap = {};
  for (const record of eventRecords) {
    eventRecordMap[record.id] = record;
  }
  const optionEdges = buildOptionEdges(eventRecordMap);

  return {
    astral_rift: rift,
    seed_event_ids: seedEvents,
    event_ids: eventIds,
    events: eventRecords,
    event_edges: optionEdges.length > 0 ? optionEdges : buildFallbackEdges(eventIds, eventToEvents),
  };
}

export { DATA_ROOT, DATASET_PATHS };
