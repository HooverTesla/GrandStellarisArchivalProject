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

      statusNode.off("click");
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
        const parentId = nodeData && nodeData.parentId;
        if (typeof parentId === "undefined") {
          event.stopPropagation();
          return;
        }

        if (parentId > 0) {
          const chart = charts[area];
          const parent = chart && chart.tree && chart.tree.nodeDB && chart.tree.nodeDB.db
            ? chart.tree.nodeDB.db[parentId]
            : null;
          if (!parent || !$("#" + parent.nodeHTMLid + " div.node-status").hasClass("active")) {
            event.stopPropagation();
            return;
          }
        }

        let prerequisitesMet = true;
        node.find("span.node-status").each(function () {
          const tech = this.classList[1];
          const prereq = $("#" + tech).find("div.node-status");
          if (prereq.length && !prereq.hasClass("active")) {
            prerequisitesMet = false;
          }
        });
        if (!prerequisitesMet) {
          event.stopPropagation();
          return;
        }

        const active = status.hasClass("active");
        if (typeof window.updateResearch === "function") {
          window.updateResearch(area, nodeId, !active);
        } else {
          status.toggleClass("active", !active);
          node.toggleClass("active", !active);
        }
        event.stopPropagation();
      });

      statusNode.data("sttBound", true).addClass("status-loaded");
    });
  }

  function ensureStatusBindings(area) {
    if (typeof window.init_nodestatus === "function") {
      window.init_nodestatus(area);
    }
    bindMissingStatusHandlers(area);
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
        acc.push(...tree.querySelectorAll(".node.tech"));
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
    $("#tech-tree-search").addClass("float-NoDisplay");
    $("#tech-tree-physics").addClass("float-NoDisplay");
    $("#tech-tree-society").addClass("float-NoDisplay");
    $("#tech-tree-engineering").addClass("float-NoDisplay");
    $("#tech-tree-anomalies").addClass("float-NoDisplay");

    if (area === "all") {
      $("#tech-tree-physics").removeClass("float-NoDisplay");
      $("#tech-tree-society").removeClass("float-NoDisplay");
      $("#tech-tree-engineering").removeClass("float-NoDisplay");
    } else if (area === "physics") {
      $("#tech-tree-physics").removeClass("float-NoDisplay");
    } else if (area === "society") {
      $("#tech-tree-society").removeClass("float-NoDisplay");
    } else if (area === "engineering") {
      $("#tech-tree-engineering").removeClass("float-NoDisplay");
    } else if (area === "events" || area === "anomalies") {
      $("#tech-tree-anomalies").removeClass("float-NoDisplay");
    }

    setup_search();
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
    });

    if (typeof window.initDB === "function" && window.indexedDB) {
      window.initDB();
    } else if (typeof window.setupLocalStorage === "function" && window.localStorage) {
      window.setupLocalStorage();
    }
  }

  function init() {
    if (initialized) {
      return;
    }
    if (!document.querySelector("#tech-tree")) {
      return;
    }
    initialized = true;
    load_tree();
    applyArea("all");
    setup_search();
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
  };
})(window, window.jQuery);
