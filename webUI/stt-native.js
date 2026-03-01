(function bootstrapSttNative(window, $) {
  "use strict";

  if (!$ || !window.Treant) {
    return;
  }

  const STT_ROOT = "../stellaris-tech-tree";
  const STT_VERSION_ALIASES = {
    latest: "phoenix-4.0.10",
  };
  const STT_DEFAULT_VERSION = "latest";
  const ICON_ROOT = `${STT_ROOT}/assets/icons`;
  const WEB_DATA_ROOT = "../assets/data/v1";
  const RESOURCE_ICON_PATTERN = /(?:\u00C2)?\u00A3(\w+)(?:\u00C2)?\u00A3/g;

  function resolveVersion() {
    const params = new URLSearchParams(window.location.search);
    const requested = (params.get("stt_version") || params.get("version") || STT_DEFAULT_VERSION).trim().toLowerCase();
    return STT_VERSION_ALIASES[requested] || requested || STT_VERSION_ALIASES[STT_DEFAULT_VERSION];
  }

  const STT_VERSION = resolveVersion();
  const STT_DATA_ROOT = `${STT_ROOT}/${STT_VERSION}`;
  window.research = ["physics", "society", "engineering", "anomaly"];
  const research = window.research;
  const charts = window.charts || {};
  window.charts = charts;
  let initialized = false;
  let focusedTechId = "";
  let bioshipMode = "all";
  let techLogicIndex = {};
  let techLogicPromise = null;
  let searchEntries = [];
  let graphCache = null;

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
    const seen = new Set();
    const output = [];
    values.forEach((value) => {
      if (typeof value !== "string" || value.length === 0 || seen.has(value)) {
        return;
      }
      seen.add(value);
      output.push(value);
    });
    return output;
  }

  function ensureTechLogicLoaded() {
    if (techLogicPromise) {
      return techLogicPromise;
    }
    techLogicPromise = window.fetch(`${WEB_DATA_ROOT}/entities/tech_prerequisites.json`, { cache: "no-cache" })
      .then((response) => (response.ok ? response.json() : {}))
      .then((payload) => {
        techLogicIndex = payload && typeof payload === "object" ? payload : {};
        graphCache = null;
        applyBioshipMode(bioshipMode);
        buildSearchEntries();
      })
      .catch(() => {
        techLogicIndex = {};
      });
    return techLogicPromise;
  }

  function getTechLogic(techId) {
    const entry = techLogicIndex[techId];
    return entry && typeof entry === "object" ? entry : null;
  }

  function isTechActive(techId) {
    return $("#" + techId).find("div.node-status").hasClass("active");
  }

  function evaluatePrerequisitesFromLogic(techId) {
    const logicRecord = getTechLogic(techId);
    if (!logicRecord || !logicRecord.prerequisite_logic) {
      return null;
    }
    const logic = logicRecord.prerequisite_logic;
    const allOf = uniqueStrings(normalizeList(logic.all_of));
    const anyOfGroups = normalizeList(logic.any_of).map((group) => uniqueStrings(normalizeList(group)));
    const allOfMet = allOf.every((prereqId) => isTechActive(prereqId));
    const anyOfMet = anyOfGroups.every((group) => group.length === 0 || group.some((prereqId) => isTechActive(prereqId)));
    return allOfMet && anyOfMet;
  }

  function evaluatePrerequisitesFallback(node) {
    let prerequisitesMet = true;
    node.find("span.node-status").each(function () {
      const tech = this.classList[1];
      const prereq = $("#" + tech).find("div.node-status");
      if (prereq.length && !prereq.hasClass("active")) {
        prerequisitesMet = false;
      }
    });
    return prerequisitesMet;
  }

  function evaluatePrerequisites(techId, node) {
    const logicResult = evaluatePrerequisitesFromLogic(techId);
    if (logicResult === null) {
      return evaluatePrerequisitesFallback(node);
    }
    return logicResult;
  }

  function getNodeArea(node) {
    if (!node || !node.classList) {
      return "";
    }
    if (node.classList.contains("physics")) {
      return "physics";
    }
    if (node.classList.contains("society")) {
      return "society";
    }
    if (node.classList.contains("engineering")) {
      return "engineering";
    }
    if (node.classList.contains("anomaly")) {
      return "events";
    }
    return "";
  }

  function normalizeAreaTab(area) {
    const value = String(area || "all").trim().toLowerCase();
    if (value === "events" || value === "event") {
      return "anomalies";
    }
    if (["all", "physics", "society", "engineering", "anomalies"].includes(value)) {
      return value;
    }
    return "all";
  }

  function getNodeTier(node) {
    const treeNodeData = $(node).data("treenode");
    if (treeNodeData && typeof treeNodeData.tier !== "undefined") {
      const direct = Number(treeNodeData.tier);
      if (!Number.isNaN(direct) && Number.isFinite(direct)) {
        return direct;
      }
    }

    const tierNode = node.querySelector(".node-title .tier");
    if (tierNode && /starting/i.test(tierNode.textContent || "")) {
      return 0;
    }
    const match = tierNode && (tierNode.textContent || "").match(/tier\s+(\d+)/i);
    if (match) {
      const parsed = Number(match[1]);
      if (!Number.isNaN(parsed)) {
        return parsed;
      }
    }
    return 0;
  }

  function getParentNode(area, parentId, nodeId) {
    if (!(parentId > 0)) {
      return null;
    }
    const chart = charts[area];
    const parentFromChart = chart && chart.tree && chart.tree.nodeDB && chart.tree.nodeDB.db
      ? chart.tree.nodeDB.db[parentId]
      : null;
    if (parentFromChart) {
      return parentFromChart;
    }
    if (typeof window.getNodeDBNode === "function") {
      try {
        const nodeEntry = window.getNodeDBNode(area, nodeId);
        if (nodeEntry && typeof nodeEntry.parentId !== "undefined") {
          const db = chart && chart.tree && chart.tree.nodeDB && chart.tree.nodeDB.db
            ? chart.tree.nodeDB.db
            : [];
          return db[nodeEntry.parentId] || null;
        }
      } catch (_) {
        return null;
      }
    }
    return null;
  }

  function buildGraphCache() {
    const prereqMap = {};
    const dependentMap = {};
    const nodes = Array.from(document.querySelectorAll("#tech-tree .node.tech"));
    nodes.forEach((node) => {
      const techId = node.id;
      if (!techId) {
        return;
      }
      const logic = getTechLogic(techId);
      const fromLogic = logic ? uniqueStrings(
        normalizeList(logic.prerequisites_flat),
      ) : [];
      const fromTooltip = Array.from(node.querySelectorAll("span.node-status"))
        .map((item) => item.classList[1])
        .filter(Boolean);
      const prereqs = uniqueStrings(fromLogic.length > 0 ? fromLogic : fromTooltip);
      prereqMap[techId] = prereqs;
      prereqs.forEach((prereqId) => {
        if (!dependentMap[prereqId]) {
          dependentMap[prereqId] = [];
        }
        if (!dependentMap[prereqId].includes(techId)) {
          dependentMap[prereqId].push(techId);
        }
      });
    });
    graphCache = { prereqMap, dependentMap };
  }

  function computeTechChainSet(rootId) {
    if (!graphCache) {
      buildGraphCache();
    }
    const chain = new Set();
    const queue = [rootId];
    while (queue.length > 0 && chain.size < 2200) {
      const current = queue.shift();
      if (!current || chain.has(current)) {
        continue;
      }
      chain.add(current);
      normalizeList(graphCache.prereqMap[current]).forEach((nextId) => {
        if (!chain.has(nextId)) {
          queue.push(nextId);
        }
      });
      normalizeList(graphCache.dependentMap[current]).forEach((nextId) => {
        if (!chain.has(nextId)) {
          queue.push(nextId);
        }
      });
    }
    return chain;
  }

  function clearChainFocus() {
    focusedTechId = "";
    Array.from(document.querySelectorAll("#tech-tree .node.tech")).forEach((node) => {
      node.classList.remove("is-chain-muted", "is-chain-focus");
    });
  }

  function applyChainFocus(techId) {
    const rootNode = document.getElementById(techId);
    if (!rootNode) {
      return false;
    }
    const chainSet = computeTechChainSet(techId);
    focusedTechId = techId;
    Array.from(document.querySelectorAll("#tech-tree .node.tech")).forEach((node) => {
      const inChain = chainSet.has(node.id);
      node.classList.toggle("is-chain-muted", !inChain);
      node.classList.toggle("is-chain-focus", node.id === techId);
    });
    return true;
  }

  function applyBioshipMode(nextMode) {
    bioshipMode = nextMode || "all";
    Array.from(document.querySelectorAll("#tech-tree .node.tech")).forEach((node) => {
      const techId = node.id;
      const logic = getTechLogic(techId);
      const mode = logic && logic.bioship_mode ? logic.bioship_mode : "any";
      const hide = bioshipMode === "bio" && mode === "non_bio_only";
      node.classList.toggle("bioship-hidden", hide);
    });
    buildSearchEntries();
    emitResearchUpdate();
  }

  function getTierSummary() {
    const summary = {
      physics: { current_tier: 0, completed_in_tier: 0, total_in_tier: 0 },
      society: { current_tier: 0, completed_in_tier: 0, total_in_tier: 0 },
      engineering: { current_tier: 0, completed_in_tier: 0, total_in_tier: 0 },
    };
    const stats = {
      physics: {},
      society: {},
      engineering: {},
    };

    Array.from(document.querySelectorAll("#tech-tree .node.tech")).forEach((node) => {
      if (node.classList.contains("bioship-hidden")) {
        return;
      }
      const area = getNodeArea(node);
      if (!stats[area]) {
        return;
      }
      const tier = getNodeTier(node);
      if (!stats[area][tier]) {
        stats[area][tier] = { total: 0, active: 0 };
      }
      stats[area][tier].total += 1;
      if ($(node).find("div.node-status").hasClass("active")) {
        stats[area][tier].active += 1;
      }
    });

    Object.keys(summary).forEach((area) => {
      const tiers = Object.keys(stats[area]).map((value) => Number(value)).sort((a, b) => a - b);
      const playableTiers = tiers.filter((tier) => tier > 0);
      let currentTier = 0;

      for (const tier of playableTiers) {
        const currentBucket = stats[area][tier];
        const prevBucket = stats[area][tier - 1];
        const unlocked = tier === 1 || (prevBucket && prevBucket.total > 0 && prevBucket.active >= prevBucket.total);
        if (unlocked && currentBucket.active < currentBucket.total) {
          currentTier = tier;
          break;
        }
        if (currentBucket.active > 0) {
          currentTier = tier;
        }
      }

      if (currentTier === 0 && playableTiers.length > 0) {
        currentTier = playableTiers[0];
      }
      const bucket = stats[area][currentTier] || { total: 0, active: 0 };
      summary[area] = {
        current_tier: currentTier,
        completed_in_tier: bucket.active,
        total_in_tier: bucket.total,
      };
    });
    return summary;
  }

  function buildSearchEntries() {
    const entries = [];
    Array.from(document.querySelectorAll("#tech-tree .node.tech")).forEach((node) => {
      if (node.classList.contains("bioship-hidden")) {
        return;
      }
      const techId = node.id;
      if (!techId) {
        return;
      }
      const titleNode = node.querySelector(".node-name");
      const title = titleNode ? titleNode.textContent.trim() : techId;
      let text = "";
      node.querySelectorAll(".node-name, .node-desc, .extra-data .tooltip-content").forEach((child) => {
        text += ` ${child.textContent || ""}`;
      });
      entries.push({
        id: techId,
        title,
        area: getNodeArea(node) || "all",
        search_text: text.trim(),
      });
    });
    searchEntries = entries;
    window.dispatchEvent(new CustomEvent("stt:search-index-updated", { detail: { count: entries.length } }));
  }

  function emitResearchUpdate() {
    window.dispatchEvent(new CustomEvent("stt:research-updated", { detail: { tierSummary: getTierSummary() } }));
  }

  function bindMissingStatusHandlers(area) {
    const root = `#tech-tree-${area}`;
    const statuses = $(`${root} .node div.node-status`);
    if (!statuses.length) {
      return;
    }

    statuses.each(function () {
      const statusNode = $(this);
      if (statusNode.data("sttBound")) {
        return;
      }

      statusNode.off("click.sttnative");
      statusNode.on("click.sttnative", function (event) {
        const status = $(this);
        const node = status.parent();
        const nodeId = node.attr("id");
        if (!nodeId) {
          event.stopPropagation();
          return;
        }

        if (node.hasClass("anomaly")) {
          const active = status.hasClass("active");
          status.toggleClass("active", !active);
          node.toggleClass("active", !active);
          event.stopPropagation();
          return;
        }

        const nodeData = node.data("treenode");
        const parentId = nodeData && typeof nodeData.parentId !== "undefined"
          ? Number(nodeData.parentId)
          : -1;

        if (parentId > 0) {
          const parent = getParentNode(area, parentId, nodeId);
          if (parent && !$("#" + parent.nodeHTMLid + " div.node-status").hasClass("active")) {
            event.stopPropagation();
            return;
          }
        }

        if (!evaluatePrerequisites(nodeId, node)) {
          event.stopPropagation();
          return;
        }

        const active = status.hasClass("active");
        try {
          if (typeof window.updateResearch === "function") {
            window.updateResearch(area, nodeId, !active);
          } else {
            status.toggleClass("active", !active);
            node.toggleClass("active", !active);
          }
        } catch (_) {
          status.toggleClass("active", !active);
          node.toggleClass("active", !active);
        }
        graphCache = null;
        buildSearchEntries();
        window.setTimeout(() => {
          emitResearchUpdate();
        }, 0);
        event.stopPropagation();
      });

      statusNode.data("sttBound", true).addClass("status-loaded");
    });
  }

  function bindNodeFocusHandlers(area) {
    const root = `#tech-tree-${area}`;
    const nodes = $(`${root} .node.tech`);
    if (!nodes.length) {
      return;
    }
    nodes.each(function () {
      const node = $(this);
      if (node.data("sttFocusBound")) {
        return;
      }
      node.on("click.sttchain", function (event) {
        if ($(event.target).closest("div.node-status").length > 0) {
          return;
        }
        const nodeId = this.id;
        if (!nodeId) {
          return;
        }
        if (focusedTechId === nodeId) {
          clearChainFocus();
        } else {
          applyChainFocus(nodeId);
        }
      });
      node.data("sttFocusBound", true);
    });
  }

  function ensureStatusBindings(area) {
    if (typeof window.init_nodestatus === "function") {
      window.init_nodestatus(area);
    }
    bindMissingStatusHandlers(area);
    bindNodeFocusHandlers(area);
  }

  const config = {
    rootOrientation: "WEST",
    nodeAlign: "TOP",
    hideRootNode: true,
    siblingSeparation: 20,
    subTeeSeparation: 20,
    scrollbar: "resize",
    connectors: {
      type: "step",
    },
    node: {
      HTMLclass: "tech",
      collapsable: false,
    },
    callback: {
      onTreeLoaded: function (tree) {
        init_tooltips();
        const area = tree.nodeHTMLclass.replace("tech", "").replace(" ", "");
        ensureStatusBindings(area);
        buildSearchEntries();
        emitResearchUpdate();
        const observer = lozad();
        observer.observe();
      },
    },
  };

  function init_tooltips() {
    $(".node:not(.tooltipstered)").tooltipster({
      minWidth: 300,
      trigger: "click",
      maxWidth: 512,
      functionInit: function (instance, helper) {
        const content = $(helper.origin).find(".extra-data");
        $(content).find("img").each(function (_, el) {
          $(el).attr("src", $(el).attr("data-src"));

          const classes = $(el)[0].classList;
          const tech = classes[classes.length - 1];
          if (!$("#" + tech).hasClass("anomaly")) {
            const parent = $("#" + tech)[0];
            if (parent !== undefined && parent.classList.length > 1) {
              $(el).addClass(parent.classList[2]);
            }
          }
        });
        instance.content($('<div class="ui-tooltip">' + $(content).html() + "</div>"));
      },
      functionReady: function (instance, helper) {
        $(helper.tooltip).find(".tooltip-content").each(function () {
          const raw = $(this).html();
          const replaced = raw.replace(RESOURCE_ICON_PATTERN, `<img class="resource" src="${ICON_ROOT}/$1.png" />`);
          $(this).html(replaced);
        });

        $(helper.tooltip).find(".node-status").each(function () {
          const tech = $(this)[0].classList[1];
          if ($("#" + tech).find("div.node-status").hasClass("active")) {
            $(this).addClass("active");
          } else {
            $(this).removeClass("active");
          }
        });
      },
    });
  }

  function setup(tech) {
    const techClass = (tech.is_dangerous ? " dangerous" : "")
      + (!tech.is_dangerous && tech.is_rare ? " rare" : "");

    const tmpl = $.templates("#node-template");
    const html = tmpl.render(tech);

    tech.HTMLid = tech.key;
    tech.HTMLclass = tech.area + techClass + (tech.is_start_tech ? " active" : "");

    let output = html;
    if (tech.is_start_tech) {
      const element = $("<div>" + html + "</div>");
      element.find("div.node-status").addClass("active").addClass("status-loaded");
      output = element.html();
    }

    tech.innerHTML = output;

    $(tech.children).each(function (_, node) {
      setup(node);
    });
  }

  function setup_search() {
    const deepsearch = $("#deepsearch");
    if (!deepsearch.length) {
      return;
    }

    const trees = document.querySelector("#tech-tree").querySelectorAll("[id|='tech-tree']");

    let nodes = Array.from(trees)
      .filter((tree) => tree.getAttribute("class") === null || !tree.getAttribute("class").includes("float-NoDisplay"))
      .reduce((acc, tree) => {
        acc.push(...Array.from(tree.querySelectorAll(".node.tech")).filter((node) => !node.classList.contains("bioship-hidden")));
        return acc;
      }, []);

    nodes = nodes.reduce((acc, node) => {
      let fullText = "";
      node.querySelectorAll(".node-name, .extra-data .tooltip-content:not(.prerequisites)").forEach((entry) => {
        fullText += entry.innerText;
        fullText += entry.title;
      });
      acc.push({ node, text: fullText });
      return acc;
    }, []);

    const debounce = (callback, wait) => {
      let timeoutId = null;
      return (...args) => {
        window.clearTimeout(timeoutId);
        timeoutId = window.setTimeout(() => callback.apply(null, args), wait);
      };
    };

    let currentIdx = 0;
    let lastSearchTerm = "";

    deepsearch.off(".sttsearch");
    deepsearch.on("change.sttsearch keyup.sttsearch paste.sttsearch", debounce(function () {
      const searchTerm = deepsearch.val();
      if (searchTerm === lastSearchTerm) {
        return;
      }
      lastSearchTerm = searchTerm;
      currentIdx = 0;

      if (!searchTerm) {
        nodes.forEach((entry) => { entry.node.style.opacity = 1; });
        return;
      }

      const hits = nodes.filter((entry) => {
        const match = entry.text.toLowerCase().includes(String(searchTerm).toLowerCase());
        entry.node.style.opacity = match ? 0.6 : 0.1;
        return match;
      });

      hits.sort((a, b) => {
        return a.node.getBoundingClientRect().top - b.node.getBoundingClientRect().top
          || a.node.getBoundingClientRect().left - b.node.getBoundingClientRect().left;
      });

      let first = true;
      hits.forEach((entry) => {
        if (first) {
          first = false;
          entry.node.scrollIntoView({
            behavior: "smooth",
            block: "center",
            inline: "nearest",
          });
          entry.node.style.opacity = 1;
        } else {
          entry.node.style.opacity = 0.6;
        }
      });
    }, 250));

    deepsearch.on("keypress.sttsearch", function (event) {
      if (event.which !== 13) {
        return;
      }

      const searchTerm = deepsearch.val();
      const hits = nodes.filter((entry) => {
        const match = entry.text.toLowerCase().includes(String(searchTerm).toLowerCase());
        entry.node.style.opacity = match ? 0.6 : 0.1;
        return match;
      });

      hits.sort((a, b) => {
        return a.node.getBoundingClientRect().top - b.node.getBoundingClientRect().top
          || a.node.getBoundingClientRect().left - b.node.getBoundingClientRect().left;
      });

      if (hits.length === 0) {
        return;
      }

      hits[currentIdx % hits.length].node.style.opacity = 0.6;
      const focused = hits[(currentIdx + 1) % hits.length].node;
      focused.scrollIntoView({
        behavior: "smooth",
        block: "center",
        inline: "nearest",
      });
      focused.style.opacity = 1;

      currentIdx += 1;
    });
  }

  function applyArea(area) {
    const resolvedArea = normalizeAreaTab(area);
    $("#tech-tree-search").addClass("float-NoDisplay");
    $("#tech-tree-physics").addClass("float-NoDisplay");
    $("#tech-tree-society").addClass("float-NoDisplay");
    $("#tech-tree-engineering").addClass("float-NoDisplay");
    $("#tech-tree-anomalies").addClass("float-NoDisplay");

    if (resolvedArea === "all") {
      $("#tech-tree-physics").removeClass("float-NoDisplay");
      $("#tech-tree-society").removeClass("float-NoDisplay");
      $("#tech-tree-engineering").removeClass("float-NoDisplay");
    } else if (resolvedArea === "physics") {
      $("#tech-tree-physics").removeClass("float-NoDisplay");
    } else if (resolvedArea === "society") {
      $("#tech-tree-society").removeClass("float-NoDisplay");
    } else if (resolvedArea === "engineering") {
      $("#tech-tree-engineering").removeClass("float-NoDisplay");
    } else if (resolvedArea === "anomalies") {
      $("#tech-tree-anomalies").removeClass("float-NoDisplay");
    }

    setup_search();
    buildSearchEntries();
  }

  function _load(jsonData, tree) {
    const container = "#tech-tree-" + jsonData.children[0].name;
    const myconfig = { container };
    $.extend(true, myconfig, config);
    charts[tree] = new Treant({ chart: myconfig, nodeStructure: jsonData.children[0] }, function () {}, $);
    const bindAttempts = [120, 350, 750, 1400];
    bindAttempts.forEach((delay) => {
      window.setTimeout(() => {
        ensureStatusBindings(tree);
      }, delay);
    });
  }

  function load_tree() {
    research.forEach((area) => {
      if (area !== "anomaly") {
        $.getJSON(`${STT_DATA_ROOT}/${area}.json`, function (jsonData) {
          setup(jsonData);
          _load(jsonData, area);
        });
      }
    });

    $.getJSON(`${STT_DATA_ROOT}/anomalies.json`, function (jsonData) {
      $(jsonData).each(function (_, item) {
        setup(item);
        const element = $("<div>").html(item.innerHTML);
        element.attr("id", item.key);
        element.attr("class", item.HTMLclass);
        element.addClass("node").addClass("tech").addClass("anomaly");
        $("#tech-tree-anomalies").append(element);
      });
      ensureStatusBindings("anomalies");
      init_tooltips();
      applyBioshipMode(bioshipMode);
      buildSearchEntries();
      emitResearchUpdate();
    });
  }

  function init() {
    if (initialized) {
      return;
    }
    if (!document.querySelector("#tech-tree")) {
      return;
    }
    initialized = true;
    ensureTechLogicLoaded();
    load_tree();
    applyArea("all");
    setup_search();
    window.setTimeout(() => {
      buildSearchEntries();
      emitResearchUpdate();
      window.dispatchEvent(new CustomEvent("stt:ready"));
    }, 1200);
  }

  window.WebUISttNative = {
    init: init,
    ensureInitialized: init,
    setTab: function (tab) {
      init();
      applyArea(tab);
    },
    applySearchTerm: function (term) {
      init();
      const input = $("#deepsearch");
      if (!input.length) {
        return;
      }
      input.val(term || "");
      input.trigger("change");
      input.trigger("keyup");
    },
    focusTech: function (techId, options) {
      init();
      const node = document.getElementById(techId);
      if (!node) {
        return false;
      }
      const opts = options && typeof options === "object" ? options : {};
      if (opts.focusChain !== false) {
        applyChainFocus(techId);
      }
      if (opts.scroll !== false) {
        node.scrollIntoView({
          behavior: "smooth",
          block: "center",
          inline: "nearest",
        });
      }
      return true;
    },
    clearChainFocus: function () {
      clearChainFocus();
      return true;
    },
    setBioshipMode: function (mode) {
      init();
      applyBioshipMode(mode || "all");
      return true;
    },
    getTierSummary: function () {
      return getTierSummary();
    },
    getSearchEntries: function () {
      return searchEntries.slice();
    },
  };
})(window, window.jQuery);
