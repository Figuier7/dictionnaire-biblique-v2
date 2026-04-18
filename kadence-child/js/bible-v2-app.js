(function () {
  "use strict";

  var config = window.FIGUIER_BIBLE_V2_CONFIG || {};
  var APP_SELECTOR = '.figuier-bible-app[data-app="bible-v2"]';
  var SOURCE_FILE_BY_ID = {
    bym_lexicon: "bym_entries",
    easton: "easton_entries",
    smith: "smith_entries"
  };
  var SOURCE_ORDER = ['bym_lexicon', 'easton', 'smith', 'isbe'];

  var SOURCE_LABELS = {
    bym_lexicon: 'Lexique BYM',
    easton: 'Easton',
    smith: 'Smith',
    isbe: 'Encyclop\u00e9die'
  };

  var SOURCE_COLORS = {
    bym_lexicon: 'bym',
    easton: 'easton',
    smith: 'smith',
    isbe: 'isbe'
  };

  var SOURCE_ROLE_LABELS = {
    bym_lexicon: 'Lexique',
    easton: 'Définition',
    smith: 'Approfondissement',
    isbe: 'Encyclopédie'
  };

  var SOURCE_ROLE_COLORS = {
    bym_lexicon: { bg: '#fdf6ec', text: '#8b6914', border: '#d4a95a' },
    easton: { bg: '#f5f0ea', text: '#5e3f22', border: '#7e5d43' },
    smith: { bg: '#f0f4ef', text: '#3d5a38', border: '#5a7a55' },
    isbe: { bg: '#f2f0f6', text: '#4a3d66', border: '#6b5b8a' }
  };

  function estimateReadingTime(text) {
    if (!text) return '';
    var words = text.split(/\s+/).length;
    var minutes = Math.max(1, Math.ceil(words / 200));
    return '~' + minutes + ' min';
  }

  function extractBiblicalReferences(text) {
    if (!text) return [];
    var refPattern = /\b((?:Ge|Gen|Ex|Le|Lév|No|Nomb|De|Deut|Jos|Jg|Jug|1\s?S(?:am)?|2\s?S(?:am)?|1\s?R(?:ois)?|2\s?R(?:ois)?|Es|Ésa|Je|Jér|Ez|Éz|Os|Jo|Joël?|Am|Ab|Abd|Jon|Mi|Mic|Na|Nah|Ha|Hab|So|Soph|Ag|Agg|Za|Zach|Mal|Ps|Pr|Prov|Job|Ca|Cant|Rt|Ruth|La|Lam|Ec|Eccl|Est|Da|Dan|Esd|Ne|Néh|1\s?Ch(?:r)?|2\s?Ch(?:r)?|Mt|Matt|Mc|Marc|Lu|Luc|Jn|Jean|Ac|Act|Ja|Jacq|Ga|Gal|1\s?Th|2\s?Th|1\s?Co(?:r)?|2\s?Co(?:r)?|Ro|Rom|Ep|Éph|Ph|Phil|Col|Phm|1\s?Ti(?:m)?|2\s?Ti(?:m)?|Tit|Tite|1\s?Pi|2\s?Pi|Jud|Jude|He|Héb|1\s?Jn|2\s?Jn|3\s?Jn|Ap|Apoc)\.?\s+\d+:\d+(?:-\d+)?)\b/g;
    var matches = [];
    var seen = {};
    var match;
    while ((match = refPattern.exec(text)) !== null) {
      var ref = match[1].replace(/\s+/g, ' ').trim();
      if (!seen[ref] && matches.length < 8) {
        seen[ref] = true;
        matches.push(ref);
      }
    }
    return matches;
  }

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

  function escapeHtml(value) {
    return normalizeText(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function uniqueStrings(values) {
    var seen = {};
    var items = [];

    (Array.isArray(values) ? values : []).forEach(function (value) {
      var text = normalizeText(value);
      var key = normalizeSearchValue(text);
      if (!text || !key || seen[key]) {
        return;
      }

      seen[key] = true;
      items.push(text);
    });

    return items;
  }

  // Taxonomie etendue : 20 categories actives (post-retypage 2026-04-16)
  // `tribu` et `non_classifie` gardes pour retrocompat (cas residuels)
  var CATEGORY_MAP = {
    personnage: "Personnage",
    etre_spirituel: "\u00catre spirituel",
    lieu: "Lieu",
    lieu_sacre: "Lieu sacr\u00e9",
    peuple: "Peuple",
    tribu: "Tribu",
    livre_biblique: "Livre biblique",
    doctrine: "Doctrine",
    rite: "Rite",
    institution: "Institution",
    fonction: "Fonction",
    objet_sacre: "Objet sacr\u00e9",
    objets_et_vetements: "Objets et v\u00eatements",
    plante: "Plante",
    animal: "Animal",
    alimentation_et_agriculture: "Alimentation et agriculture",
    corps_et_sante: "Corps et sant\u00e9",
    mesures_et_temps: "Mesures et temps",
    matiere: "Mati\u00e8re",
    evenement: "\u00c9v\u00e9nement",
    nature: "Nature",
    non_classifie: "Non classifi\u00e9"
  };

  var CATEGORY_EMOJI = {
    personnage: "\ud83d\udc64",         // 👤
    etre_spirituel: "\ud83d\udc7c",     // 👼
    lieu: "\ud83c\udfdb\ufe0f",         // 🏛️
    lieu_sacre: "\ud83d\udd4d",         // 🕍 synagogue/temple
    peuple: "\ud83c\udf0d",             // 🌍
    tribu: "\u26fa",                   // ⛺
    livre_biblique: "\ud83d\udcd6",     // 📖
    doctrine: "\u2728",                // ✨
    rite: "\ud83d\udd4a\ufe0f",         // 🕊️
    institution: "\ud83c\udfe0",        // 🏠
    fonction: "\ud83c\udf96\ufe0f",     // 🎖️ titre/role
    objet_sacre: "\ud83d\udd6f\ufe0f",  // 🕯️
    objets_et_vetements: "\ud83e\uddf5", // 🧵
    plante: "\ud83c\udf3f",             // 🌿
    animal: "\ud83d\udc3e",             // 🐾
    alimentation_et_agriculture: "\ud83c\udf3e", // 🌾
    corps_et_sante: "\u2764\ufe0f",    // ❤️
    mesures_et_temps: "\u23f3",        // ⏳
    matiere: "\ud83d\udc8e",            // 💎
    evenement: "\ud83d\udcc5",          // 📅
    nature: "\ud83c\udfde\ufe0f",       // 🏞️
    non_classifie: "\ud83d\udcc1"       // 📁
  };

  function formatCategoryLabel(category) {
    return CATEGORY_MAP[category] || normalizeText(category).replace(/_/g, " ");
  }

  function formatCategoryLabelWithEmoji(category) {
    var emoji = CATEGORY_EMOJI[category] || "";
    var label = formatCategoryLabel(category);
    return emoji ? emoji + " " + label : label;
  }

  function getConceptPublicForms(concept) {
    var publicForms = concept && concept.public_forms ? concept.public_forms : {};
    return {
      restoredReference: normalizeText(publicForms.restored_reference || concept && concept.label_restore || ""),
      frenchReference: normalizeText(publicForms.french_reference || concept && concept.label || ""),
      other: uniqueStrings(publicForms.other_forms || publicForms.secondary_labels || []),
      english: uniqueStrings(publicForms.english_labels || []),
      aliasesPublic: uniqueStrings(publicForms.aliases_public || [])
    };
  }

  function getFirstPublicSecondaryLabel(concept, fallback) {
    var displayTitles = getConceptDisplayTitles(concept);
    if (displayTitles.secondary) {
      return displayTitles.secondary;
    }
    return normalizeText(fallback);
  }

  function getConceptDisplayTitles(concept) {
    var displayTitles = concept && concept.display_titles ? concept.display_titles : {};
    var primary = normalizeText(displayTitles.primary);
    var secondary = normalizeText(displayTitles.secondary);
    var strategy = normalizeText(displayTitles.strategy);

    if (!primary) {
      primary = normalizeText(concept && (concept.label_restore || concept.label || concept.concept_id));
    }

    if (!strategy) {
      strategy = secondary ? "restored_first" : "french_only";
    }

    return {
      strategy: strategy,
      primary: primary,
      secondary: secondary
    };
  }

  function getBrowsePaginationConfig(appConfig) {
    var browseConfig = appConfig && appConfig.browse ? appConfig.browse : {};
    return {
      homeLetterPreviewSize: Number(browseConfig.homeLetterPreviewSize || 6),
      homeCategoryPreviewSize: Number(browseConfig.homeCategoryPreviewSize || 4),
      letterPageSize: Number(browseConfig.letterPageSize || 12),
      categoryDirectoryPageSize: Number(browseConfig.categoryDirectoryPageSize || 6),
      categoryConceptPageSize: Number(browseConfig.categoryConceptPageSize || 12)
    };
  }

  function paginateItems(items, page, pageSize) {
    var safeItems = Array.isArray(items) ? items : [];
    var safePageSize = Math.max(1, Number(pageSize || 1));
    var totalPages = Math.max(1, Math.ceil(safeItems.length / safePageSize));
    var safePage = Math.min(Math.max(1, Number(page || 1)), totalPages);
    var start = (safePage - 1) * safePageSize;

    return {
      page: safePage,
      pageSize: safePageSize,
      totalItems: safeItems.length,
      totalPages: totalPages,
      items: safeItems.slice(start, start + safePageSize)
    };
  }

  function getFirstLetter(value) {
    var text = normalizeText(value);
    if (!text) {
      return "#";
    }

    text = text.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    text = text.replace(/^[^A-Za-z0-9]+/, "");
    if (!text) {
      return "#";
    }

    return text.charAt(0).toUpperCase();
  }

  function compareBrowseItems(a, b) {
    return normalizeText(a.display_title_primary || a.label || a.concept_id).localeCompare(
      normalizeText(b.display_title_primary || b.label || b.concept_id),
      "fr",
      { sensitivity: "base" }
    );
  }

  function buildBrowseIndexFromConcepts(concepts) {
    var conceptList = Array.isArray(concepts) ? concepts : [];
    var letterMap = {};
    var categoryMap = {};

    conceptList.forEach(function (concept) {
      if (!concept || concept.status === "blocked" || concept.navigation_visibility === "hidden") {
        return;
      }

      var displayTitles = getConceptDisplayTitles(concept);
      var label = normalizeText(concept.label || concept.concept_id);
      if (!label && !displayTitles.primary) {
        return;
      }

      var item = {
        concept_id: normalizeText(concept.concept_id),
        label: label,
        display_title_primary: displayTitles.primary || label,
        display_title_secondary: displayTitles.secondary || "",
        alpha_letter: normalizeText(concept.alpha_letter) || getFirstLetter(displayTitles.primary || label),
        category: normalizeText(concept.category),
        other_form: getConceptPublicForms(concept).restoredReference,
        status: normalizeText(concept.status) || "ready"
      };

      if (!item.alpha_letter) {
        item.alpha_letter = "#";
      }

      if (!letterMap[item.alpha_letter]) {
        letterMap[item.alpha_letter] = [];
      }
      letterMap[item.alpha_letter].push(item);

      if (item.category) {
        if (!categoryMap[item.category]) {
          categoryMap[item.category] = [];
        }
        categoryMap[item.category].push(item);
      }
    });

    var letters = Object.keys(letterMap).sort().map(function (letter) {
      var items = letterMap[letter].sort(compareBrowseItems);
      return {
        letter: letter,
        count: items.length,
        preview_items: items.slice(0, 6),
        items: items
      };
    });

    var categories = Object.keys(categoryMap).sort(function (left, right) {
      return normalizeText(formatCategoryLabel(left)).localeCompare(
        normalizeText(formatCategoryLabel(right)),
        "fr",
        { sensitivity: "base" }
      );
    }).map(function (category) {
      var items = categoryMap[category].sort(compareBrowseItems);
      return {
        category: category,
        count: items.length,
        preview_items: items.slice(0, 4),
        items: items
      };
    });

    return {
      version: "client-fallback",
      generated_at: "",
      letters: letters,
      categories: categories
    };
  }

  function excerptText(value, maxLength) {
    var clean = normalizeText(value).replace(/\s+/g, " ");
    if (clean.length <= maxLength) {
      return clean;
    }

    return clean.slice(0, maxLength).replace(/\s+\S*$/, "").trim() + "...";
  }

  function renderRichText(value) {
    var text = normalizeText(value);
    if (!text) {
      return "<p></p>";
    }

    if (window.marked && typeof window.marked.parse === "function") {
      return window.marked.parse(text);
    }

    return text
      .split(/\n{2,}/)
      .map(function (paragraph) {
        return "<p>" + escapeHtml(paragraph).replace(/\n/g, "<br>") + "</p>";
      })
      .join("");
  }

  function debounce(fn, delay) {
    var timer = null;
    return function () {
      var args = arguments;
      var context = this;
      window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        fn.apply(context, args);
      }, delay);
    };
  }

  function readJsonLines(text) {
    return text
      .split(/\r?\n/)
      .map(function (line) {
        return line.trim();
      })
      .filter(Boolean)
      .map(function (line) {
        return JSON.parse(line);
      });
  }

  function buildSearchFallbackScore(doc, queryNormalized, queryCompact) {
    var score = 0;
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
    });

    if (doc.status === "ready") {
      score += 20;
    }

    return score;
  }

  function BibleDataStore(appConfig) {
    this.config = appConfig || {};
    this.manifest = null;
    this.concepts = null;
    this.conceptMap = null;
    this.conceptLinks = null;
    this.browseIndex = null;
    this.sourceMap = null;
    this.entryCaches = {};
    this.entryIndexes = {};
    this.searchDocs = null;
    this.worker = null;
    this.workerReadyPromise = null;
    this.workerPending = {};
    this.workerRequestId = 0;
  }

  BibleDataStore.prototype.resolveManifestFileUrl = function (fileKey) {
    if (!this.manifest || !this.manifest.files || !this.manifest.files[fileKey]) {
      return "";
    }

    var relativePath = this.manifest.files[fileKey];
    var uploadsBase = this.manifest.uploads_base || "/wp-content/uploads/dictionnaires/";
    var resolved = new URL(relativePath, window.location.origin + uploadsBase).toString();
    if (this.manifest.version) {
      resolved += (resolved.indexOf('?') === -1 ? '?' : '&') + 'v=' + encodeURIComponent(this.manifest.version);
    }
    return resolved;
  };

  BibleDataStore.prototype.loadManifest = async function () {
    if (this.manifest) {
      return this.manifest;
    }

    var response = await fetch(this.config.manifestUrl, { credentials: "same-origin" });
    if (!response.ok) {
      throw new Error("manifest_unavailable");
    }

    this.manifest = await response.json();
    this.sourceMap = {};
    (this.manifest.sources || []).forEach(function (source) {
      this.sourceMap[source.id] = source;
    }, this);

    return this.manifest;
  };

  BibleDataStore.prototype.loadBootstrap = async function () {
    await this.loadManifest();

    if (!this.concepts) {
      var conceptsUrl = this.resolveManifestFileUrl("concepts");
      var conceptLinksUrl = this.resolveManifestFileUrl("concept_links");
      var browseUrl = this.resolveManifestFileUrl("browse_index");
      var requests = [
        fetch(conceptsUrl, { credentials: "same-origin" }),
        fetch(conceptLinksUrl, { credentials: "same-origin" })
      ];

      if (browseUrl) {
        requests.push(fetch(browseUrl, { credentials: "same-origin" }));
      }

      var results = await Promise.all(requests);

      if (!results[0].ok || !results[1].ok) {
        throw new Error("concept_artifacts_unavailable");
      }

      this.concepts = await results[0].json();
      this.conceptLinks = await results[1].json();
      if (results[2] && results[2].ok) {
        this.browseIndex = await results[2].json();
      } else {
        this.browseIndex = { letters: [], categories: [] };
      }
      if (!this.browseIndex || !Array.isArray(this.browseIndex.letters) || this.browseIndex.letters.length === 0) {
        this.browseIndex = buildBrowseIndexFromConcepts(this.concepts);
      }
      this.conceptMap = {};
      this.concepts.forEach(function (concept) {
        this.conceptMap[concept.concept_id] = concept;
      }, this);
    }

    return {
      manifest: this.manifest,
      concepts: this.concepts,
      conceptLinks: this.conceptLinks,
      browseIndex: this.browseIndex
    };
  };

  BibleDataStore.prototype.getBrowseIndex = function () {
    if ((!this.browseIndex || !Array.isArray(this.browseIndex.letters) || this.browseIndex.letters.length === 0) && this.concepts) {
      this.browseIndex = buildBrowseIndexFromConcepts(this.concepts);
    }
    return this.browseIndex || { letters: [], categories: [] };
  };

  BibleDataStore.prototype.ensureEntries = async function (dictionaryId) {
    if (this.entryCaches[dictionaryId]) {
      return this.entryCaches[dictionaryId];
    }

    await this.loadManifest();

    var manifestKey = SOURCE_FILE_BY_ID[dictionaryId];
    if (!manifestKey && this.manifest && this.manifest.files && this.manifest.files[dictionaryId + "_entries"]) {
      manifestKey = dictionaryId + "_entries";
    }
    if (!manifestKey) {
      return [];
    }

    var url = this.resolveManifestFileUrl(manifestKey);
    var response = await fetch(url, { credentials: "same-origin" });

    if (!response.ok) {
      // Monolithic file missing — try letter-split files (e.g. isbe-A.json … isbe-Z.json)
      var allEntries = await this._loadSplitEntries(dictionaryId);
      if (allEntries.length > 0) {
        this.entryCaches[dictionaryId] = allEntries;
        this.entryIndexes[dictionaryId] = {};
        allEntries.forEach(function (entry) {
          this.entryIndexes[dictionaryId][entry.id] = entry;
        }, this);
        return allEntries;
      }
      // No split files either — graceful fallback
      this.entryCaches[dictionaryId] = [];
      this.entryIndexes[dictionaryId] = {};
      return [];
    }

    var payload = await response.json();
    var entries = Array.isArray(payload)
      ? payload
      : (payload && Array.isArray(payload.value) ? payload.value : []);
    this.entryCaches[dictionaryId] = entries;
    this.entryIndexes[dictionaryId] = {};
    entries.forEach(function (entry) {
      this.entryIndexes[dictionaryId][entry.id] = entry;
    }, this);

    return entries;
  };

  /**
   * Load letter-split dictionary files (e.g. isbe-A.json … isbe-Z.json).
   * Checks manifest for keys like isbe_entries_A, isbe_entries_B, etc.
   */
  BibleDataStore.prototype._loadSplitEntries = async function (dictionaryId) {
    var letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
    var self = this;
    var urls = [];
    for (var i = 0; i < letters.length; i++) {
      var key = dictionaryId + '_entries_' + letters[i];
      if (this.manifest && this.manifest.files && this.manifest.files[key]) {
        urls.push(this.resolveManifestFileUrl(key));
      }
    }
    if (urls.length === 0) return [];

    var responses = await Promise.all(urls.map(function (u) {
      return fetch(u, { credentials: "same-origin" }).catch(function () { return null; });
    }));

    var allEntries = [];
    for (var r = 0; r < responses.length; r++) {
      if (responses[r] && responses[r].ok) {
        try {
          var payload = await responses[r].json();
          var arr = Array.isArray(payload) ? payload : (payload && Array.isArray(payload.value) ? payload.value : []);
          allEntries = allEntries.concat(arr);
        } catch (e) { /* skip malformed */ }
      }
    }
    return allEntries;
  };

  BibleDataStore.prototype.getEntryById = async function (dictionaryId, entryId) {
    await this.ensureEntries(dictionaryId);
    return this.entryIndexes[dictionaryId][entryId] || null;
  };

  BibleDataStore.prototype.getConceptById = function (conceptId) {
    return this.conceptMap ? this.conceptMap[conceptId] || null : null;
  };

  BibleDataStore.prototype.ensureSearchDocs = async function () {
    if (this.searchDocs) {
      return this.searchDocs;
    }

    await this.loadManifest();

    var docsUrl = this.resolveManifestFileUrl("search_docs");
    if (!docsUrl) {
      this.searchDocs = [];
      return this.searchDocs;
    }

    var response = await fetch(docsUrl, { credentials: "same-origin" });
    if (!response.ok) {
      throw new Error("search_docs_unavailable");
    }

    this.searchDocs = readJsonLines(await response.text());
    return this.searchDocs;
  };

  BibleDataStore.prototype.ensureSearchWorker = async function () {
    if (this.workerReadyPromise) {
      return this.workerReadyPromise;
    }

    await this.loadManifest();

    var workerUrl = this.config.workerUrl;
    var searchIndexUrl = this.resolveManifestFileUrl("search_index");
    if (!workerUrl || !searchIndexUrl || typeof window.Worker !== "function") {
      throw new Error("worker_unavailable");
    }

    this.worker = new Worker(workerUrl);
    this.worker.onmessage = this.handleWorkerMessage.bind(this);
    this.worker.onerror = this.handleWorkerError.bind(this);

    this.workerReadyPromise = new Promise(function (resolve, reject) {
      this.workerPending.__init__ = { resolve: resolve, reject: reject };
      this.worker.postMessage({
        type: "init",
        indexUrl: searchIndexUrl
      });
    }.bind(this));

    return this.workerReadyPromise;
  };

  BibleDataStore.prototype.handleWorkerMessage = function (event) {
    var payload = event.data || {};

    if (payload.type === "ready") {
      if (this.workerPending.__init__) {
        this.workerPending.__init__.resolve(payload);
        delete this.workerPending.__init__;
      }
      return;
    }

    if (payload.type === "error") {
      if (payload.requestId && this.workerPending[payload.requestId]) {
        this.workerPending[payload.requestId].reject(new Error(payload.message || "worker_error"));
        delete this.workerPending[payload.requestId];
      } else if (this.workerPending.__init__) {
        this.workerPending.__init__.reject(new Error(payload.message || "worker_init_error"));
        delete this.workerPending.__init__;
      }
      return;
    }

    if (payload.type === "results" && payload.requestId && this.workerPending[payload.requestId]) {
      this.workerPending[payload.requestId].resolve(payload.results || []);
      delete this.workerPending[payload.requestId];
    }
  };

  BibleDataStore.prototype.handleWorkerError = function (error) {
    if (this.workerPending.__init__) {
      this.workerPending.__init__.reject(error);
      delete this.workerPending.__init__;
    }
  };

  BibleDataStore.prototype.searchConcepts = async function (query) {
    var cleanedQuery = normalizeText(query);
    if (cleanedQuery.length < 2) {
      return [];
    }

    try {
      await this.ensureSearchWorker();
      var requestId = "q" + (++this.workerRequestId);
      return await new Promise(function (resolve, reject) {
        this.workerPending[requestId] = { resolve: resolve, reject: reject };
        this.worker.postMessage({
          type: "search",
          requestId: requestId,
          query: cleanedQuery
        });
      }.bind(this));
    } catch (workerError) {
      return this.searchConceptsFallback(cleanedQuery);
    }
  };

  BibleDataStore.prototype.searchConceptsFallback = async function (query) {
    var docs = await this.ensureSearchDocs();
    var normalized = normalizeSearchValue(query);
    var compact = compactSearchValue(query);

    return docs
      .map(function (doc) {
        return Object.assign({ score: buildSearchFallbackScore(doc, normalized, compact) }, doc);
      })
      .filter(function (doc) {
        return doc.score > 0;
      })
      .sort(function (left, right) {
        if (right.score !== left.score) {
          return right.score - left.score;
        }
        return normalizeText(left.label).localeCompare(normalizeText(right.label), "fr", { sensitivity: "base" });
      })
      .slice(0, 20);
  };

  function BibleV2App(root, appConfig) {
    this.root = root;
    this.config = appConfig || {};
    this.labels = (this.config && this.config.labels) || {};
    this.browseConfig = getBrowsePaginationConfig(this.config);
    this.store = new BibleDataStore(this.config);
    this.searchInput = root.querySelector(".fb-search-input");
    this.searchClearButton = root.querySelector(".fb-search-clear");
    this.searchStatus = root.querySelector(".fb-search-status");
    this.navBackButton = root.querySelector(".fb-nav-back");
    this.searchPanel = root.querySelector(".fb-search-panel");
    this.conceptSlot = root.querySelector(".fb-concept-slot");
    this.readingPanel = root.querySelector(".fb-reading-panel");
    this.primePromise = null;
    this.state = {
      view: "idle",
      query: "",
      results: [],
      activeResultIndex: -1,
      activeConceptId: "",
      isSearching: false,
      activeReading: null,
      browseView: "home",
      activeBrowseLetter: "",
      activeBrowseLetterPage: 1,
      activeBrowseCategory: "",
      activeBrowseCategoryPage: 1,
      activeCategoryDirectoryPage: 1,
      lastEntryView: "idle"
    };
    this.searchDebounced = debounce(this.handleSearchInput.bind(this), 140);
  }

  /**
   * Charge le fichier concept-url-slugs.json (concept_id → slug français).
   * Utilisé pour générer des URLs avec les noms francisés.
   */
  BibleV2App.prototype.loadUrlSlugs = async function () {
    this._urlSlugs = {};
    this._reverseUrlSlugs = {};
    var url = this.config.urlSlugsUrl;
    if (!url) return;
    try {
      var resp = await fetch(url);
      if (resp.ok) {
        this._urlSlugs = await resp.json();
        // Build reverse map (slug → concept_id)
        for (var cid in this._urlSlugs) {
          if (this._urlSlugs.hasOwnProperty(cid)) {
            this._reverseUrlSlugs[this._urlSlugs[cid]] = cid;
          }
        }
      }
    } catch (e) {
      // Fallback silencieux — les URLs utiliseront le concept_id
    }
  };

  /**
   * Retourne le slug d'URL français pour un concept_id donné.
   */
  BibleV2App.prototype.getUrlSlug = function (conceptId) {
    if (this._urlSlugs && this._urlSlugs[conceptId]) {
      return this._urlSlugs[conceptId];
    }
    return conceptId;
  };

  /**
   * Résout un slug d'URL en concept_id.
   * Accepte un slug français ou un concept_id direct.
   */
  BibleV2App.prototype.resolveUrlSlug = function (slug) {
    if (!slug) return null;
    slug = decodeURIComponent(slug);
    // Direct concept_id?
    if (this.store.getConceptById(slug)) return slug;
    // French slug?
    if (this._reverseUrlSlugs && this._reverseUrlSlugs[slug]) {
      return this._reverseUrlSlugs[slug];
    }
    return slug;
  };

  BibleV2App.prototype.init = async function () {
    if (this.searchInput && this.labels.search_placeholder) {
      this.searchInput.setAttribute("placeholder", this.labels.search_placeholder);
    }

    this.setSearchStatus(this.labels.loading || "Chargement...");
    this.bindEvents();

    try {
      await this.store.loadBootstrap();
      await this.loadUrlSlugs();
      this.initializeBrowseState();
      this.renderIdleState();
      this.renderSearchPrompt();
      this.setView("idle");
      this.setSearchStatus(this.labels.search_empty || "Recherchez un concept biblique.");
      this.primeSearchEarly();
      this.resolveInitialRoute();
    } catch (error) {
      this.renderErrorState(this.labels.search_error || "L'interface n'a pas pu etre initialisee.");
      this.setSearchStatus(this.labels.search_error || "L'interface n'a pas pu etre initialisee.");
    }
  };

  BibleV2App.prototype.bindEvents = function () {
    if (!this.searchInput) {
      return;
    }

    this.searchInput.addEventListener("focus", function () {
      this.openSearch();
      this.primeSearchEarly();
    }.bind(this));

    this.searchInput.addEventListener("input", function () {
      this.state.query = normalizeText(this.searchInput.value);
      this.state.isSearching = this.state.query.length >= 2;
      if (this.state.isSearching) {
        this.state.results = [];
        this.state.activeResultIndex = -1;
      }
      this.toggleClearButton();
      this.openSearch();
      this.searchDebounced();
    }.bind(this));

    this.searchInput.addEventListener("keydown", this.handleSearchKeydown.bind(this));

    if (this.searchClearButton) {
      this.searchClearButton.addEventListener("click", function () {
        this.resetSearch();
        this.searchInput.focus();
      }.bind(this));
    }

    if (this.navBackButton) {
      this.navBackButton.addEventListener("click", this.handleBackAction.bind(this));
    }

    if (this.searchPanel) {
      this.searchPanel.addEventListener("click", function (event) {
        var button = event.target.closest("[data-concept-id]");
        if (!button) {
          return;
        }

        event.preventDefault();
        this.openConcept(button.getAttribute("data-concept-id"), true);
      }.bind(this));
    }

    if (this.conceptSlot) {
      this.conceptSlot.addEventListener("click", function (event) {
        var readingButton = event.target.closest('[data-action="open-reading"]');
        if (!readingButton) {
          return;
        }

        event.preventDefault();
        this.openReading(
          readingButton.getAttribute("data-dictionary"),
          readingButton.getAttribute("data-entry-id"),
          readingButton.getAttribute("data-role")
        );
        return;
      }.bind(this));

      this.conceptSlot.addEventListener("click", function (event) {
        var conceptButton = event.target.closest("[data-concept-id]");
        if (conceptButton) {
          event.preventDefault();
          this.openConcept(conceptButton.getAttribute("data-concept-id"), true);
          return;
        }

        var browseAction = event.target.closest("[data-action]");
        if (!browseAction) {
          return;
        }

        event.preventDefault();
        switch (browseAction.getAttribute("data-action")) {
          case "open-browse-home":
            this.openBrowseHome();
            break;
          case "open-browse-letter":
            this.openBrowseLetter(browseAction.getAttribute("data-browse-letter") || "");
            break;
          case "open-browse-categories":
            this.openBrowseCategories();
            break;
          case "open-browse-category":
            this.openBrowseCategory(browseAction.getAttribute("data-browse-category") || "");
            break;
          case "paginate-letter":
            this.state.activeBrowseLetterPage = Math.max(1, this.state.activeBrowseLetterPage + Number(browseAction.getAttribute("data-page-delta") || 0));
            this.renderIdleState();
            break;
          case "paginate-categories":
            this.state.activeCategoryDirectoryPage = Math.max(1, this.state.activeCategoryDirectoryPage + Number(browseAction.getAttribute("data-page-delta") || 0));
            this.renderIdleState();
            break;
          case "paginate-category":
            this.state.activeBrowseCategoryPage = Math.max(1, this.state.activeBrowseCategoryPage + Number(browseAction.getAttribute("data-page-delta") || 0));
            this.renderIdleState();
            break;
        }
      }.bind(this));
    }

    if (this.readingPanel) {
      this.readingPanel.addEventListener("click", function (event) {
        var closeButton = event.target.closest('[data-action="close-reading"]');
        if (!closeButton) {
          return;
        }

        event.preventDefault();
        this.closeReading();
      }.bind(this));
    }

    // History API: handle back/forward navigation
    window.addEventListener("popstate", function (event) {
      if (event.state && event.state.conceptId) {
        this.openConcept(event.state.conceptId, false);
      } else {
        this.resolveInitialRoute();
      }
    }.bind(this));

    // Legacy hash support (backward compat)
    window.addEventListener("hashchange", function () {
      this.resolveInitialRoute();
    }.bind(this));
  };

  BibleV2App.prototype.setView = function (view) {
    this.state.view = view;
    this.root.setAttribute("data-view", view);

    if (this.searchPanel) {
      this.searchPanel.hidden = view !== "search";
    }

    if (this.readingPanel) {
      this.readingPanel.hidden = view !== "reading";
    }

    this.syncChrome();
  };

  BibleV2App.prototype.initializeBrowseState = function () {
    var browseIndex = this.store.getBrowseIndex();
    if (this.state.activeBrowseLetter) {
      return;
    }

    if (browseIndex.letters && browseIndex.letters.length > 0) {
      this.state.activeBrowseLetter = normalizeText(browseIndex.letters[0].letter);
    }

    if (!this.state.activeBrowseCategory && browseIndex.categories && browseIndex.categories.length > 0) {
      this.state.activeBrowseCategory = normalizeText(browseIndex.categories[0].category);
    }
  };

  BibleV2App.prototype.getBrowseGroupByLetter = function (letter) {
    var targetLetter = normalizeText(letter);
    var browseIndex = this.store.getBrowseIndex();
    return (Array.isArray(browseIndex.letters) ? browseIndex.letters : []).filter(function (item) {
      return normalizeText(item.letter) === targetLetter;
    })[0] || null;
  };

  BibleV2App.prototype.getBrowseGroupByCategory = function (category) {
    var targetCategory = normalizeText(category);
    var browseIndex = this.store.getBrowseIndex();
    return (Array.isArray(browseIndex.categories) ? browseIndex.categories : []).filter(function (item) {
      return normalizeText(item.category) === targetCategory;
    })[0] || null;
  };

  BibleV2App.prototype.openBrowseHome = function () {
    this.state.browseView = "home";
    this.state.activeBrowseLetterPage = 1;
    this.state.activeCategoryDirectoryPage = 1;
    this.state.activeBrowseCategoryPage = 1;
    this.renderIdleState();
    this.setView("idle");
  };

  BibleV2App.prototype.openBrowseLetter = function (letter) {
    if (normalizeText(letter)) {
      this.state.activeBrowseLetter = normalizeText(letter);
    }
    this.state.activeBrowseLetterPage = 1;
    this.state.browseView = "letter";
    this.renderIdleState();
    this.setView("idle");
  };

  BibleV2App.prototype.openBrowseCategories = function () {
    this.state.browseView = "categories";
    this.state.activeCategoryDirectoryPage = 1;
    this.renderIdleState();
    this.setView("idle");
  };

  BibleV2App.prototype.openBrowseCategory = function (category) {
    if (normalizeText(category)) {
      this.state.activeBrowseCategory = normalizeText(category);
    }
    this.state.activeBrowseCategoryPage = 1;
    this.state.browseView = "category";
    this.renderIdleState();
    this.setView("idle");
  };

  BibleV2App.prototype.getBrowseBackTarget = function () {
    if (this.state.browseView === "category") {
      return "categories";
    }
    if (this.state.browseView === "categories" || this.state.browseView === "letter") {
      return "home";
    }
    return "";
  };

  BibleV2App.prototype.getCanonicalConceptId = function (conceptId) {
    var concept = this.store.getConceptById(conceptId);
    if (!concept) {
      return conceptId;
    }

    var entries = Array.isArray(concept.entries) ? concept.entries : [];
    var related = Array.isArray(concept.related_concepts) ? concept.related_concepts : [];
    if (entries.length === 1 && entries[0].dictionary === "bym_lexicon") {
      var redirectRelation = related.filter(function (item) {
        return item && item.relation === "cross_reference" && normalizeText(item.concept_id);
      })[0];

      if (redirectRelation && this.store.getConceptById(redirectRelation.concept_id)) {
        return redirectRelation.concept_id;
      }
    }

    return conceptId;
  };

  BibleV2App.prototype.normalizeSearchResults = function (results) {
    var seen = {};
    var normalizedResults = [];

    (Array.isArray(results) ? results : []).forEach(function (result) {
      var canonicalConceptId = this.getCanonicalConceptId(result.concept_id);
      if (!canonicalConceptId || seen[canonicalConceptId]) {
        return;
      }

      var canonicalConcept = this.store.getConceptById(canonicalConceptId);
      var nextResult = Object.assign({}, result, {
        concept_id: canonicalConceptId
      });

      if (canonicalConcept) {
        nextResult.label = canonicalConcept.label || result.label;
        nextResult.label_restore = canonicalConcept.label_restore || result.label_restore || "";
        nextResult.category = canonicalConcept.category || result.category || "";
        nextResult.aliases = Array.isArray(canonicalConcept.aliases) ? canonicalConcept.aliases : (result.aliases || []);
      }

      normalizedResults.push(nextResult);
      seen[canonicalConceptId] = true;
    }.bind(this));

    return normalizedResults;
  };

  BibleV2App.prototype.syncChrome = function () {
    if (!this.navBackButton) {
      return;
    }

    var shouldShowBack = false;
    if (this.state.view === "reading") {
      shouldShowBack = true;
    } else if (this.state.view === "search") {
      shouldShowBack = true;
    } else if (this.state.view === "concept") {
      shouldShowBack = true;
    } else if (this.state.view === "idle" && this.state.browseView !== "home") {
      shouldShowBack = true;
    }

    this.navBackButton.hidden = !shouldShowBack;
    this.navBackButton.textContent = this.labels.back || "Retour";
  };

  BibleV2App.prototype.hasSearchContext = function () {
    return normalizeText(this.state.query).length >= 2 || this.state.results.length > 0;
  };

  BibleV2App.prototype.primeSearchEarly = function () {
    if (this.primePromise) {
      return this.primePromise;
    }

    this.primePromise = (async function () {
      try {
        await this.store.ensureSearchWorker();
      } catch (error) {
        await this.store.ensureSearchDocs();
      }
    }.bind(this))();

    return this.primePromise;
  };

  BibleV2App.prototype.resetSearch = function () {
    this.searchInput.value = "";
    this.state.query = "";
    this.state.results = [];
    this.state.activeResultIndex = -1;
    this.state.isSearching = false;
    this.toggleClearButton();
    this.renderSearchPrompt();
    this.setSearchStatus(this.labels.search_prompt || this.labels.search_empty || "");
    if (this.state.activeConceptId) {
      this.setView("concept");
    } else {
      this.setView("idle");
      this.renderIdleState();
    }
  };

  BibleV2App.prototype.openSearch = function () {
    this.setView("search");
    this.renderSearchState();
  };

  BibleV2App.prototype.closeSearch = function () {
    if (this.state.activeConceptId) {
      this.setView("concept");
    } else {
      this.setView("idle");
      this.renderIdleState();
    }
  };

  BibleV2App.prototype.handleBackAction = function () {
    if (this.state.view === "reading") {
      this.closeReading();
      return;
    }

    if (this.state.view === "search") {
      this.closeSearch();
      return;
    }

    if (this.state.view === "concept") {
      if (this.state.lastEntryView === "search") {
        this.openSearch();
      } else {
        this.state.activeConceptId = "";
        this.clearConceptHash();
        this.setView("idle");
        this.renderIdleState();
      }
      return;
    }

    if (this.state.view === "idle") {
      if (this.state.browseView === "category") {
        this.openBrowseCategories();
        return;
      }

      if (this.state.browseView === "categories" || this.state.browseView === "letter") {
        this.openBrowseHome();
      }
    }
  };

  BibleV2App.prototype.handleSearchInput = async function () {
    var query = normalizeText(this.searchInput.value);
    this.state.query = query;
    if (query.length < 2) {
      this.state.results = [];
      this.state.activeResultIndex = -1;
      this.state.isSearching = false;
      this.renderSearchPrompt();
      this.setSearchStatus(this.labels.search_prompt || this.labels.search_empty || "");
      return;
    }

    this.openSearch();
    this.state.isSearching = true;
    this.renderSearchLoading();
    this.setSearchStatus(this.labels.search_loading || "Preparation de la recherche...");

    try {
      var results = this.normalizeSearchResults(await this.store.searchConcepts(query));
      this.state.results = results;
      this.state.activeResultIndex = results.length > 0 ? 0 : -1;
      this.state.isSearching = false;
      this.renderSearchState();
      this.setSearchStatus(
        results.length > 0
          ? results.length + " concept(s) trouves."
          : (this.labels.search_no_results || "Aucun concept correspondant.")
      );
    } catch (error) {
      this.state.results = [];
      this.state.activeResultIndex = -1;
      this.state.isSearching = false;
      this.renderSearchError();
      this.setSearchStatus(this.labels.search_error || "La recherche n'a pas pu etre initialisee.");
    }
  };

  BibleV2App.prototype.handleSearchKeydown = function (event) {
    if (event.key === "Escape") {
      if (this.state.view === "search") {
        event.preventDefault();
        this.closeSearch();
      }
      return;
    }

    if (!this.state.results.length) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      this.state.activeResultIndex = Math.min(this.state.results.length - 1, this.state.activeResultIndex + 1);
      this.renderSearchResults(this.state.results);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      this.state.activeResultIndex = Math.max(0, this.state.activeResultIndex - 1);
      this.renderSearchResults(this.state.results);
      return;
    }

    if (event.key === "Enter") {
      event.preventDefault();
      var selected = this.state.results[this.state.activeResultIndex] || this.state.results[0];
      if (selected) {
        this.openConcept(selected.concept_id, true);
      }
    }
  };

  BibleV2App.prototype.toggleClearButton = function () {
    if (!this.searchClearButton) {
      return;
    }

    this.searchClearButton.hidden = !normalizeText(this.searchInput.value);
  };

  BibleV2App.prototype.renderSearchState = function () {
    var query = normalizeText(this.state.query);
    if (query.length < 2) {
      this.renderSearchPrompt();
      return;
    }

    if (this.state.isSearching) {
      this.renderSearchLoading();
      return;
    }

    if (!Array.isArray(this.state.results) || this.state.results.length === 0) {
      this.renderSearchNoResults();
      return;
    }
 
    this.renderSearchResults(this.state.results);
  };

  BibleV2App.prototype.renderSearchLoading = function () {
    if (!this.searchPanel) {
      return;
    }

    this.searchPanel.innerHTML = ''
      + '<div class="fb-search-panel-card">'
      +   '<h2 class="fb-panel-title">' + escapeHtml(this.labels.search_open || "Recherche") + '</h2>'
      +   '<p class="fb-panel-copy">' + escapeHtml(this.labels.search_loading || "Preparation de la recherche...") + '</p>'
      + '</div>';
  };

  BibleV2App.prototype.renderSearchPrompt = function () {
    if (!this.searchPanel) {
      return;
    }

    this.searchPanel.innerHTML = ''
      + '<div class="fb-search-panel-card">'
      +   '<h2 class="fb-panel-title">' + escapeHtml(this.labels.search_open || "Recherche") + '</h2>'
      +   '<p class="fb-panel-copy">' + escapeHtml(this.labels.search_prompt || "Saisissez au moins deux caracteres pour rechercher un concept biblique.") + '</p>'
      + '</div>';
  };

  BibleV2App.prototype.renderSearchNoResults = function () {
    if (!this.searchPanel) {
      return;
    }

    this.searchPanel.innerHTML = ''
      + '<div class="fb-search-panel-card">'
      +   '<h2 class="fb-panel-title">' + escapeHtml(this.labels.search_open || "Recherche") + '</h2>'
      +   '<p class="fb-panel-copy">' + escapeHtml(this.labels.search_no_results || "Aucun concept correspondant.") + '</p>'
      + '</div>';
  };

  BibleV2App.prototype.renderSearchError = function () {
    if (!this.searchPanel) {
      return;
    }

    this.searchPanel.innerHTML = ''
      + '<div class="fb-search-panel-card">'
      +   '<h2 class="fb-panel-title">Recherche indisponible</h2>'
      +   '<p class="fb-panel-copy">' + escapeHtml(this.labels.search_error || "La recherche n'a pas pu etre initialisee.") + '</p>'
      + '</div>';
  };

  BibleV2App.prototype.renderSearchResults = function (results) {
    if (!Array.isArray(results) || results.length === 0 || !this.searchPanel) {
      return;
    }

    var html = results.map(function (result, index) {
      var concept = this.store.getConceptById(result.concept_id);
      var displayTitles = getConceptDisplayTitles(concept || result);
      var categoryValue = result.category || (concept ? concept.category : "");
      var sourceBadges = (result.dictionaries || []).map(function (dictionaryId) {
        var source = this.store.sourceMap[dictionaryId];
        return '<span class="fb-source-badge">' + escapeHtml(source ? source.label : dictionaryId) + '</span>';
      }.bind(this)).join("");

      var secondaryLabel = displayTitles.secondary;
      var secondaryMarkup = secondaryLabel
        ? '<span class="fb-result-secondary">' + escapeHtml(secondaryLabel) + '</span>'
        : "";

      var categoryPill = categoryValue
        ? '<span class="fb-pill fb-pill--muted">' + escapeHtml(formatCategoryLabel(categoryValue)) + '</span>'
        : "";

      return ''
        + '<button class="fb-result-button' + (index === this.state.activeResultIndex ? ' is-active' : '') + '" type="button" data-concept-id="' + escapeHtml(result.concept_id) + '">'
        +   '<div class="fb-result-title">' + escapeHtml(displayTitles.primary || result.label || result.concept_id) + secondaryMarkup + '</div>'
        +   '<div class="fb-result-meta">' + categoryPill + sourceBadges + '</div>'
        + '</button>';
    }.bind(this)).join("");

    this.searchPanel.innerHTML = ''
      + '<div class="fb-search-panel-card">'
      +   '<div class="fb-panel-head">'
      +     '<h2 class="fb-panel-title">' + escapeHtml(this.labels.search_open || "Recherche") + '</h2>'
      +     '<p class="fb-panel-copy">' + escapeHtml(this.state.query) + '</p>'
      +   '</div>'
      +   '<div class="fb-result-list">' + html + '</div>'
      + '</div>';
  };

  BibleV2App.prototype.resolveInitialRoute = function () {
    // Priority 1: PHP-injected concept from URL rewrite (/dictionnaire-biblique/{slug}/)
    if (this.config.initialConceptId && !this._initialRouteResolved) {
      this._initialRouteResolved = true;
      this.openConcept(this.config.initialConceptId, false);
      return;
    }

    // Priority 2: Path-based URL (History API) — resolve French slug → concept_id
    var seoBase = this.config.seoBaseUrl || "";
    if (seoBase) {
      var path = window.location.pathname;
      var basePathMatch = seoBase.replace(/^https?:\/\/[^\/]+/, "");
      if (path.indexOf(basePathMatch) === 0) {
        var rawSlug = decodeURIComponent(path.slice(basePathMatch.length).replace(/\/+$/, ""));
        if (rawSlug) {
          var conceptId = this.resolveUrlSlug(rawSlug);
          if (conceptId && conceptId !== this.state.activeConceptId) {
            this.openConcept(conceptId, false);
            return;
          }
        }
      }
    }

    // Priority 3: Legacy hash routing (backward compat) — redirect to clean French URL
    var hash = window.location.hash.replace(/^#/, "");
    var expectedPrefix = (this.config.hashPrefix || "concept") + "/";
    if (hash && hash.indexOf(expectedPrefix) === 0) {
      var hashConceptId = decodeURIComponent(hash.slice(expectedPrefix.length));
      if (hashConceptId && hashConceptId !== this.state.activeConceptId) {
        var urlSlug = this.getUrlSlug(hashConceptId);
        var cleanUrl = (this.config.seoBaseUrl || "/dictionnaire-biblique/") + encodeURIComponent(urlSlug) + "/";
        if (window.history && typeof window.history.replaceState === "function") {
          window.history.replaceState(null, document.title, cleanUrl);
        }
        this.openConcept(hashConceptId, false);
        return;
      }
    }

    if (!this.state.activeConceptId) {
      this.setView(this.hasSearchContext() ? "search" : "idle");
      if (!this.hasSearchContext()) {
        this.renderIdleState();
      }
    }
  };

  BibleV2App.prototype.openConcept = async function (conceptId, updateHash) {
    var canonicalConceptId = this.getCanonicalConceptId(conceptId);
    var concept = this.store.getConceptById(canonicalConceptId);
    if (!concept) {
      this.renderErrorState(this.labels.concept_error || "Le concept demande est introuvable.");
      return;
    }

    if (this.state.view !== "concept" && this.state.view !== "reading") {
      this.state.lastEntryView = this.state.view;
    }
    this.state.activeConceptId = canonicalConceptId;
    this.renderConceptLoading(concept);
    this.setView("concept");

    try {
      var sourceEntries = await this.resolveConceptEntries(concept);
      this.renderConcept(concept, sourceEntries);

      if (this.searchInput) {
        this.searchInput.value = this.state.query || "";
        this.toggleClearButton();
      }

      if (updateHash) {
        var seoBase = this.config.seoBaseUrl || "/dictionnaire-biblique/";
        var urlSlug = this.getUrlSlug(canonicalConceptId);
        var nextUrl = seoBase + encodeURIComponent(urlSlug) + "/";
        if (window.history && typeof window.history.pushState === "function") {
          if (window.location.pathname !== nextUrl) {
            window.history.pushState({ conceptId: canonicalConceptId }, "", nextUrl);
          }
        } else {
          // Fallback pour vieux navigateurs
          var nextHash = (this.config.hashPrefix || "concept") + "/" + encodeURIComponent(canonicalConceptId);
          if (window.location.hash !== "#" + nextHash) {
            window.location.hash = nextHash;
          }
        }
      }
    } catch (error) {
      this.renderErrorState(this.labels.concept_error || "Le concept demande est introuvable.");
    }
  };

  BibleV2App.prototype.clearConceptHash = function () {
    var seoBase = this.config.seoBaseUrl || "/dictionnaire-biblique/";
    var currentPath = window.location.pathname;

    // Check if we're on a concept URL (either hash or pushState)
    var expectedPrefix = "#" + (this.config.hashPrefix || "concept") + "/";
    var isHashConcept = window.location.hash.indexOf(expectedPrefix) === 0;
    var basePathMatch = seoBase.replace(/^https?:\/\/[^\/]+/, "");
    var isPathConcept = currentPath.indexOf(basePathMatch) === 0 && currentPath !== basePathMatch;

    if (!isHashConcept && !isPathConcept) {
      return;
    }

    if (window.history && typeof window.history.replaceState === "function") {
      window.history.replaceState(null, document.title, basePathMatch);
    } else {
      window.location.hash = "";
    }
  };

  BibleV2App.prototype.resolveConceptEntries = async function (concept) {
    var resolvedEntries = [];
    var entryRefs = Array.isArray(concept.entries) ? concept.entries.slice() : [];

    entryRefs.sort(function (left, right) {
      var leftIdx = SOURCE_ORDER.indexOf(left.dictionary);
      var rightIdx = SOURCE_ORDER.indexOf(right.dictionary);
      if (leftIdx === -1) leftIdx = 999;
      if (rightIdx === -1) rightIdx = 999;
      return leftIdx - rightIdx;
    });

    for (var index = 0; index < entryRefs.length; index += 1) {
      var entryRef = entryRefs[index];
      var entry = await this.store.getEntryById(entryRef.dictionary, entryRef.entry_id);
      if (!entry) {
        continue;
      }
      resolvedEntries.push({
        ref: entryRef,
        entry: entry,
        source: this.store.sourceMap[entryRef.dictionary] || null
      });
    }

    return resolvedEntries;
  };

  BibleV2App.prototype.renderConceptLoading = function (concept) {
    var displayTitles = getConceptDisplayTitles(concept);
    this.conceptSlot.innerHTML = ''
      + '<div class="fb-concept-page fb-loading">'
      +   '<div class="fb-concept-hero">'
      +     '<div class="fb-concept-heading">'
      +       '<h2 class="fb-concept-title">' + escapeHtml(displayTitles.primary || concept.label || concept.concept_id) + '</h2>'
      +       (displayTitles.secondary ? '<div class="fb-concept-title-secondary">' + escapeHtml(displayTitles.secondary) + '</div>' : '')
      +     '</div>'
      +     '<div class="fb-concept-restore">' + escapeHtml(this.labels.loading || "Chargement...") + '</div>'
      +   '</div>'
      + '</div>';
  };

  BibleV2App.prototype.renderPaginationControls = function (target, pagination, labels) {
    if (!pagination || pagination.totalPages <= 1) {
      return "";
    }

    return ''
      + '<div class="fb-pagination" data-target="' + escapeHtml(target) + '">'
      +   '<button class="fb-pagination__button" type="button" data-action="' + escapeHtml(labels.action) + '" data-page-delta="-1"' + (pagination.page <= 1 ? ' disabled' : '') + '>' + escapeHtml(this.labels.page_prev || "Precedent") + '</button>'
      +   '<span class="fb-pagination__status">' + escapeHtml((this.labels.page_indicator || "Page {current} sur {total}").replace("{current}", pagination.page).replace("{total}", pagination.totalPages)) + '</span>'
      +   '<button class="fb-pagination__button" type="button" data-action="' + escapeHtml(labels.action) + '" data-page-delta="1"' + (pagination.page >= pagination.totalPages ? ' disabled' : '') + '>' + escapeHtml(this.labels.page_next || "Suivant") + '</button>'
      + '</div>';
  };

  BibleV2App.prototype.renderIdleState = function () {
    if (!this.conceptSlot) {
      return;
    }

    switch (this.state.browseView) {
      case "letter":
        this.renderLetterBrowseView();
        break;
      case "categories":
        this.renderCategoriesBrowseView();
        break;
      case "category":
        this.renderCategoryBrowseView();
        break;
      default:
        this.renderHomeView();
        break;
    }
  };

  BibleV2App.prototype.renderHomeView = function () {
    var browseIndex = this.store.getBrowseIndex();
    var letters = Array.isArray(browseIndex.letters) ? browseIndex.letters : [];
    var categories = Array.isArray(browseIndex.categories) ? browseIndex.categories.slice() : [];
    var heroImageUrl = normalizeText(this.config.heroImageUrl || "");
    var activeLetter = this.state.activeBrowseLetter || (letters[0] ? letters[0].letter : "");
    var activeLetterGroup = this.getBrowseGroupByLetter(activeLetter);
    var previewLetterItems = activeLetterGroup && Array.isArray(activeLetterGroup.preview_items) && activeLetterGroup.preview_items.length > 0
      ? activeLetterGroup.preview_items
      : (activeLetterGroup && Array.isArray(activeLetterGroup.items) ? activeLetterGroup.items.slice(0, this.browseConfig.homeLetterPreviewSize) : []);
    var letterButtons = letters.map(function (item) {
      var isActive = normalizeText(item.letter) === normalizeText(activeLetter);
      return ''
        + '<button class="fb-letter-button' + (isActive ? ' is-active' : '') + '" type="button" data-action="open-browse-letter" data-browse-letter="' + escapeHtml(item.letter) + '">'
        +   '<span class="fb-letter-button__label">' + escapeHtml(item.letter) + '</span>'
        +   '<span class="fb-letter-button__count">' + escapeHtml(item.count) + '</span>'
        + '</button>';
    }).join("");

    categories.sort(function (left, right) {
      if (right.count !== left.count) {
        return right.count - left.count;
      }
      return normalizeText(formatCategoryLabel(left.category)).localeCompare(
        normalizeText(formatCategoryLabel(right.category)),
        "fr",
        { sensitivity: "base" }
      );
    });

    var previewCategories = categories.slice(0, this.browseConfig.homeCategoryPreviewSize).map(function (group) {
      var previewItems = Array.isArray(group.preview_items) && group.preview_items.length > 0
        ? group.preview_items
        : (Array.isArray(group.items) ? group.items.slice(0, 2) : []);
      var previewSummary = previewItems.map(function (item) {
        return normalizeText(item.display_title_primary || item.label || item.concept_id);
      }).filter(Boolean).join(" / ");

      return ''
        + '<article class="fb-category-card fb-category-card--summary">'
        +   '<div class="fb-category-card__head">'
        +     '<h3 class="fb-category-card__title">' + escapeHtml(formatCategoryLabelWithEmoji(group.category || "")) + '</h3>'
        +     '<span class="fb-pill fb-pill--muted">' + escapeHtml(group.count) + '</span>'
        +   '</div>'
        +   (previewSummary ? '<p class="fb-category-card__copy">' + escapeHtml(previewSummary) + '</p>' : '')
        +   '<div class="fb-browse-actions">'
        +     '<button class="fb-browse-link" type="button" data-action="open-browse-category" data-browse-category="' + escapeHtml(group.category) + '">' + escapeHtml(this.labels.open_category || "Ouvrir la catÃ©gorie") + '</button>'
        +   '</div>'
        + '</article>';
    }.bind(this)).join("");

    var heroImageMarkup = heroImageUrl
      ? '<div class="fb-home-media">'
        + '<img src="' + escapeHtml(heroImageUrl) + '" alt="' + escapeHtml(this.labels.home_image_alt || "Ã‰tude matinale sous un figuier") + '" loading="lazy" decoding="async">'
        + '</div>'
      : '';

    this.conceptSlot.innerHTML = ''
      + '<section class="fb-home">'
      +   '<section class="fb-home-hero">'
      +     '<div class="fb-home-hero__grid">'
      +       '<div class="fb-home-hero__intro">'
      +         '<p class="fb-home-kicker">' + escapeHtml(this.labels.home_kicker || "Recherche avancÃ©e et index alphabÃ©tique") + '</p>'
      +         '<div class="fb-home-heading">'
      +           '<h1 class="fb-home-title">' + escapeHtml(this.labels.home_title || "Interface biblique") + '</h1>'
      +           (this.labels.home_title_note ? '<p class="fb-home-title-note">' + escapeHtml(this.labels.home_title_note) + '</p>' : '')
      +         '</div>'
      +       '</div>'
      +       '<div class="fb-home-hero__aside">'
      +         '<div class="fb-home-hero__actions">'
      +           '<button class="fb-home-action" type="button" data-action="open-browse-letter" data-browse-letter="' + escapeHtml(activeLetter) + '">' + escapeHtml(this.labels.home_browse_letter || "Parcourir les concepts") + '</button>'
      +           '<button class="fb-home-action fb-home-action--secondary" type="button" data-action="open-browse-categories">' + escapeHtml(this.labels.home_browse_categories || "Explorer les catÃ©gories") + '</button>'
      +         '</div>'
      +       '</div>'
      +     '</div>'
      +     (this.labels.home_positioning ? '<p class="fb-home-positioning">' + escapeHtml(this.labels.home_positioning) + '</p>' : '')
      +     heroImageMarkup
      +   '</section>'
      +   '<section class="fb-browse-shell fb-browse-shell--preview">'
      +     '<div class="fb-panel-head">'
      +       '<h2 class="fb-panel-title">' + escapeHtml(this.labels.browse_title || "Parcourir par lettre") + '</h2>'
      +       '<p class="fb-panel-copy">' + escapeHtml(this.labels.browse_copy || "") + '</p>'
      +     '</div>'
      +     (letterButtons ? '<div class="fb-letter-nav">' + letterButtons + '</div>' : '')
      +     '<div class="fb-browse-grid fb-browse-grid--preview">' + previewLetterItems.map(function (item) {
              return this.renderBrowseConceptButton(item, true);
            }.bind(this)).join("") + '</div>'
      +     '<div class="fb-browse-actions">'
      +       '<button class="fb-browse-link" type="button" data-action="open-browse-letter" data-browse-letter="' + escapeHtml(activeLetter) + '">' + escapeHtml(this.labels.browse_letter_open || "Ouvrir la vue dediee") + '</button>'
      +     '</div>'
      +   '</section>'
      +   '<section class="fb-browse-shell fb-browse-shell--preview">'
      +     '<div class="fb-panel-head">'
      +       '<h2 class="fb-panel-title">' + escapeHtml(this.labels.categories_title || "Explorer par catÃ©gorie") + '</h2>'
      +       '<p class="fb-panel-copy">' + escapeHtml(this.labels.categories_copy || "") + '</p>'
      +     '</div>'
      +     '<div class="fb-category-grid fb-category-grid--preview">' + previewCategories + '</div>'
      +     '<div class="fb-browse-actions">'
      +       '<button class="fb-browse-link" type="button" data-action="open-browse-categories">' + escapeHtml(this.labels.categories_open_all || "Voir toutes les catÃ©gories") + '</button>'
      +     '</div>'
      +   '</section>'
      + '</section>';
  };

  BibleV2App.prototype.renderLetterBrowseView = function () {
    var browseIndex = this.store.getBrowseIndex();
    var letters = Array.isArray(browseIndex.letters) ? browseIndex.letters : [];
    var activeLetter = this.state.activeBrowseLetter || (letters[0] ? letters[0].letter : "");
    var activeLetterGroup = this.getBrowseGroupByLetter(activeLetter);
    var pagination = paginateItems(
      activeLetterGroup && Array.isArray(activeLetterGroup.items) ? activeLetterGroup.items : [],
      this.state.activeBrowseLetterPage,
      this.browseConfig.letterPageSize
    );
    this.state.activeBrowseLetterPage = pagination.page;

    var letterButtons = letters.map(function (item) {
      var isActive = normalizeText(item.letter) === normalizeText(activeLetter);
      return ''
        + '<button class="fb-letter-button' + (isActive ? ' is-active' : '') + '" type="button" data-action="open-browse-letter" data-browse-letter="' + escapeHtml(item.letter) + '">'
        +   '<span class="fb-letter-button__label">' + escapeHtml(item.letter) + '</span>'
        +   '<span class="fb-letter-button__count">' + escapeHtml(item.count) + '</span>'
        + '</button>';
    }).join("");

    this.conceptSlot.innerHTML = ''
      + '<section class="fb-browse-shell fb-browse-shell--detail">'
      +   '<div class="fb-panel-head fb-panel-head--tight">'
      +     '<p class="fb-home-kicker">' + escapeHtml(this.labels.browse_letter_kicker || "Vue alphabetique") + '</p>'
      +     '<h1 class="fb-panel-title">' + escapeHtml((this.labels.browse_letter_title || "Lettre") + " " + activeLetter) + '</h1>'
      +     '<p class="fb-panel-copy">' + escapeHtml((this.labels.browse_letter_count || "{count} concepts pour cette lettre.").replace("{count}", pagination.totalItems)) + '</p>'
      +   '</div>'
      +   '<div class="fb-browse-actions">'
      +     '<button class="fb-browse-link" type="button" data-action="open-browse-home">' + escapeHtml(this.labels.back || "Retour") + '</button>'
      +   '</div>'
      +   (letterButtons ? '<div class="fb-letter-nav">' + letterButtons + '</div>' : '')
      +   '<div class="fb-browse-grid">' + (pagination.items.length > 0
            ? pagination.items.map(function (item) { return this.renderBrowseConceptButton(item); }.bind(this)).join("")
            : '<p class="fb-panel-copy">' + escapeHtml(this.labels.browse_empty || "Aucun concept disponible pour cette lettre.") + '</p>') + '</div>'
      +   this.renderPaginationControls("letter", pagination, { action: "paginate-letter" })
      + '</section>';
  };

  BibleV2App.prototype.renderCategoriesBrowseView = function () {
    var browseIndex = this.store.getBrowseIndex();
    var categories = Array.isArray(browseIndex.categories) ? browseIndex.categories.slice() : [];

    categories.sort(function (left, right) {
      if (right.count !== left.count) {
        return right.count - left.count;
      }
      return normalizeText(formatCategoryLabel(left.category)).localeCompare(
        normalizeText(formatCategoryLabel(right.category)),
        "fr",
        { sensitivity: "base" }
      );
    });

    var pagination = paginateItems(categories, this.state.activeCategoryDirectoryPage, this.browseConfig.categoryDirectoryPageSize);
    this.state.activeCategoryDirectoryPage = pagination.page;

    this.conceptSlot.innerHTML = ''
      + '<section class="fb-browse-shell fb-browse-shell--detail">'
      +   '<div class="fb-panel-head fb-panel-head--tight">'
      +     '<p class="fb-home-kicker">' + escapeHtml(this.labels.categories_kicker || "Parcours thÃ©matique") + '</p>'
      +     '<h1 class="fb-panel-title">' + escapeHtml(this.labels.categories_title || "Explorer par catÃ©gorie") + '</h1>'
      +     '<p class="fb-panel-copy">' + escapeHtml(this.labels.categories_directory_copy || this.labels.categories_copy || "") + '</p>'
      +   '</div>'
      +   '<div class="fb-browse-actions">'
      +     '<button class="fb-browse-link" type="button" data-action="open-browse-home">' + escapeHtml(this.labels.back || "Retour") + '</button>'
      +   '</div>'
      +   '<div class="fb-category-grid">' + pagination.items.map(function (group) {
            var previewItems = Array.isArray(group.preview_items) && group.preview_items.length > 0 ? group.preview_items : (Array.isArray(group.items) ? group.items.slice(0, 3) : []);
            return ''
              + '<article class="fb-category-card">'
              +   '<div class="fb-category-card__head">'
              +     '<h2 class="fb-category-card__title">' + escapeHtml(formatCategoryLabelWithEmoji(group.category || "")) + '</h2>'
              +     '<span class="fb-pill fb-pill--muted">' + escapeHtml(group.count) + '</span>'
              +   '</div>'
              +   '<div class="fb-category-card__items">'
              +     previewItems.map(function (item) { return this.renderBrowseConceptButton(item, true); }.bind(this)).join("")
              +   '</div>'
              +   '<div class="fb-browse-actions">'
              +     '<button class="fb-browse-link" type="button" data-action="open-browse-category" data-browse-category="' + escapeHtml(group.category) + '">' + escapeHtml(this.labels.open_category || "Ouvrir la catÃ©gorie") + '</button>'
              +   '</div>'
              + '</article>';
          }.bind(this)).join("") + '</div>'
      +   this.renderPaginationControls("categories", pagination, { action: "paginate-categories" })
      + '</section>';
  };

  BibleV2App.prototype.renderCategoryBrowseView = function () {
    var activeCategory = this.state.activeBrowseCategory;
    var categoryGroup = this.getBrowseGroupByCategory(activeCategory);
    var pagination = paginateItems(
      categoryGroup && Array.isArray(categoryGroup.items) ? categoryGroup.items : [],
      this.state.activeBrowseCategoryPage,
      this.browseConfig.categoryConceptPageSize
    );
    this.state.activeBrowseCategoryPage = pagination.page;

    this.conceptSlot.innerHTML = ''
      + '<section class="fb-browse-shell fb-browse-shell--detail">'
      +   '<div class="fb-panel-head fb-panel-head--tight">'
      +     '<p class="fb-home-kicker">' + escapeHtml(this.labels.category_view_kicker || "Vue par catÃ©gorie") + '</p>'
      +     '<h1 class="fb-panel-title">' + escapeHtml(formatCategoryLabelWithEmoji(activeCategory || "")) + '</h1>'
      +     '<p class="fb-panel-copy">' + escapeHtml((this.labels.category_view_count || "{count} concepts dans cette catÃ©gorie.").replace("{count}", pagination.totalItems)) + '</p>'
      +   '</div>'
      +   '<div class="fb-browse-actions">'
      +     '<button class="fb-browse-link" type="button" data-action="open-browse-categories">' + escapeHtml(this.labels.categories_back || "Retour aux catÃ©gories") + '</button>'
      +   '</div>'
      +   '<div class="fb-browse-grid">' + (pagination.items.length > 0
            ? pagination.items.map(function (item) { return this.renderBrowseConceptButton(item); }.bind(this)).join("")
            : '<p class="fb-panel-copy">' + escapeHtml(this.labels.category_empty || "Aucun concept disponible pour cette catÃ©gorie.") + '</p>') + '</div>'
      +   this.renderPaginationControls("category", pagination, { action: "paginate-category" })
      + '</section>';
  };

  BibleV2App.prototype.renderBrowseConceptButton = function (item, compact) {
    var targetConceptId = this.getCanonicalConceptId(item.concept_id);
    var secondaryLabel = normalizeText(item.display_title_secondary || item.secondary_label || "");
    var category = item.category
      ? '<span class="fb-pill fb-pill--muted">' + escapeHtml(formatCategoryLabel(item.category)) + '</span>'
      : "";
    var secondary = secondaryLabel
      ? '<span class="fb-pill">' + escapeHtml(secondaryLabel) + '</span>'
      : "";

    return ''
      + '<button class="fb-browse-button' + (compact ? ' is-compact' : '') + '" type="button" data-concept-id="' + escapeHtml(targetConceptId || item.concept_id) + '">'
      +   '<span class="fb-browse-button__title">' + escapeHtml(item.display_title_primary || item.label || item.concept_id) + '</span>'
      +   '<span class="fb-browse-button__meta">' + category + secondary + '</span>'
      + '</button>';
  };

  BibleV2App.prototype.renderRelatedConceptButton = function (concept) {
    var displayTitles = getConceptDisplayTitles(concept);
    var meta = [];
    if (concept.category) {
      meta.push('<span class="fb-pill fb-pill--muted">' + escapeHtml(formatCategoryLabel(concept.category)) + '</span>');
    }
    if (displayTitles.secondary) {
      meta.push('<span class="fb-pill">' + escapeHtml(displayTitles.secondary) + '</span>');
    }

    return ''
      + '<button class="fb-related-button" type="button" data-concept-id="' + escapeHtml(concept.concept_id) + '">'
      +   '<span class="fb-browse-button__title">' + escapeHtml(displayTitles.primary || concept.label || concept.concept_id) + '</span>'
      +   (meta.length ? '<span class="fb-browse-button__meta">' + meta.join("") + '</span>' : '')
      + '</button>';
  };

  BibleV2App.prototype.renderErrorState = function (message) {
    this.conceptSlot.innerHTML = ''
      + '<div class="fb-error-state">'
      +   '<h2>Chargement incomplet</h2>'
      +   '<p>' + escapeHtml(message) + '</p>'
      + '</div>';
  };

  BibleV2App.prototype.renderConcept = function (concept, sourceEntries) {
    var displayTitles = getConceptDisplayTitles(concept);
    var publicForms = getConceptPublicForms(concept);
    var aliases = uniqueStrings(publicForms.aliasesPublic || []);

    // Group entries by dictionary (source)
    var sourceGroups = {};
    sourceEntries.forEach(function (item) {
      var dictId = item.ref.dictionary;
      if (!sourceGroups[dictId]) {
        sourceGroups[dictId] = [];
      }
      sourceGroups[dictId].push(item);
    });

    var sourceBadges = sourceEntries.map(function (item) {
      var label = item.source ? item.source.label : item.ref.dictionary;
      return '<span class="fb-source-badge">' + escapeHtml(label) + '</span>';
    }).join("");

    var heroMeta = [];
    if (concept.category) {
      heroMeta.push('<span class="fb-pill fb-pill--muted">' + escapeHtml(formatCategoryLabel(concept.category)) + '</span>');
    }
    if (sourceEntries.length > 0) {
      heroMeta.push('<span class="fb-pill fb-pill--muted fb-pill--count">' + sourceEntries.length + ' source' + (sourceEntries.length > 1 ? 's' : '') + '</span>');
    }

    var formGroups = [];
    if (publicForms.other.length > 0) {
      formGroups.push(
        '<div class="fb-form-group">'
          + '<span class="fb-inline-label">' + escapeHtml(this.labels.other_forms || "Autres formes") + '</span>'
          + '<div class="fb-sources-list">'
          + publicForms.other.map(function (value) {
              return '<span class="fb-pill">' + escapeHtml(value) + '</span>';
            }).join("")
          + '</div>'
        + '</div>'
      );
    }
    if (publicForms.english.length > 0) {
      formGroups.push(
        '<div class="fb-form-group">'
          + '<span class="fb-inline-label">' + escapeHtml(this.labels.english_forms || "Formes anglaises") + '</span>'
          + '<div class="fb-sources-list">'
          + publicForms.english.map(function (value) {
              return '<span class="fb-pill fb-pill--muted">' + escapeHtml(value) + '</span>';
            }).join("")
          + '</div>'
        + '</div>'
      );
    }
    if (aliases.length > 0) {
      formGroups.push(
        '<div class="fb-form-group">'
          + '<span class="fb-inline-label">' + escapeHtml(this.labels.aliases || "Autres appellations") + '</span>'
          + '<div class="fb-sources-list">'
          + aliases.map(function (value) {
              return '<span class="fb-pill fb-pill--muted">' + escapeHtml(value) + '</span>';
            }).join("")
          + '</div>'
        + '</div>'
      );
    }

    // Biblical references removed from hero — now in concordance accordion
    var refsHtml = '';

    var relatedConcepts = Array.isArray(concept.related_concepts)
      ? concept.related_concepts.map(function (relation) {
          var relatedConcept = this.store.getConceptById(relation.concept_id);
          if (!relatedConcept) {
            return "";
          }
          return this.renderRelatedConceptButton(relatedConcept);
        }.bind(this)).filter(Boolean).join("")
      : "";

    // Build vertical source sections in SOURCE_ORDER
    var self = this;
    var sourceSectionsHtml = SOURCE_ORDER.map(function (dictId) {
      if (!sourceGroups[dictId]) return "";
      return self.renderSourceSection(dictId, sourceGroups[dictId]);
    }).join("");

    // Render any sources not in SOURCE_ORDER (fallback)
    Object.keys(sourceGroups).forEach(function (dictId) {
      if (SOURCE_ORDER.indexOf(dictId) === -1) {
        sourceSectionsHtml += self.renderSourceSection(dictId, sourceGroups[dictId]);
      }
    });

    var html = ''
      + '<article class="fb-concept-page">'
      +   '<section class="fb-concept-hero">'
      +     '<div class="fb-concept-heading">'
      +       '<h1 class="fb-concept-title">' + escapeHtml(displayTitles.primary || concept.label || concept.concept_id) + '</h1>'
      +       (displayTitles.secondary ? '<div class="fb-concept-title-secondary" aria-label="Nom fran\u00e7ais de rep\u00e8re">' + escapeHtml(displayTitles.secondary) + '</div>' : '')
      +     '</div>'
      +     (heroMeta.length ? '<div class="fb-concept-meta">' + heroMeta.join("") + '</div>' : '')
      +     (formGroups.length ? '<div class="fb-concept-forms">' + formGroups.join("") + '</div>' : '')
      +     refsHtml
      +   '</section>'
      +   '<div class="fb-concept-body">'
      +     '<div class="fb-main-stack">'
      +       sourceSectionsHtml
      +     '</div>'
      +   '</div>'
      +   (relatedConcepts
            ? '<section class="fb-related-standalone">'
            +     '<h2 class="fb-related-standalone__title">Concepts li\u00e9s</h2>'
            +     '<div class="fb-related-standalone__list">' + relatedConcepts + '</div>'
            +   '</section>'
            : '')
      +   '<footer class="fb-copyright-block">'
      +     '<div class="fb-copyright-block__heading">Sources & attributions</div>'
      +     '<div class="fb-copyright-block__text">'
      +       'BYM Lexique \u00b7 '
      +       'Easton\u2019s Bible Dictionary (1897, domaine public) \u00b7 '
      +       'Smith\u2019s Bible Dictionary (1863, domaine public) \u00b7 '
      +       'International Standard Bible Encyclopedia (\u00e9d. James Orr, 1915, domaine public \u2014 num\u00e9ris\u00e9 par CrossWire / SWORD Project) \u00b7 '
      +       'BDB Hebrew Lexicon (Brown-Driver-Briggs, 1906 \u2014 donn\u00e9es Open Scriptures Hebrew Bible Project, licence CC BY 4.0)'
      +     '</div>'
      +   '</footer>'
      + '</article>';

    this.conceptSlot.innerHTML = html;

    // Wire ISBE toggle buttons
    this.conceptSlot.querySelectorAll('[data-action="toggle-isbe"]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var wrapper = btn.closest('.fb-source-section');
        if (!wrapper) return;
        var body = wrapper.querySelector('.fb-source-section__body');
        if (!body) return;
        var isHidden = body.hidden;
        body.hidden = !isHidden;
        btn.textContent = isHidden
          ? (self.labels.isbe_collapse || "Masquer l\u0027article encyclop\u00e9dique")
          : (self.labels.isbe_expand || "Lire l\u0027article encyclop\u00e9dique");
        btn.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
      });
    });

    // Wire biblical reference pills (delegate to v3-patch verse bubble if available)
    this.conceptSlot.querySelectorAll('[data-bible-ref]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var ref = btn.getAttribute('data-bible-ref');
        if (ref && typeof window.showVerseBubble === 'function') {
          var rect = btn.getBoundingClientRect();
          window.showVerseBubble(ref, { x: rect.left, y: rect.bottom + window.scrollY });
        }
      });
    });
  };

  BibleV2App.prototype.renderSourceSection = function (dictId, items) {
    var sectionLabel = SOURCE_LABELS[dictId] || (items[0] && items[0].source ? items[0].source.label : dictId);
    var colorClass = SOURCE_COLORS[dictId] || 'default';
    var isISBE = dictId === 'isbe';
    var roleLabel = SOURCE_ROLE_LABELS[dictId] || '';
    var roleColors = SOURCE_ROLE_COLORS[dictId] || null;

    // Estimate reading time from all entries combined
    var totalText = items.map(function (item) {
      return (item.entry && item.entry.definition) ? item.entry.definition : '';
    }).join(' ');
    var readTime = estimateReadingTime(totalText);

    var roleBadgeHtml = roleColors
      ? '<span class="fb-role-badge" style="background:' + roleColors.bg + ';color:' + roleColors.text + ';border-color:' + roleColors.border + '30">' + escapeHtml(roleLabel) + '</span>'
      : '';

    var readTimeHtml = (readTime && totalText.split(/\s+/).length > 100)
      ? '<span class="fb-read-time">' + escapeHtml(readTime) + '</span>'
      : '';

    var headerMeta = (roleBadgeHtml || readTimeHtml)
      ? '<div class="fb-source-section__meta">' + roleBadgeHtml + readTimeHtml + '</div>'
      : '';

    var entriesHtml = items.map(function (item) {
      return this.renderSourceSectionEntry(item);
    }.bind(this)).join("");

    if (isISBE) {
      return ''
        + '<section class="fb-source-section fb-source-section--' + escapeHtml(colorClass) + '" data-source="' + escapeHtml(dictId) + '">'
        +   '<header class="fb-source-section__header">'
        +     '<div class="fb-source-section__title-row">'
        +       '<h2 class="fb-source-section__title">' + escapeHtml(sectionLabel) + '</h2>'
        +       headerMeta
        +     '</div>'
        +     '<button class="fb-source-section__toggle" type="button" data-action="toggle-isbe" aria-expanded="false">'
        +       escapeHtml(this.labels.isbe_expand || "Lire l\u0027article encyclop\u00e9dique")
        +     '</button>'
        +   '</header>'
        +   '<div class="fb-source-section__body" hidden>'
        +     entriesHtml
        +   '</div>'
        + '</section>';
    }

    return ''
      + '<section class="fb-source-section fb-source-section--' + escapeHtml(colorClass) + '" data-source="' + escapeHtml(dictId) + '">'
      +   '<header class="fb-source-section__header">'
      +     '<div class="fb-source-section__title-row">'
      +       '<h2 class="fb-source-section__title">' + escapeHtml(sectionLabel) + '</h2>'
      +       headerMeta
      +     '</div>'
      +   '</header>'
      +   '<div class="fb-source-section__body">'
      +     entriesHtml
      +   '</div>'
      + '</section>';
  };

  BibleV2App.prototype.renderSourceSectionEntry = function (item) {
    var entry = item.entry;
    var isDirect = entry.render_mode_default === "direct" || item.ref.dictionary === "bym_lexicon";
    var previewLength = item.ref.dictionary === "isbe" ? 280 : 220;
    var sourceTitles = this.getEntryDisplayTitles(item.ref.dictionary, entry);

    if (entry.display_strategy === "resolved_redirect" && entry.redirect_target_concept_id) {
      return ''
        + '<div class="fb-source-entry fb-source-entry--redirect">'
        +   '<p>' + escapeHtml(this.labels.redirect_intro || "Dans le lexique BYM, cette forme renvoie \u00e0 ce concept.") + '</p>'
        +   '<div class="fb-source-actions">'
        +     '<button class="fb-source-action" type="button" data-concept-id="' + escapeHtml(entry.redirect_target_concept_id) + '">' + escapeHtml(this.labels.redirect_open || "Ouvrir le concept cible") + '</button>'
        +   '</div>'
        + '</div>';
    }

    return ''
      + '<div class="fb-source-entry">'
      +   (isDirect
          ? '<div class="fb-source-content">' + renderRichText(entry.definition) + '</div>'
          : '<div class="fb-source-preview">' + escapeHtml(excerptText(entry.definition, previewLength)) + '</div>'
            + '<div class="fb-source-actions"><button class="fb-source-action" type="button" data-action="open-reading" data-entry-id="' + escapeHtml(entry.id) + '" data-dictionary="' + escapeHtml(item.ref.dictionary) + '" data-role="' + escapeHtml(item.ref.display_role) + '">' + escapeHtml(this.labels.reading_open || "Lire la suite") + '</button></div>')
      + '</div>';
  };

  BibleV2App.prototype.getEntryDisplayTitles = function (dictionaryId, entry) {
    var sourcePrimaryTitle = "";
    var sourceSecondaryTitle = "";

    if (dictionaryId === "bym_lexicon" && entry && entry.concept_hint) {
      var hintedConcept = this.store.getConceptById(entry.concept_hint);
      if (hintedConcept) {
        var conceptTitles = getConceptDisplayTitles(hintedConcept);
        sourcePrimaryTitle = conceptTitles.primary || hintedConcept.label || "";
        sourceSecondaryTitle = conceptTitles.secondary || "";
        return {
          primary: sourcePrimaryTitle,
          secondary: sourceSecondaryTitle
        };
      }
    }

    if (dictionaryId === "bym_lexicon" && entry.mot_restore && normalizeSearchValue(entry.mot_restore) !== normalizeSearchValue(entry.label_fr || entry.mot)) {
      sourcePrimaryTitle = entry.mot_restore;
      sourceSecondaryTitle = entry.label_fr || entry.mot;
    } else {
      sourcePrimaryTitle = entry.label_fr || entry.mot_restore || entry.mot;
      if (entry.mot && normalizeSearchValue(entry.mot) !== normalizeSearchValue(sourcePrimaryTitle)) {
        sourceSecondaryTitle = entry.mot;
      }
    }

    return {
      primary: sourcePrimaryTitle,
      secondary: sourceSecondaryTitle
    };
  };

  BibleV2App.prototype.renderSourceCard = function (item) {
    var entry = item.entry;
    var roleLabel = this.labels[item.ref.display_role] || item.ref.display_role;
    var sourceLabel = item.source ? item.source.label : item.ref.dictionary;
    var previewLength = entry.render_mode_default === "deep_read" ? 280 : 220;
    var isDirect = entry.render_mode_default === "direct";
    var sourceTitles = this.getEntryDisplayTitles(item.ref.dictionary, entry);
    var sourcePrimaryTitle = sourceTitles.primary;
    var sourceSecondaryTitle = sourceTitles.secondary;

    var heading = ''
      + '<span class="fb-source-title__primary">' + escapeHtml(sourcePrimaryTitle) + '</span>'
      + (sourceSecondaryTitle ? '<span class="fb-source-title__secondary">' + escapeHtml(sourceSecondaryTitle) + '</span>' : '');

    var metaParts = [];
    metaParts.push('<span class="fb-source-badge">' + escapeHtml(roleLabel) + '</span>');
    metaParts.push('<span class="fb-source-badge">' + escapeHtml(sourceLabel) + '</span>');
    if (entry.mot_restore && item.ref.dictionary !== "bym_lexicon") {
      metaParts.push('<span class="fb-source-badge">' + escapeHtml(this.labels.other_form || "Forme d'origine") + ': ' + escapeHtml(entry.mot_restore) + '</span>');
    }

    if (entry.display_strategy === "resolved_redirect" && entry.redirect_target_concept_id) {
      return ''
        + '<section class="fb-source-card fb-source-card--redirect" data-role="' + escapeHtml(item.ref.display_role) + '" data-mode="' + escapeHtml(entry.render_mode_default) + '">'
        +   '<header class="fb-source-header">'
        +     '<h2 class="fb-source-title">' + heading + '</h2>'
        +     '<div class="fb-source-meta">' + metaParts.join("") + '</div>'
        +   '</header>'
        +   '<div class="fb-source-body fb-source-redirect">'
        +     '<p>' + escapeHtml(this.labels.redirect_intro || "Dans le lexique BYM, cette forme renvoie a ce concept.") + '</p>'
        +     '<div class="fb-source-actions">'
        +       '<button class="fb-source-action" type="button" data-concept-id="' + escapeHtml(entry.redirect_target_concept_id) + '">' + escapeHtml(this.labels.redirect_open || "Ouvrir le concept cible") + '</button>'
        +     '</div>'
        +   '</div>'
        + '</section>';
    }

    return ''
      + '<section class="fb-source-card" data-role="' + escapeHtml(item.ref.display_role) + '" data-mode="' + escapeHtml(entry.render_mode_default) + '">'
      +   '<header class="fb-source-header">'
      +     '<h2 class="fb-source-title">' + heading + '</h2>'
      +     '<div class="fb-source-meta">' + metaParts.join("") + '</div>'
      +   '</header>'
      +   '<div class="fb-source-body">'
      +     (isDirect
            ? '<div class="fb-source-content">' + renderRichText(entry.definition) + '</div>'
            : '<div class="fb-source-preview">' + escapeHtml(excerptText(entry.definition, previewLength)) + '</div>')
      +   '</div>'
      +   (!isDirect
            ? '<div class="fb-source-actions"><button class="fb-source-action" type="button" data-action="open-reading" data-entry-id="' + escapeHtml(entry.id) + '" data-dictionary="' + escapeHtml(item.ref.dictionary) + '" data-role="' + escapeHtml(item.ref.display_role) + '">' + escapeHtml(this.labels.reading_open || "Lire la suite") + '</button></div>'
            : '')
      + '</section>';
  };

  BibleV2App.prototype.openReading = async function (dictionaryId, entryId, displayRole) {
    if (!dictionaryId || !entryId) {
      return;
    }

    this.setView("reading");
    this.readingPanel.innerHTML = ''
      + '<div class="fb-reading-shell fb-loading">'
      +   '<div class="fb-reading-head">'
      +     '<h2 class="fb-reading-title">' + escapeHtml(this.labels.reading_loading || "Chargement de la lecture...") + '</h2>'
      +   '</div>'
      + '</div>';

    try {
      var entry = await this.store.getEntryById(dictionaryId, entryId);
      if (!entry) {
        throw new Error("reading_entry_missing");
      }

      var source = this.store.sourceMap[dictionaryId] || null;
      this.state.activeReading = {
        dictionary: dictionaryId,
        entryId: entryId
      };

      this.renderReadingPanel(entry, source, displayRole, dictionaryId);
    } catch (error) {
      this.readingPanel.innerHTML = ''
        + '<div class="fb-reading-shell">'
        +   '<div class="fb-reading-head">'
        +     '<h2 class="fb-reading-title">Lecture indisponible</h2>'
        +     '<button class="fb-reading-close" type="button" data-action="close-reading">' + escapeHtml(this.labels.reading_close || "Fermer la lecture") + '</button>'
        +   '</div>'
        +   '<div class="fb-reading-body"><p>' + escapeHtml(this.labels.concept_error || "Le concept demande est introuvable.") + '</p></div>'
        + '</div>';
    }
  };

  BibleV2App.prototype.renderReadingPanel = function (entry, source, displayRole, dictionaryId) {
    var roleLabel = this.labels[displayRole] || displayRole || "";
    var sourceLabel = source ? source.label : "";
    var metaParts = [];
    var sourceTitles = this.getEntryDisplayTitles(dictionaryId, entry);

    if (roleLabel) {
      metaParts.push('<span class="fb-source-badge">' + escapeHtml(roleLabel) + '</span>');
    }
    if (sourceLabel) {
      metaParts.push('<span class="fb-source-badge">' + escapeHtml(sourceLabel) + '</span>');
    }
    if (entry.mot_restore && dictionaryId !== "bym_lexicon") {
      metaParts.push('<span class="fb-source-badge">' + escapeHtml(this.labels.other_form || "Forme d'origine") + ': ' + escapeHtml(entry.mot_restore) + '</span>');
    }

    this.readingPanel.innerHTML = ''
      + '<div class="fb-reading-shell">'
      +   '<div class="fb-reading-head">'
      +     '<div class="fb-reading-head-copy">'
      +       '<h2 class="fb-reading-title">' + escapeHtml(sourceTitles.primary || entry.label_fr || entry.mot) + '</h2>'
      +       (sourceTitles.secondary ? '<div class="fb-concept-title-secondary">' + escapeHtml(sourceTitles.secondary) + '</div>' : '')
      +       (metaParts.length ? '<div class="fb-source-meta">' + metaParts.join("") + '</div>' : '')
      +     '</div>'
      +     '<button class="fb-reading-close" type="button" data-action="close-reading">' + escapeHtml(this.labels.reading_close || "Fermer la lecture") + '</button>'
      +   '</div>'
      +   '<div class="fb-reading-body">'
      +     '<div class="fb-source-content">' + renderRichText(entry.definition) + '</div>'
      +   '</div>'
      + '</div>';
  };

  BibleV2App.prototype.closeReading = function () {
    this.state.activeReading = null;
    this.setView("concept");
  };

  BibleV2App.prototype.setSearchStatus = function (message) {
    if (this.searchStatus) {
      this.searchStatus.textContent = message || "";
    }
  };

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(APP_SELECTOR).forEach(function (root) {
      var app = new BibleV2App(root, config);
      app.init();
    });
  });
})();
