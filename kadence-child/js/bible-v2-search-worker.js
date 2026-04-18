"use strict";

var searchIndex = null;
var docsById = {};

function normalizeText(value) {
  return (value || "").toString().trim();
}

function normalizeSearchValue(value) {
  var normalized = normalizeText(value);
  if (!normalized) {
    return "";
  }

  normalized = normalized.normalize("NFKC");
  normalized = normalized
    .replace(/[œŒ]/g, function (match) { return match === "Œ" ? "OE" : "oe"; })
    .replace(/[æÆ]/g, function (match) { return match === "Æ" ? "AE" : "ae"; })
    .replace(/[\u2018\u2019\u201B\u2032\u02BC\u0060\u00B4]/g, "'")
    .replace(/[\u2010\u2011\u2012\u2013\u2014\u2212]/g, "-");
  normalized = normalized.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  normalized = normalized.toLowerCase();
  normalized = normalized.replace(/[-'\s]+/g, " ");
  normalized = normalized.replace(/[^a-z0-9 ]+/g, " ");
  normalized = normalized.replace(/\s+/g, " ").trim();

  return normalized;
}

function compactSearchValue(value) {
  return normalizeSearchValue(value).replace(/\s+/g, "");
}

function getTrigrams(value) {
  var trigrams = [];
  var seen = Object.create(null);

  if (!value || value.length < 3) {
    return trigrams;
  }

  for (var index = 0; index <= value.length - 3; index += 1) {
    var trigram = value.slice(index, index + 3);
    if (!seen[trigram]) {
      seen[trigram] = true;
      trigrams.push(trigram);
    }
  }

  return trigrams;
}

function addScore(scoreMap, conceptId, amount) {
  scoreMap[conceptId] = (scoreMap[conceptId] || 0) + amount;
}

function overlapScore(queryCompact, formCompact) {
  if (!queryCompact || !formCompact || queryCompact.length < 3 || formCompact.length < 3) {
    return 0;
  }

  var queryTrigrams = getTrigrams(queryCompact);
  var formTrigrams = Object.create(null);
  var score = 0;

  getTrigrams(formCompact).forEach(function (trigram) {
    formTrigrams[trigram] = true;
  });

  queryTrigrams.forEach(function (trigram) {
    if (formTrigrams[trigram]) {
      score += 1;
    }
  });

  return score;
}

function buildDocsIndex() {
  docsById = {};
  (searchIndex.docs || []).forEach(function (doc) {
    docsById[doc.concept_id] = doc;
  });
}

function scoreDocument(doc, queryNormalized, queryCompact, baseScore) {
  var score = baseScore || 0;
  var forms = Array.isArray(doc.search_forms) ? doc.search_forms : [];

  forms.forEach(function (form) {
    var normalized = normalizeText(form.normalized);
    var compact = normalizeText(form.compact);
    var weight = Number(form.weight || 0);

    if (normalized === queryNormalized) {
      score += weight + 600;
    } else if (queryCompact && compact === queryCompact) {
      score += weight + 560;
    } else if (queryCompact && compact.indexOf(queryCompact) === 0) {
      score += weight + 260;
    } else if (normalized.indexOf(queryNormalized) === 0) {
      score += weight + 210;
    } else if (normalized.indexOf(queryNormalized) !== -1) {
      score += weight + 120;
    } else if (queryCompact && compact.indexOf(queryCompact) !== -1) {
      score += weight + 100;
    }

    score += overlapScore(queryCompact, compact) * 12;
  });

  if (doc.status === "ready") {
    score += 20;
  }

  return score;
}

function runSearch(query) {
  var queryNormalized = normalizeSearchValue(query);
  var queryCompact = compactSearchValue(query);
  var candidates = Object.create(null);
  var prefixKey;

  if (!queryNormalized || queryNormalized.length < 2) {
    return [];
  }

  (searchIndex.exact_map[queryNormalized] || []).forEach(function (conceptId) {
    addScore(candidates, conceptId, 1200);
  });

  if (queryCompact.length >= (searchIndex.params.min_prefix_length || 2)) {
    prefixKey = queryCompact.slice(0, Math.min(queryCompact.length, searchIndex.params.max_prefix_length || 12));
    (searchIndex.prefix_map[prefixKey] || []).forEach(function (conceptId) {
      addScore(candidates, conceptId, 320);
    });
  }

  if (queryCompact.length >= (searchIndex.params.trigram_length || 3)) {
    getTrigrams(queryCompact).forEach(function (trigram) {
      (searchIndex.trigram_map[trigram] || []).forEach(function (conceptId) {
        addScore(candidates, conceptId, 40);
      });
    });
  }

  return Object.keys(candidates)
    .map(function (conceptId) {
      var doc = docsById[conceptId];
      if (!doc) {
        return null;
      }

      return Object.assign({}, doc, {
        score: scoreDocument(doc, queryNormalized, queryCompact, candidates[conceptId])
      });
    })
    .filter(Boolean)
    .sort(function (left, right) {
      if (right.score !== left.score) {
        return right.score - left.score;
      }
      return normalizeText(left.label).localeCompare(normalizeText(right.label), "fr", { sensitivity: "base" });
    })
    .slice(0, 20);
}

self.addEventListener("message", function (event) {
  var payload = event.data || {};

  if (payload.type === "init") {
    fetch(payload.indexUrl)
      .then(function (response) {
        if (!response.ok) {
          throw new Error("search_index_unavailable");
        }
        return response.json();
      })
      .then(function (indexPayload) {
        searchIndex = indexPayload;
        buildDocsIndex();
        self.postMessage({
          type: "ready",
          docsCount: searchIndex.docs_count || 0
        });
      })
      .catch(function (error) {
        self.postMessage({
          type: "error",
          message: error && error.message ? error.message : "search_index_unavailable"
        });
      });

    return;
  }

  if (payload.type === "search") {
    if (!searchIndex) {
      self.postMessage({
        type: "error",
        requestId: payload.requestId,
        message: "search_index_not_ready"
      });
      return;
    }

    try {
      self.postMessage({
        type: "results",
        requestId: payload.requestId,
        results: runSearch(payload.query)
      });
    } catch (error) {
      self.postMessage({
        type: "error",
        requestId: payload.requestId,
        message: error && error.message ? error.message : "search_failed"
      });
    }
  }
});
