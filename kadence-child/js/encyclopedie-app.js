/**
 * encyclopedie-app.js — Portail Encyclopédie Biblique (Lazy Rendering Version)
 * Charge browse-index.json + concepts.json
 * Affiche stats, search, lettre-index, catégories au chargement
 * Affiche concepts à la demande (par lettre ou catégorie) avec pagination
 * Dépend de figuierEncycConfig injecté par PHP.
 */
(function () {
  'use strict';

  var CFG = window.figuierEncycConfig || {};
  var manifestUrl = CFG.manifestUrl || '';
  var dictBaseUrl = CFG.dictBaseUrl || '/dictionnaire-biblique/';
  var slugsUrl = CFG.slugsUrl || '';

  // Derive base URL for data files from manifestUrl
  var dataBaseUrl = manifestUrl.replace(/source-manifest\.json.*$/, '');

  var allConcepts = [];
  var slugMap = {};
  var browseLetters = [];
  var browseCategories = [];
  var manifestStats = {};

  var root = document.getElementById('encyclopedie-app');
  if (!root) return;

  // State for current view
  var currentView = 'main'; // 'main', 'letter', 'category'
  var currentLetter = '';
  var currentCategory = '';
  var currentPage = 1;
  var itemsPerPage = 50;

  // ── Init ──
  function init() {
    root.innerHTML = '<div class="encyc-loading">Chargement de l\'encyclopédie…</div>';
    var promises = [
      fetch(manifestUrl).then(function (r) { return r.json(); }),
      fetch(dataBaseUrl + 'browse-index.json').then(function (r) { return r.json(); }),
      fetch(dataBaseUrl + 'concepts.json').then(function (r) { return r.json(); })
    ];
    if (slugsUrl) {
      promises.push(fetch(slugsUrl).then(function (r) { return r.json(); }));
    }
    Promise.all(promises).then(function (results) {
      var manifest = results[0];
      var browseIndex = results[1];
      var concepts = results[2];
      if (results[3]) slugMap = results[3];

      manifestStats = manifest.stats || {};
      browseLetters = browseIndex.letters || [];
      browseCategories = browseIndex.categories || [];

      // Build allConcepts from concepts.json
      allConcepts = concepts.map(function (c) {
        var label = c.label || '';
        var primary = (c.display_titles && c.display_titles.primary) || c.label_restore || label;
        var secondary = (c.display_titles && c.display_titles.secondary) || '';
        var cat = c.category || '';
        return {
          concept_id: c.concept_id || '',
          label: label,
          primary: primary,
          secondary: secondary,
          category: cat,
          slug: getSlug(c.concept_id, label),
          letter: (primary || label).charAt(0).toUpperCase()
        };
      });
      allConcepts.sort(function (a, b) { return a.primary.localeCompare(b.primary, 'fr'); });

      render();
    }).catch(function (err) {
      root.innerHTML = '<p class="encyc-error">Impossible de charger les données. Réessayez plus tard.</p>';
      console.error('[Encyclopédie]', err);
    });
  }

  function getSlug(conceptId, label) {
    if (slugMap[label]) return slugMap[label];
    if (slugMap[conceptId]) return slugMap[conceptId];
    var key = (label || '').toLowerCase().trim();
    if (slugMap[key]) return slugMap[key];
    return conceptId || encodeURIComponent(key.replace(/\s+/g, '-').replace(/['']/g, '-'));
  }

  // ── Pretty category names ──
  var catLabels = {
    'alimentation_et_agriculture': 'Alimentation & Agriculture',
    'animal': 'Animaux',
    'corps_et_sante': 'Corps & Santé',
    'doctrine': 'Doctrine & Théologie',
    'etre_spirituel': 'Êtres spirituels',
    'evenement': 'Événements',
    'institution': 'Institutions',
    'lieu': 'Lieux & Géographie',
    'livre_biblique': 'Livres bibliques',
    'matiere': 'Matières & Matériaux',
    'mesures_et_temps': 'Mesures & Temps',
    'non_classifie': 'Non classifié',
    'objet_sacre': 'Objets sacrés',
    'objets_et_vetements': 'Objets & Vêtements',
    'personnage': 'Personnages',
    'peuple': 'Peuples & Nations',
    'plante': 'Plantes',
    'rite': 'Rites & Pratiques'
  };

  var catIcons = {
    'alimentation_et_agriculture': '🌾',
    'animal': '🐑',
    'corps_et_sante': '🩺',
    'doctrine': '✝️',
    'etre_spirituel': '👼',
    'evenement': '📅',
    'institution': '🏛️',
    'lieu': '📍',
    'livre_biblique': '📖',
    'matiere': '💎',
    'mesures_et_temps': '⏳',
    'non_classifie': '📋',
    'objet_sacre': '🕯️',
    'objets_et_vetements': '🧥',
    'personnage': '👤',
    'peuple': '👥',
    'plante': '🌿',
    'rite': '🙏'
  };

  function prettyCat(raw) {
    return catLabels[raw] || raw.replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  // ── Main render (initial view) ──
  function render() {
    root.innerHTML = '';

    var totalConcepts = manifestStats.concepts_count || allConcepts.length;
    var totalCats = browseCategories.length;
    var totalLetters = browseLetters.length;

    // Stats bar
    var statsHtml = '<div class="encyc-stats">'
      + '<span class="encyc-stat"><strong>' + totalConcepts + '</strong> concepts</span>'
      + '<span class="encyc-stat"><strong>' + totalCats + '</strong> catégories</span>'
      + '<span class="encyc-stat"><strong>' + totalLetters + '</strong> lettres</span>'
      + '</div>';

    // Search
    var searchHtml = '<div class="encyc-search-wrap">'
      + '<input type="text" id="encyc-search" class="encyc-search" placeholder="Rechercher un concept biblique…" autocomplete="off" />'
      + '<div id="encyc-search-results" class="encyc-search-results" style="display:none"></div>'
      + '</div>';

    // Letter index bar
    var letterHtml = '<section class="encyc-section">'
      + '<h2 class="encyc-section-title">Index alphabétique</h2>'
      + '<div class="encyc-letter-bar">';
    browseLetters.forEach(function (l) {
      letterHtml += '<a href="#letter-' + l.letter + '" class="encyc-letter-btn" data-letter="' + l.letter + '">'
        + l.letter + ' <small>(' + l.count + ')</small></a>';
    });
    letterHtml += '</div></section>';

    // Categories grid
    var catHtml = '<section class="encyc-section">'
      + '<h2 class="encyc-section-title">Explorer par catégorie</h2>'
      + '<div class="encyc-cat-grid">';
    browseCategories.forEach(function (cat) {
      var icon = catIcons[cat.category] || '📖';
      var label = prettyCat(cat.category);
      catHtml += '<a href="#cat-' + cat.category + '" class="encyc-cat-card" data-cat="' + cat.category + '">'
        + '<span class="encyc-cat-icon">' + icon + '</span>'
        + '<span class="encyc-cat-name">' + label + '</span>'
        + '<span class="encyc-cat-count">' + cat.count + ' concepts</span>'
        + '</a>';
    });
    catHtml += '</div></section>';

    // Results container (initially hidden, populated on demand)
    var resultsHtml = '<div id="encyc-results" style="display:none"></div>';

    root.innerHTML = statsHtml + searchHtml + letterHtml + catHtml + resultsHtml;

    // Wire search
    var searchInput = document.getElementById('encyc-search');
    var searchResults = document.getElementById('encyc-search-results');
    var debounceTimer;
    searchInput.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      var val = this.value.trim();
      debounceTimer = setTimeout(function () { doSearch(val, searchResults); }, 200);
    });

    // Close search on outside click
    document.addEventListener('click', function (e) {
      if (!e.target.closest('.encyc-search-wrap')) searchResults.style.display = 'none';
    });

    // Wire category cards
    root.querySelectorAll('.encyc-cat-card').forEach(function (card) {
      card.addEventListener('click', function (e) {
        e.preventDefault();
        var cat = this.getAttribute('data-cat');
        showCategory(cat);
      });
    });

    // Wire letter buttons
    root.querySelectorAll('.encyc-letter-btn').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        var letter = this.getAttribute('data-letter');
        showLetter(letter);
      });
    });
  }

  // ── Render results for a letter ──
  function showLetter(letter) {
    currentView = 'letter';
    currentLetter = letter;
    currentPage = 1;

    // Update active state on letter buttons
    root.querySelectorAll('.encyc-letter-btn').forEach(function (btn) {
      btn.classList.remove('active');
      if (btn.getAttribute('data-letter') === letter) {
        btn.classList.add('active');
      }
    });

    renderResults();
  }

  // ── Render results for a category ──
  function showCategory(category) {
    currentView = 'category';
    currentCategory = category;
    currentPage = 1;

    renderResults();
  }

  // ── Go back to main view ──
  function goBack() {
    currentView = 'main';
    currentLetter = '';
    currentCategory = '';
    currentPage = 1;

    root.querySelectorAll('.encyc-letter-btn').forEach(function (btn) {
      btn.classList.remove('active');
    });

    var resultsDiv = document.getElementById('encyc-results');
    if (resultsDiv) resultsDiv.style.display = 'none';
  }

  // ── Get filtered concepts ──
  function getFilteredConcepts() {
    if (currentView === 'letter') {
      return allConcepts.filter(function (c) { return c.letter === currentLetter; });
    } else if (currentView === 'category') {
      return allConcepts.filter(function (c) { return c.category === currentCategory; });
    }
    return [];
  }

  // ── Render paginated results ──
  function renderResults() {
    var filtered = getFilteredConcepts();
    var totalPages = Math.ceil(filtered.length / itemsPerPage);

    // Clamp page number
    if (currentPage < 1) currentPage = 1;
    if (currentPage > totalPages) currentPage = totalPages;

    var startIdx = (currentPage - 1) * itemsPerPage;
    var endIdx = startIdx + itemsPerPage;
    var pageItems = filtered.slice(startIdx, endIdx);

    var resultsDiv = document.getElementById('encyc-results');
    var html = '';

    // Add back link for category view
    if (currentView === 'category') {
      html += '<div style="margin-bottom: var(--s-4);">'
        + '<a href="#" class="encyc-back-link" id="back-to-main">← Retour</a>'
        + '</div>';
    }

    // Heading
    if (currentView === 'letter') {
      html += '<section class="encyc-letter-section">'
        + '<h3 class="encyc-letter-heading">' + currentLetter + ' <small>(' + filtered.length + ')</small></h3>';
    } else if (currentView === 'category') {
      html += '<section class="encyc-cat-section">'
        + '<h3 class="encyc-cat-heading">' + prettyCat(currentCategory) + ' <small>(' + filtered.length + ')</small></h3>';
    }

    // Concept grid
    html += '<div class="encyc-concept-grid">';
    pageItems.forEach(function (c) {
      var displayLabel = c.primary;
      var sub = c.secondary && c.secondary !== c.primary ? ' <small class="encyc-concept-alt">(' + escHtml(c.secondary) + ')</small>' : '';
      html += '<a href="' + dictBaseUrl + c.slug + '/" class="encyc-concept-link">'
        + '<span class="encyc-concept-label">' + escHtml(displayLabel) + sub + '</span>'
        + (c.category && currentView !== 'category' ? '<span class="encyc-concept-cat">' + prettyCat(c.category) + '</span>' : '')
        + '</a>';
    });
    html += '</div>';

    // Pagination controls
    if (totalPages > 1) {
      html += '<div class="encyc-pagination">';

      // Previous button
      if (currentPage > 1) {
        html += '<button class="encyc-page-btn" id="page-prev">← Précédent</button>';
      } else {
        html += '<button class="encyc-page-btn" disabled>← Précédent</button>';
      }

      // Page info
      html += '<span class="encyc-page-info">Page ' + currentPage + '/' + totalPages + '</span>';

      // Next button
      if (currentPage < totalPages) {
        html += '<button class="encyc-page-btn" id="page-next">Suivant →</button>';
      } else {
        html += '<button class="encyc-page-btn" disabled>Suivant →</button>';
      }

      html += '</div>';
    }

    html += '</section>';

    resultsDiv.innerHTML = html;
    resultsDiv.style.display = 'block';

    // Scroll results into view
    resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Wire pagination buttons
    var prevBtn = document.getElementById('page-prev');
    if (prevBtn) {
      prevBtn.addEventListener('click', function () {
        if (currentPage > 1) {
          currentPage--;
          renderResults();
        }
      });
    }

    var nextBtn = document.getElementById('page-next');
    if (nextBtn) {
      nextBtn.addEventListener('click', function () {
        if (currentPage < totalPages) {
          currentPage++;
          renderResults();
        }
      });
    }

    // Wire back button
    var backBtn = document.getElementById('back-to-main');
    if (backBtn) {
      backBtn.addEventListener('click', function (e) {
        e.preventDefault();
        goBack();
      });
    }
  }

  // ── Search ──
  function doSearch(query, container) {
    if (query.length < 2) { container.style.display = 'none'; return; }
    var q = query.toLowerCase();
    var matches = allConcepts.filter(function (c) {
      return c.label.toLowerCase().indexOf(q) !== -1
        || c.primary.toLowerCase().indexOf(q) !== -1
        || (c.secondary && c.secondary.toLowerCase().indexOf(q) !== -1);
    }).slice(0, 25);
    if (matches.length === 0) {
      container.innerHTML = '<div class="encyc-no-result">Aucun résultat pour « ' + escHtml(query) + ' »</div>';
    } else {
      container.innerHTML = matches.map(function (c) {
        var sub = c.secondary && c.secondary !== c.primary ? ' <small>(' + escHtml(c.secondary) + ')</small>' : '';
        return '<a href="' + dictBaseUrl + c.slug + '/" class="encyc-search-item">'
          + '<span>' + highlight(c.primary, q) + sub + '</span>'
          + (c.category ? '<small>' + prettyCat(c.category) + '</small>' : '')
          + '</a>';
      }).join('');
    }
    container.style.display = 'block';
  }

  // ── Utilities ──
  function escHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function highlight(text, query) {
    var idx = text.toLowerCase().indexOf(query);
    if (idx === -1) return escHtml(text);
    return escHtml(text.substring(0, idx))
      + '<mark>' + escHtml(text.substring(idx, idx + query.length)) + '</mark>'
      + escHtml(text.substring(idx + query.length));
  }

  // ── Boot ──
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
