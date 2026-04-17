/**
 * lexique-strong-app.js — Lexique hebreu biblique
 * 8674 entrees lexicales + Arbre des racines hebraiques (1822 racines).
 * Sources : Brown-Driver-Briggs (BDB), Open Scriptures Hebrew Bible (OSHB), numerotation Strong.
 * Depend de figuierLexiqueConfig injecte par PHP.
 */
(function () {
  'use strict';

  var CFG = window.figuierLexiqueConfig || {};
  var lexiconUrl = CFG.lexiconUrl || '';
  var dictBaseUrl = CFG.dictBaseUrl || '/dictionnaire-biblique/';
  var slugsUrl = CFG.slugsUrl || '';
  var manifestUrl = CFG.manifestUrl || '';
  var concordanceUrl = CFG.concordanceUrl || '';

  var allEntries = [];
  var filteredEntries = [];
  var slugMap = {};
  var conceptIndex = {};
  var rootFamilies = {};
  var occurrences = {};
  var rootIndex = {};
  var PAGE_SIZE = 50;
  var currentPage = 0;
  var currentQuery = '';
  var currentView = 'browse';
  var selectedRoot = '';
  var expandedNode = '';
  var arbreQuery = '';

  var root = document.getElementById('lexique-strong-app');
  if (!root) return;

  var dataBaseUrl = manifestUrl ? manifestUrl.replace(/source-manifest\.json.*$/, '') : '';

  // ── POS metadata ──
  var POS_META = {
    'v':         { color: '#6b8f5e', label: 'Verbes',           bg: '#f2f6f0' },
    'n-m':       { color: '#b28c64', label: 'Noms masculins',   bg: '#faf5f0' },
    'n-f':       { color: '#a0725a', label: 'Noms f\u00e9minins', bg: '#f8f0ec' },
    'a':         { color: '#7a6f9b', label: 'Adjectifs',        bg: '#f3f1f7' },
    'n-pr-m':    { color: '#8a7a6a', label: 'Noms propres (m)', bg: '#f5f3f0' },
    'n-pr-f':    { color: '#8a7a6a', label: 'Noms propres (f)', bg: '#f5f3f0' },
    'n-pr-loc':  { color: '#8a7a6a', label: 'Lieux',            bg: '#f5f3f0' }
  };

  function posInfo(p) {
    if (POS_META[p]) return POS_META[p];
    if (p && p.indexOf('n-pr') === 0) return POS_META['n-pr-m'];
    if (p && p.indexOf('n-') === 0) return POS_META['n-m'];
    return { color: '#999', label: p || 'Autre', bg: '#f5f5f5' };
  }

  function posGroup(p) {
    if (p === 'v') return 'v';
    if (p === 'a') return 'a';
    if (p && p.indexOf('n-pr') === 0) return 'n-pr';
    if (p && (p.indexOf('n-f') === 0 || p === 'n-f')) return 'n-f';
    if (p && (p.indexOf('n-m') === 0 || p === 'n-m' || p === 'n')) return 'n-m';
    return 'other';
  }

  var POS_ORDER = ['v', 'n-m', 'n-f', 'a', 'n-pr'];

  // ── Featured roots (largest families) ──
  // Root keys must match strong-root-families.json exactly (no niqqud, no final letters)
  var FEATURED = [
    { root: '\u05D0\u05D3\u05DE', hint: 'homme \u00b7 terre \u00b7 rouge' },
    { root: '\u05DE\u05DC\u05DB', hint: 'roi \u00b7 r\u00e8gne' },
    { root: '\u05E9\u05DC\u05DE', hint: 'paix \u00b7 entier' },
    { root: '\u05D3\u05D1\u05E8', hint: 'parole \u00b7 chose' },
    { root: '\u05E2\u05DC\u05D4', hint: 'monter \u00b7 offrande' },
    { root: '\u05E8\u05D0\u05D4', hint: 'voir \u00b7 vision' },
    { root: '\u05E8\u05D5\u05DE', hint: '\u00e9lever \u00b7 haut' },
    { root: '\u05D0\u05DE\u05E0', hint: 'v\u00e9rit\u00e9 \u00b7 fid\u00e8le' },
    { root: '\u05D2\u05DC\u05DC', hint: 'rouler \u00b7 r\u00e9v\u00e9ler' },
    { root: '\u05DE\u05E8\u05E8', hint: 'amer \u00b7 amertume' },
    { root: '\u05E2\u05D1\u05D3', hint: 'servir \u00b7 serviteur' },
    { root: '\u05D7\u05D9\u05DC', hint: 'force \u00b7 arm\u00e9e' }
  ];

  // ── Init ──
  function init() {
    root.innerHTML = '<div class="lex-loading">Chargement du lexique h\u00e9breu\u2026</div>';
    var promises = [
      fetch(lexiconUrl).then(function (r) { return r.json(); })
    ];
    if (slugsUrl) promises.push(fetch(slugsUrl).then(function (r) { return r.json(); }));
    if (dataBaseUrl) promises.push(fetch(dataBaseUrl + 'concepts.json').then(function (r) { return r.json(); }));
    if (dataBaseUrl) promises.push(
      fetch(dataBaseUrl + 'strong-root-families.json')
        .then(function (r) { return r.ok ? r.json() : {}; })
        .catch(function () { return {}; })
    );
    if (concordanceUrl) promises.push(
      fetch(concordanceUrl)
        .then(function (r) { return r.ok ? r.json() : {}; })
        .catch(function () { return {}; })
    );

    Promise.all(promises).then(function (results) {
      var idx = 0;
      var data = results[idx++];
      allEntries = Array.isArray(data) ? data : (data.value || []);
      if (slugsUrl) slugMap = results[idx++] || {};
      var conceptsData = dataBaseUrl ? results[idx++] : null;
      if (conceptsData) buildConceptIndex(conceptsData);
      if (dataBaseUrl) rootFamilies = results[idx++] || {};
      if (concordanceUrl) {
        var concRaw = results[idx++] || {};
        Object.keys(concRaw).forEach(function (s) {
          occurrences[s] = Array.isArray(concRaw[s]) ? concRaw[s].length : 0;
        });
      }
      filteredEntries = allEntries;
      buildRootIndex();
      render();
    }).catch(function (err) {
      root.innerHTML = '<p class="lex-error">Impossible de charger le lexique. R\u00e9essayez plus tard.</p>';
      console.error('[Lexique hebreu biblique]', err);
    });
  }

  function buildConceptIndex(concepts) {
    if (!Array.isArray(concepts)) return;
    concepts.forEach(function (c) {
      var label = (c.label || '').toLowerCase().trim();
      if (label && !conceptIndex[label]) {
        conceptIndex[label] = getSlug(c.label, label);
      }
    });
  }

  function buildRootIndex() {
    var seen = {};
    Object.keys(rootFamilies).forEach(function (strongId) {
      var rf = rootFamilies[strongId];
      if (!rf || !rf.r) return;
      var r = rf.r;
      if (!rootIndex[r]) rootIndex[r] = [];
      // Add root entry itself
      if (!seen[strongId]) {
        seen[strongId] = true;
        var entry = findEntry(strongId);
        rootIndex[r].push({
          s: strongId,
          h: entry ? entry.h : '',
          x: entry ? (entry.x || '') : '',
          g: entry ? (entry.g && entry.g[0] ? entry.g[0] : '') : '',
          p: entry ? entry.p : '',
          o: occurrences[strongId] || 0
        });
      }
      // Add siblings
      if (rf.f) {
        rf.f.forEach(function (sib) {
          if (!seen[sib.s]) {
            seen[sib.s] = true;
            rootIndex[r].push({
              s: sib.s, h: sib.h || '', x: sib.x || '', g: sib.g || '', p: sib.p || '',
              o: occurrences[sib.s] || 0
            });
          }
        });
      }
    });
  }

  function findEntry(strongId) {
    for (var i = 0; i < allEntries.length; i++) {
      if (allEntries[i].s === strongId) return allEntries[i];
    }
    return null;
  }

  function getSlug(label, key) {
    if (slugMap[label]) return slugMap[label];
    if (slugMap[key]) return slugMap[key];
    return encodeURIComponent((key || label.toLowerCase()).replace(/\s+/g, '-').replace(/['']/g, '-'));
  }

  // ── Normalization for search ──
  function normalize(s) {
    return (s || '').toLowerCase()
      .replace(/[\u02BC\u02BB\u02BE\u02BF\u0027\u2018\u2019]/g, '')
      .replace(/[\u0103\u0101\u00E2\u00E0\u00E4]/g, 'a')
      .replace(/[\u0113\u00EA\u00E8\u00E9\u00EB]/g, 'e')
      .replace(/[\u012B\u00EE\u00EF]/g, 'i')
      .replace(/[\u014D\u00F4\u00F6]/g, 'o')
      .replace(/[\u016B\u00FB\u00FC]/g, 'u')
      .replace(/\u1E25/g, 'h')
      .replace(/\u1E33/g, 'k')
      .replace(/\u1E63/g, 's')
      .replace(/\u1E6D/g, 't')
      .replace(/[\u015B\u015D]/g, 's')
      .replace(/\s+/g, ' ').trim();
  }

  // ── Browse: Search / filter ──
  function doSearch(query) {
    currentQuery = query;
    currentPage = 0;
    if (!query || query.length < 2) {
      filteredEntries = allEntries;
    } else {
      var q = normalize(query);
      var isStrong = /^h?\d+$/i.test(q);
      if (isStrong) {
        var num = q.replace(/^h/i, '');
        filteredEntries = allEntries.filter(function (e) {
          return e.s && e.s.replace(/^H/i, '') === num;
        });
      } else {
        filteredEntries = allEntries.filter(function (e) {
          return (e.h && e.h.indexOf(query) !== -1)
            || (e.x && normalize(e.x).indexOf(q) !== -1)
            || (e.d && normalize(e.d).indexOf(q) !== -1)
            || (e.se && e.se.some(function (sense) {
              return normalize(sense.d || '').indexOf(q) !== -1;
            }));
        });
      }
    }
    renderBrowse();
  }

  // ── Main render ──
  function render() {
    root.innerHTML = '';

    // Tabs
    var tabsHtml = '<div class="lex-tabs">'
      + '<button class="lex-tab' + (currentView === 'browse' ? ' active' : '') + '" type="button" data-view="browse">Parcourir le lexique</button>'
      + '<button class="lex-tab' + (currentView === 'arbre' ? ' active' : '') + '" type="button" data-view="arbre">Arbre des racines</button>'
      + '</div>';

    // View containers
    var browseHtml = '<div id="lex-browse"' + (currentView !== 'browse' ? ' hidden' : '') + '></div>';
    var arbreHtml = '<div id="lex-arbre"' + (currentView !== 'arbre' ? ' hidden' : '') + '></div>';

    root.innerHTML = tabsHtml + browseHtml + arbreHtml;

    // Wire tabs
    root.querySelectorAll('.lex-tab').forEach(function (tab) {
      tab.addEventListener('click', function () {
        switchView(tab.getAttribute('data-view'));
      });
    });

    // Handle hash
    handleHash();

    // Initial render of active view
    if (currentView === 'browse') {
      renderBrowse();
    } else {
      renderArbre();
    }
  }

  function switchView(view) {
    currentView = view;
    root.querySelectorAll('.lex-tab').forEach(function (t) {
      t.classList.toggle('active', t.getAttribute('data-view') === view);
    });
    var browseEl = document.getElementById('lex-browse');
    var arbreEl = document.getElementById('lex-arbre');
    if (browseEl) browseEl.hidden = (view !== 'browse');
    if (arbreEl) arbreEl.hidden = (view !== 'arbre');

    if (view === 'browse') {
      renderBrowse();
    } else {
      renderArbre();
    }
  }

  function handleHash() {
    var hash = decodeURIComponent(window.location.hash.substring(1));
    if (!hash) return;
    if (/^racine=/.test(hash)) {
      currentView = 'arbre';
      selectedRoot = resolveRoot(hash.replace('racine=', ''));
      root.querySelectorAll('.lex-tab').forEach(function (t) {
        t.classList.toggle('active', t.getAttribute('data-view') === 'arbre');
      });
      var browseEl = document.getElementById('lex-browse');
      var arbreEl = document.getElementById('lex-arbre');
      if (browseEl) browseEl.hidden = true;
      if (arbreEl) arbreEl.hidden = false;
      renderArbre();
    } else if (/^H\d+$/i.test(hash)) {
      currentView = 'browse';
      var searchInput = document.querySelector('#lex-browse .lex-search');
      if (searchInput) searchInput.value = hash;
      doSearch(hash);
    }
  }

  // Normalize Hebrew root: strip niqqud/cantillation, replace final letters with normal
  function normalizeRoot(r) {
    return r
      .replace(/[\u0591-\u05C7]/g, '')  // strip niqqud & cantillation marks
      .replace(/\u05DA/g, '\u05DB')     // kaf sofit → kaf
      .replace(/\u05DD/g, '\u05DE')     // mem sofit → mem
      .replace(/\u05DF/g, '\u05E0')     // nun sofit → nun
      .replace(/\u05E3/g, '\u05E4')     // pe sofit → pe
      .replace(/\u05E5/g, '\u05E6');    // tsade sofit → tsade
  }

  function resolveRoot(r) {
    if (rootIndex[r]) return r;
    var norm = normalizeRoot(r);
    if (rootIndex[norm]) return norm;
    return r;
  }

  // ══════════════════════════════════════════════════════════
  //  BROWSE VIEW
  // ══════════════════════════════════════════════════════════

  function renderBrowse() {
    var container = document.getElementById('lex-browse');
    if (!container) return;

    // Only build the shell once
    if (!container.querySelector('.lex-search')) {
      var statsHtml = '<div class="lex-stats">'
        + '<span class="lex-stat"><strong>' + allEntries.length + '</strong> entr\u00e9es h\u00e9bra\u00efques</span>'
        + '<span class="lex-stat">Strong H1 \u2013 H' + allEntries.length + '</span>'
        + '</div>';

      var searchHtml = '<div class="lex-search-wrap">'
        + '<input type="text" class="lex-search" '
        + 'placeholder="Rechercher par num\u00e9ro Strong, mot h\u00e9breu, translit\u00e9ration ou d\u00e9finition\u2026" autocomplete="off" />'
        + '</div>';

      container.innerHTML = statsHtml + searchHtml
        + '<div id="lex-hebrew-controls-slot"></div>'
        + '<div id="lex-results"></div>'
        + '<div id="lex-pagination" class="lex-pagination"></div>';

      // Injection de la barre de contr\u00f4le Hebrew (toggle masquer / translit auto)
      if (window.FIGUIER_HEBREW_UTILS && typeof window.FIGUIER_HEBREW_UTILS.createHebrewControlsBar === 'function') {
        var slot = container.querySelector('#lex-hebrew-controls-slot');
        if (slot) {
          slot.appendChild(window.FIGUIER_HEBREW_UTILS.createHebrewControlsBar());
        }
      }

      var searchInput = container.querySelector('.lex-search');
      var debounceTimer;
      searchInput.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        var val = this.value.trim();
        debounceTimer = setTimeout(function () { doSearch(val); }, 250);
      });

      if (currentQuery) {
        searchInput.value = currentQuery;
      }
    }

    renderEntries();
  }

  function renderEntries() {
    var container = document.getElementById('lex-results');
    if (!container) return;
    var start = currentPage * PAGE_SIZE;
    var end = Math.min(start + PAGE_SIZE, filteredEntries.length);
    var page = filteredEntries.slice(start, end);

    if (filteredEntries.length === 0) {
      container.innerHTML = '<div class="lex-no-result">Aucune entr\u00e9e trouv\u00e9e'
        + (currentQuery ? ' pour \u00ab ' + escHtml(currentQuery) + ' \u00bb' : '') + '</div>';
      document.getElementById('lex-pagination').innerHTML = '';
      return;
    }

    var html = '<div class="lex-count">' + filteredEntries.length + ' r\u00e9sultat'
      + (filteredEntries.length > 1 ? 's' : '') + '</div>';

    html += '<div class="lex-entries">';
    page.forEach(function (entry) {
      html += renderCard(entry);
    });
    html += '</div>';
    container.innerHTML = html;

    // Wire BDB legend toggles
    _wireBdbLegendToggles(container);

    // Re-applique les pre\u0301fe\u0301rences h\u00e9breu (translit auto + masquage) sur le DOM re-rendu
    if (window.FIGUIER_HEBREW_UTILS && typeof window.FIGUIER_HEBREW_UTILS.applyHebrewPrefs === 'function') {
      window.FIGUIER_HEBREW_UTILS.applyHebrewPrefs();
    }

    // Wire root sibling clicks
    container.querySelectorAll('.lex-root-sib').forEach(function (sib) {
      sib.addEventListener('click', function (evt) {
        evt.preventDefault();
        var strong = sib.getAttribute('data-strong');
        if (!strong) return;
        var target = document.getElementById(strong);
        if (target) {
          target.classList.add('lex-card--highlight');
          target.scrollIntoView({ behavior: 'smooth', block: 'center' });
          setTimeout(function () { target.classList.remove('lex-card--highlight'); }, 1500);
        } else {
          var searchInput = container.closest('#lex-browse').querySelector('.lex-search');
          if (searchInput) searchInput.value = strong;
          doSearch(strong);
        }
      });
    });

    // Wire "more" expand buttons
    container.querySelectorAll('.lex-root-more').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var extra = btn.parentNode.querySelector('.lex-root-extra');
        if (extra) { extra.hidden = false; btn.hidden = true; }
      });
    });

    // Wire "Voir l'arbre" links
    container.querySelectorAll('.lex-root-arbre-link').forEach(function (link) {
      link.addEventListener('click', function (evt) {
        evt.preventDefault();
        var r = link.getAttribute('data-root');
        if (r) {
          selectedRoot = resolveRoot(r);
          switchView('arbre');
        }
      });
    });

    renderPagination();
  }

  // === HELPERS LEXIQUE HEBREU BIBLIQUE (tiers T1-T7) ===

  // OSIS -> BYM book info {file, code} (compatible avec handler verse-bubble de bible-v3-patch.js)
  var OSIS_TO_BYM_BOOK_LEX = {
    Gen:   {file:'Genese',       code:'01'},
    Exod:  {file:'Exode',        code:'02'},
    Lev:   {file:'Levitique',    code:'03'},
    Num:   {file:'Nombres',      code:'04'},
    Deut:  {file:'Deuteronome',  code:'05'},
    Josh:  {file:'Josue',        code:'06'},
    Judg:  {file:'Juges',        code:'07'},
    '1Sam':{file:'1Samuel',      code:'08'},
    '2Sam':{file:'2Samuel',      code:'09'},
    '1Kgs':{file:'1Rois',        code:'10'},
    '2Kgs':{file:'2Rois',        code:'11'},
    Isa:   {file:'Esaie',        code:'12'},
    Jer:   {file:'Jeremie',      code:'13'},
    Ezek:  {file:'Ezechiel',     code:'14'},
    Hos:   {file:'Osee',         code:'15'},
    Joel:  {file:'Joel',         code:'16'},
    Amos:  {file:'Amos',         code:'17'},
    Obad:  {file:'Abdias',       code:'18'},
    Jonah: {file:'Jonas',        code:'19'},
    Mic:   {file:'Michee',       code:'20'},
    Nah:   {file:'Nahoum',       code:'21'},
    Hab:   {file:'Habacuc',      code:'22'},
    Zeph:  {file:'Sophonie',     code:'23'},
    Hag:   {file:'Aggee',        code:'24'},
    Zech:  {file:'Zacharie',     code:'25'},
    Mal:   {file:'Malachie',     code:'26'},
    Ps:    {file:'Psaumes',      code:'27'},
    Prov:  {file:'Proverbes',    code:'28'},
    Job:   {file:'Job',          code:'29'},
    Song:  {file:'Cantique',     code:'30'},
    Ruth:  {file:'Ruth',         code:'31'},
    Lam:   {file:'Lamentations', code:'32'},
    Eccl:  {file:'Ecclesiaste',  code:'33'},
    Esth:  {file:'Esther',       code:'34'},
    Dan:   {file:'Daniel',       code:'35'},
    Ezra:  {file:'Esdras',       code:'36'},
    Neh:   {file:'Nehemie',      code:'37'},
    '1Chr':{file:'1Chroniques',  code:'38'},
    '2Chr':{file:'2Chroniques',  code:'39'}
  };
  function lexParseBymRef(osisRef) {
    if (!osisRef || typeof osisRef !== 'string') return null;
    var parts = osisRef.split('-');
    var m1 = /^(\w+)\.(\d+)\.(\d+)$/.exec(parts[0]);
    if (!m1) return null;
    var book = OSIS_TO_BYM_BOOK_LEX[m1[1]];
    if (!book) return null;
    var out = { file: book.code + '-' + book.file + '.md', code: book.code, chapter: parseInt(m1[2], 10), verse: parseInt(m1[3], 10), verseEnd: null };
    if (parts.length > 1) {
      var m2 = /^(\w+)\.(\d+)\.(\d+)$/.exec(parts[1]);
      if (m2 && m2[1] === m1[1] && m2[2] === m1[2]) out.verseEnd = parseInt(m2[3], 10);
    }
    return out;
  }

  var OSTERWALD_BOOKS = {
    Gen:'Gn', Exod:'Ex', Lev:'Lv', Num:'Nb', Deut:'Dt',
    Josh:'Jos', Judg:'Jg', Ruth:'Rt', '1Sam':'1 S', '2Sam':'2 S',
    '1Kgs':'1 R', '2Kgs':'2 R', '1Chr':'1 Ch', '2Chr':'2 Ch',
    Ezra:'Esd', Neh:'N\u00e9', Esth:'Est', Job:'Jb', Ps:'Ps',
    Prov:'Pr', Eccl:'Ec', Song:'Ct', Isa:'\u00c9s', Jer:'Jr',
    Lam:'Lm', Ezek:'\u00c9z', Dan:'Dn', Hos:'Os', Joel:'Jl',
    Amos:'Am', Obad:'Ab', Jonah:'Jon', Mic:'Mi', Nah:'Na',
    Hab:'Ha', Zeph:'So', Hag:'Ag', Zech:'Za', Mal:'Ml'
  };

  function lexOsterwaldRef(osisRef) {
    if (!osisRef || typeof osisRef !== 'string') return '';
    var parts = osisRef.split('-');
    function parseOne(s) {
      var m = /^(\w+)\.(\d+)\.(\d+)$/.exec(s);
      if (!m) return null;
      return { book: m[1], chap: m[2], verse: m[3] };
    }
    var a = parseOne(parts[0]);
    if (!a) return osisRef;
    var bookA = OSTERWALD_BOOKS[a.book] || a.book;
    if (parts.length === 1) return bookA + ' ' + a.chap + ':' + a.verse;
    var b = parseOne(parts[1]);
    if (!b) return bookA + ' ' + a.chap + ':' + a.verse;
    if (a.book === b.book && a.chap === b.chap) {
      return bookA + ' ' + a.chap + ':' + a.verse + '-' + b.verse;
    }
    if (a.book === b.book) {
      return bookA + ' ' + a.chap + ':' + a.verse + ' \u2013 ' + b.chap + ':' + b.verse;
    }
    var bookB = OSTERWALD_BOOKS[b.book] || b.book;
    return bookA + ' ' + a.chap + ':' + a.verse + ' \u2013 ' + bookB + ' ' + b.chap + ':' + b.verse;
  }

  function lexWrapHebrewInline(escaped) {
    return escaped.replace(/[\u0590-\u05FF]+(?:\s+[\u0590-\u05FF]+)*/g, function (m) {
      return '<span class="fb-inline-he" dir="rtl">' + m + '</span>';
    });
  }
  function escHtmlHe(text) {
    return lexWrapHebrewInline(escHtml(text));
  }

  // Dictionnaire d'abbre\u0301viations BDB (grammaticales + livres bibliques + autres).
  // Utilise\u0301 pour ajouter des tooltips HTML via formatBdbText.
  var BDB_ABBREV_GRAM = {
    'Pf.': 'Parfait (action acheve\u0301e)',
    'Impf.': 'Imparfait (action inacheve\u0301e / future)',
    'Imv.': 'Impe\u0301ratif',
    'Inf.': 'Infinitif',
    'Inf. abs.': 'Infinitif absolu',
    'Inf. cstr.': 'Infinitif construit',
    'Inf. constr.': 'Infinitif construit',
    'Pt.': 'Participe',
    'Pt. act.': 'Participe actif',
    'Pt. pass.': 'Participe passif',
    'cstr.': 'E\u0301tat construit',
    'constr.': 'E\u0301tat construit',
    'abs.': 'E\u0301tat absolu',
    'fig.': 'Sens figure\u0301',
    'sq.': 'suivi de',
    'supr.': 'plus haut dans l\u2019entre\u0301e',
    'infr.': 'plus bas dans l\u2019entre\u0301e',
    'v.': 'voir',
    'cf.': 'comparer avec',
    'pl.': 'pluriel',
    'sg.': 'singulier',
    'm.': 'masculin',
    'f.': 'fe\u0301minin',
    'c.': 'commun',
    'id.': 'me\u0302me signification',
    'sim.': 'similaire',
    'esp.': 'spe\u0301cialement',
    'prob.': 'probablement',
    'rd.': 'lire',
    'abb.': 'abre\u0301ge\u0301',
    'vb.': 'verbe',
    'adj.': 'adjectif',
    'adv.': 'adverbe',
    'subst.': 'substantif',
    'n. m.': 'nom masculin',
    'n. f.': 'nom fe\u0301minin',
    'etc.': 'etcetera (et autres)',
    'intrans.': 'intransitif',
    'trans.': 'transitif',
    'acc.': 'accusatif (objet direct)',
    'du.': 'duel (deux)',
    'coll.': 'collectif',
    'denom.': 'de\u0301nominatif',
    'part.': 'particule',
    'prop.': 'proprement',
    'gen.': 'ge\u0301ne\u0301ralement',
    'specif.': 'spe\u0301cifiquement',
    'rel.': 'relatif',
    'abst.': 'abstrait',
    'coh.': 'cohortatif',
    'juss.': 'jussif',
    // Sources documentaires bibliques
    'JE': 'Source Je\u0301hoviste-E\u0301lohiste (critique documentaire)',
    'JED': 'Sources J, E et D combine\u0301es',
  };

  var BDB_ABBREV_BOOKS = {
    'Gn':'Gene\u0300se', 'Ex':'Exode', 'Lv':'Le\u0301vitique', 'Nb':'Nombres', 'Dt':'Deute\u0301ronome',
    'Jos':'Josue\u0301', 'Jg':'Juges', 'Rt':'Ruth',
    '1 S':'1 Samuel', '2 S':'2 Samuel', '1 R':'1 Rois', '2 R':'2 Rois',
    '1 Ch':'1 Chroniques', '2 Ch':'2 Chroniques',
    'Esd':'Esdras', 'Ne\u0301':'Ne\u0301he\u0301mie', 'Est':'Esther',
    'Jb':'Job', 'Ps':'Psaumes', 'Pr':'Proverbes', 'Ec':'Eccle\u0301siaste', 'Ct':'Cantique',
    'E\u0301s':'E\u0301sai\u0308e', 'Jr':'Je\u0301re\u0301mie', 'Lm':'Lamentations', 'E\u0301z':'E\u0301ze\u0301chiel', 'Dn':'Daniel',
    'Os':'Ose\u0301e', 'Jl':'Joe\u0308l', 'Am':'Amos', 'Ab':'Abdias', 'Jon':'Jonas',
    'Mi':'Miche\u0301e', 'Na':'Nahum', 'Ha':'Habaquq', 'So':'Sophonie',
    'Ag':'Agge\u0301e', 'Za':'Zacharie', 'Ml':'Malachie',
    'Je':'Je\u0301re\u0301mie', // BDB utilise parfois "Je" au lieu de "Jr"
    '\u03C8':'Psaumes (symbole grec psi)',
  };

  var BDB_ABBREV_LANG = {
    'As.': 'Assyrien',
    'Aram.': 'Arame\u0301en',
    'Syr.': 'Syriaque',
    'Ar.': 'Arabe',
    'Eth.': 'E\u0301thiopien',
    'Sab.': 'Sabe\u0301en',
    'LXX': 'Septante (traduction grecque AT)',
    'Vulg.': 'Vulgate (traduction latine)',
    'Tg.': 'Targoum (paraphrase arame\u0301enne)',
    'Q':'Qere\u0301 (lecture marginale)',
    'Kt':'Ketiv (lecture du texte)',
  };

  function _allAbbrev() {
    var all = {};
    for (var k in BDB_ABBREV_GRAM) all[k] = BDB_ABBREV_GRAM[k];
    for (var k2 in BDB_ABBREV_BOOKS) all[k2] = BDB_ABBREV_BOOKS[k2];
    for (var k3 in BDB_ABBREV_LANG) all[k3] = BDB_ABBREV_LANG[k3];
    return all;
  }

  // Rendu du panneau le\u0301gende (par de\u0301faut cache\u0301, toggle via bouton).
  function _renderBdbLegend() {
    function dlItems(dict) {
      var keys = Object.keys(dict).sort();
      return keys.map(function (k) {
        return '<div class="lex-legend-item"><dt>' + escHtml(k) + '</dt><dd>' + escHtml(dict[k]) + '</dd></div>';
      }).join('');
    }
    return '<div class="lex-bdb-legend" id="lex-bdb-legend-panel" hidden>' +
      '<div class="lex-legend-cols">' +
        '<section class="lex-legend-col">' +
          '<h4>Grammaticales</h4>' +
          '<dl>' + dlItems(BDB_ABBREV_GRAM) + '</dl>' +
        '</section>' +
        '<section class="lex-legend-col">' +
          '<h4>Livres bibliques</h4>' +
          '<dl>' + dlItems(BDB_ABBREV_BOOKS) + '</dl>' +
        '</section>' +
        '<section class="lex-legend-col">' +
          '<h4>Versions &amp; langues</h4>' +
          '<dl>' + dlItems(BDB_ABBREV_LANG) + '</dl>' +
        '</section>' +
      '</div>' +
    '</div>';
  }

  // Attache le comportement toggle sur tous les boutons de legende (une fois a\u0300 l'init du lexique)
  function _wireBdbLegendToggles(root) {
    var btns = (root || document).querySelectorAll('.lex-bdb-legend-toggle');
    btns.forEach(function (btn) {
      if (btn._wired) return;
      btn._wired = true;
      btn.addEventListener('click', function () {
        var expanded = btn.getAttribute('aria-expanded') === 'true';
        var panel = btn.closest('.lex-def-full') && btn.closest('.lex-def-full').querySelector('.lex-bdb-legend');
        if (!panel) return;
        if (expanded) {
          panel.setAttribute('hidden', '');
          btn.setAttribute('aria-expanded', 'false');
        } else {
          panel.removeAttribute('hidden');
          btn.setAttribute('aria-expanded', 'true');
        }
      });
    });
  }

  // Enveloppe les abbre\u0301viations reconnues dans du HTML avec tooltip.
  // Matche mot entier, e\u0301vite les substitutions dans du HTML attr.
  function _linkifyAbbrevs(html) {
    var all = _allAbbrev();
    // Sort by longueur decroissante pour matcher les composes d'abord (Inf. abs. avant Inf.)
    var keys = Object.keys(all).sort(function (a, b) { return b.length - a.length; });
    // Escape regex special chars in keys
    var escRe = function (s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); };
    // Construit un pattern OR des abbre\u0301viations + word boundary
    // Pour les abbre\u0301viations avec point (Pf., Impf.), le point est inclus dans le match
    // Pour les mots sans point (Gn, Jg), on require un word boundary apres ET un chiffre suivant optionnel
    var patterns = keys.map(function (k) { return escRe(k); });
    // Ajoute un lookahead pour eviter match dans autre mot
    var bigRe = new RegExp('(^|[^\\w])(' + patterns.join('|') + ')(?=[\\s.,;:)\\]]|$)', 'g');
    return html.replace(bigRe, function (m, prefix, abbr) {
      var title = all[abbr];
      if (!title) return m;
      return prefix + '<abbr class="lex-abbrev" title="' + escHtml(title) + '">' + abbr + '</abbr>';
    });
  }

  // Formatte le texte BDB (definition complete) en paragraphes par stem.
  // Detecte les debuts de section verbale (Qal, Niph., Pi., Pu., Hiph., Hoph.,
  // Hithp., Hithpo., Po‛l, Polel, Pilpel) et les met en evidence.
  // Detecte aussi les sous-sections (Pf., Impf., Pt., Imv., Inf.) comme paragraphes plus petits.
  function formatBdbText(text) {
    if (!text) return '';
    // 1. Escape + wrap hebrew inline + linkify abbreviations (tooltips)
    var html = _linkifyAbbrevs(escHtmlHe(text));
    // 2. Detecter les stems en debut de section :
    //    precede de " — " (tiret cadratin), " ; " ou debut du texte,
    //    suivi d'un mot grammatical (Pf/Impf/Pt/Imv/Inf) ou ponctuation.
    //    Pour eviter faux positifs (ex: "cf. Pi. supr."), on exige un contexte de debut de section.
    var stemPattern = /(^|[\u2014\u2013]\s*|\.\s+|;\s+)(Qal\b|Niph\.|Pi\.|Pu\.|Hiph\.|Hoph\.|Hithp\.|Hithpo\.|Po[\u2018\u2019\u02BB\u02BC']l\.?|Polel\b|Pilpel\b|Polp\.|Pilp\.|Hishtaph\.?)/g;
    // On separe le texte en tokens : partie avant stem + [stem + body] repetes
    var tokens = [];
    var lastEnd = 0;
    var m;
    while ((m = stemPattern.exec(html)) !== null) {
      // Ajout du texte avant
      if (m.index > lastEnd) {
        tokens.push({ type: 'text', content: html.slice(lastEnd, m.index) + (m[1] || '') });
      }
      tokens.push({ type: 'stem', name: m[2] });
      lastEnd = m.index + m[0].length;
    }
    if (lastEnd < html.length) {
      tokens.push({ type: 'text', content: html.slice(lastEnd) });
    }

    // Si pas de stem detecte, retourner le texte simple
    if (!tokens.some(function (t) { return t.type === 'stem'; })) {
      return '<div class="lex-bdb-flow">' + html + '</div>';
    }

    // Construire le HTML : intro (avant premier stem) + sections
    var out = '';
    var i = 0;
    // Intro
    if (tokens[0] && tokens[0].type === 'text') {
      var introText = tokens[0].content.trim();
      if (introText) {
        out += '<div class="lex-bdb-intro">' + introText + '</div>';
      }
      i = 1;
    }
    // Sections
    while (i < tokens.length) {
      if (tokens[i].type === 'stem') {
        var stem = tokens[i].name;
        var body = '';
        if (i + 1 < tokens.length && tokens[i + 1].type === 'text') {
          body = tokens[i + 1].content.trim();
          i += 2;
        } else {
          i += 1;
        }
        // Sous-decouper le body par marqueurs grammaticaux (Pf., Impf., Pt., Imv., Inf., etc.)
        var formattedBody = _formatBdbSubsection(body);
        out += '<div class="lex-bdb-section">' +
          '<strong class="lex-bdb-stem-label">' + stem + '</strong>' +
          (formattedBody ? ' ' + formattedBody : '') +
          '</div>';
      } else {
        i += 1;
      }
    }
    return out;
  }

  // De\u0301coupe le corps d'une section stem par marqueurs grammaticaux.
  // Resultat : `<span class="lex-bdb-gram-intro">intro</span>`
  // + `<div class="lex-bdb-subsection"><strong class="lex-bdb-gram">Pf.</strong> body</div>` repetes.
  function _formatBdbSubsection(body) {
    if (!body) return '';
    // Pattern des marqueurs grammaticaux (apres ';' ou debut)
    // Attention : "Inf. abs." et "Inf. cstr." doivent matcher AVANT "Inf." seul.
    var gramPattern = /(^|;\s+|\.\s+(?=[A-Z]))(Inf\.\s+abs\.|Inf\.\s+cstr\.|Inf\.\s+constr\.|Pt\.\s+act\.|Pt\.\s+pass\.|Pf\.|Impf\.|Imv\.|Inf\.|Pt\.|cstr\.|abs\.|fig\.)\b/g;
    var tokens = [];
    var lastEnd = 0;
    var m;
    while ((m = gramPattern.exec(body)) !== null) {
      if (m.index > lastEnd) {
        tokens.push({ type: 'text', content: body.slice(lastEnd, m.index) + (m[1] || '') });
      }
      tokens.push({ type: 'gram', name: m[2] });
      lastEnd = m.index + m[0].length;
    }
    if (lastEnd < body.length) {
      tokens.push({ type: 'text', content: body.slice(lastEnd) });
    }
    if (!tokens.some(function (t) { return t.type === 'gram'; })) {
      return body;
    }
    var out = '';
    var i = 0;
    // Intro avant premier marqueur
    if (tokens[0] && tokens[0].type === 'text') {
      var intro = tokens[0].content.trim();
      if (intro) {
        out += '<span class="lex-bdb-gram-intro">' + intro + '</span>';
      }
      i = 1;
    }
    while (i < tokens.length) {
      if (tokens[i].type === 'gram') {
        var gram = tokens[i].name;
        var txt = '';
        if (i + 1 < tokens.length && tokens[i + 1].type === 'text') {
          txt = tokens[i + 1].content.trim();
          i += 2;
        } else {
          i += 1;
        }
        out += '<div class="lex-bdb-subsection">' +
          '<strong class="lex-bdb-gram">' + gram + '</strong>' +
          (txt ? ' ' + txt : '') +
          '</div>';
      } else {
        i += 1;
      }
    }
    return out;
  }
  function lexStrongLinkify(text) {
    var html = lexWrapHebrewInline(escHtml(text));
    return html.replace(/\b(\d{1,4})\b/g, function (m, num) {
      return '<a class="lex-strong-link" href="#H' + num + '" data-strong="H' + num + '">' + num + '</a>';
    });
  }

  function lexStemTooltip(stem) {
    var tips = {
      'Qal':    'Qal : forme verbale simple, active, basique',
      'Niph':   'Niphal : forme verbale passive ou r\u00e9fl\u00e9chie',
      'Pi':     'Piel : intensif actif',
      'Pu':     'Pual : intensif passif',
      'Hiph':   'Hiphil : causatif actif',
      'Hoph':   'Hophal : causatif passif',
      'Hithp':  'Hithpael : r\u00e9fl\u00e9chi intensif',
      'Hithpo': 'Hithpolel : r\u00e9fl\u00e9chi poly-lel\u00e9 (racines creuses)',
      'Po\u02bbl': 'Polel : forme intensive des racines creuses (comme Piel)',
      'Pol':    'Polel : forme intensive des racines creuses',
      'Polel':  'Polel : forme intensive des racines creuses',
      'Pol\u02bb': 'Polel : forme intensive des racines creuses',
      'Pilp':   'Pilpel : redoublement de la racine (intensif)',
      'Pilpel': 'Pilpel : redoublement de la racine (intensif)',
      'Polp':   'Polpal : passif du Polel',
      'Polpal': 'Polpal : passif du Polel',
      'Hishtaph':'Hishtaphel : forme se prosterner (\u05D7\u05D5\u05D4)',
      'Tiph':   'Tiphel : forme rare causative',
      'Palel':  'Palel : forme rare intensive'
    };
    return tips[stem] || '';
  }

  function lexRenderSenseItem(s) {
    var nAttr = s.n ? ' data-n="' + escHtml(s.n) + '"' : '';
    var def = escHtmlHe(s.d || '');
    var subHtml = '';
    if (Array.isArray(s.c) && s.c.length > 0) {
      subHtml = '<ol class="lex-sense-sublist">' +
        s.c.map(lexRenderSenseItem).join('') + '</ol>';
    }
    return '<li' + nAttr + '>' + def + subHtml + '</li>';
  }

  function lexRenderSensesT5(entry) {
    var senses = entry.se;
    if (!Array.isArray(senses) || senses.length === 0) {
      if (Array.isArray(entry.bd) && entry.bd.length > 0) {
        return '<div class="lex-senses-block">' +
          '<div class="lex-senses-title">Sens et emplois</div>' +
          '<div class="lex-stem-group">' +
          '<span class="lex-stem-label" title="Usages principales">Usages</span>' +
          '<ol class="lex-sense-list">' +
          entry.bd.map(function (d) { return '<li>' + escHtmlHe(d) + '</li>'; }).join('') +
          '</ol></div></div>';
      }
      return '';
    }

    var groups = [];
    var byStem = {};
    senses.forEach(function (s) {
      var st = (s.st || '').trim();
      if (!(st in byStem)) { byStem[st] = []; groups.push({ stem: st, items: byStem[st] }); }
      byStem[st].push(s);
    });
    var hasAnyStem = groups.some(function (g) { return g.stem; });

    return '<div class="lex-senses-block">' +
      '<div class="lex-senses-title">Sens et emplois</div>' +
      groups.map(function (g) {
        var label = g.stem || (hasAnyStem ? 'Autres' : 'Usages');
        var tip = g.stem ? lexStemTooltip(g.stem) : '';
        var tipAttr = tip ? ' title="' + escHtml(tip) + '"' : '';
        return '<div class="lex-stem-group">' +
          '<span class="lex-stem-label"' + tipAttr + '>' + escHtml(label) + '</span>' +
          '<ol class="lex-sense-list">' +
          g.items.map(lexRenderSenseItem).join('') +
          '</ol></div>';
      }).join('') +
    '</div>';
  }

  function lexRenderBdbRefsT6(br) {
    if (!Array.isArray(br) || br.length === 0) return '';
    return '<div class="lex-refs">' +
      '<div class="lex-refs-label">Passages bibliques</div>' +
      '<div class="lex-refs-list">' +
      br.map(function (r) {
        var info = lexParseBymRef(r);
        var label = escHtml(lexOsterwaldRef(r));
        if (info) {
          var verseEndAttr = info.verseEnd ? ' data-verse-end="' + info.verseEnd + '"' : '';
          return '<span class="lex-ref-link fb-ref-badge"' +
            ' data-file="' + escHtml(info.file) + '"' +
            ' data-code="' + escHtml(info.code) + '"' +
            ' data-chapter="' + info.chapter + '"' +
            ' data-verse="' + info.verse + '"' +
            verseEndAttr +
            ' title="Ouvrir la bulle verset BYM">' + label + '</span>';
        }
        return '<span class="lex-ref-link">' + label + '</span>';
      }).join(' \u00b7 ') +
      '</div></div>';
  }

  function lexRenderEtymT7(etymText, twot) {
    if (!etymText && !twot) return '';
    var parts = [];
    if (etymText) parts.push(lexStrongLinkify(etymText));
    if (twot) parts.push('<span class="lex-twot">TWOT #' + escHtml(twot) + '</span>');
    return '<div class="lex-etym">' +
      '<span class="lex-etym-label">\u00c9tymologie</span> ' +
      parts.join(' ') +
    '</div>';
  }

  function renderCard(e) {
    var strong = e.s || '';
    var hebrew = e.h || '';
    var translit = e.x || '';
    var pron = e.pr || '';
    var def = e.d || '';

    // T1 : head — Strong + POS (bp si disponible)
    var posLabel = e.bp || e.p || '';
    var posTitle = (e.bp && e.p && e.bp !== e.p) ? (e.bp + ' (Strong: ' + e.p + ')') : posLabel;
    var posHtml = posLabel ? '<span class="lex-pos" title="' + escHtml(posTitle) + '">' + escHtml(posLabel) + '</span>' : '';

    var html = '<div class="lex-card" id="' + strong + '">'
      + '<div class="lex-card-head">'
      + '<span class="lex-strong">' + strong + '</span>'
      + posHtml
      + '<span class="lex-hebrew" dir="rtl">' + hebrew + '</span>'
      + (hebrew ? ' <button class="lex-audio-btn fb-hebrew-card__audio" type="button" data-text="' + escHtml(hebrew) + '" data-lang="he-IL" title="\u00c9couter" aria-label="\u00c9couter la prononciation">\ud83d\udd0a</button>' : '')
      + '</div>';

    // T2 : translit + pron
    if (translit) html += '<div class="lex-translit">' + escHtml(translit) + '</div>';
    if (pron) html += '<div class="lex-pron">' + escHtml(pron) + '</div>';

    // T3 : def courte
    if (def) html += '<div class="lex-def">' + escHtmlHe(def) + '</div>';

    // T4 : def complete BDB (df) formate par section de stem
    var defFull = (e.df && e.df !== def) ? e.df : '';
    if (defFull) {
      html += '<div class="lex-def-full">'
        + '<div class="lex-def-full-header">'
        +   '<span class="lex-def-full-label">D\u00e9finition compl\u00e8te (BDB)</span>'
        +   '<button type="button" class="lex-bdb-legend-toggle" aria-expanded="false" aria-controls="lex-bdb-legend-panel" title="Voir la le\u0301gende des abre\u0301viations">\u24D8 L\u00e9gende</button>'
        + '</div>'
        + _renderBdbLegend()
        + formatBdbText(defFull)
        + '</div>';
    }

    // T5 : Sens et emplois (groupes par stem)
    html += lexRenderSensesT5(e);

    // T6 : Passages bibliques
    html += lexRenderBdbRefsT6(e.br);

    // T7 : Etymologie + TWOT
    html += lexRenderEtymT7(e.et, e.tw);

    // Root family
    var rootData = rootFamilies[strong];
    if (rootData && rootData.r && rootData.f && rootData.f.length > 0) {
      var siblings = rootData.f;
      var showMax = 8;
      var hasMore = siblings.length > showMax;
      html += '<div class="lex-root">';
      html += '<div class="lex-root-head">'
        + '<span class="lex-root-label">Racine</span>'
        + '<span class="lex-root-hebrew" dir="rtl">' + rootData.r + '</span>'
        + '<span class="lex-root-count">' + (siblings.length + 1) + ' mots</span>'
        + '<a href="#" class="lex-root-arbre-link" data-root="' + escHtml(rootData.r) + '">Voir l\'arbre \u2192</a>'
        + '</div>';
      html += '<div class="lex-root-family">';
      var limit = hasMore ? showMax : siblings.length;
      for (var si = 0; si < limit; si++) {
        var sib = siblings[si];
        html += '<a href="#' + escHtml(sib.s) + '" class="lex-root-sib" data-strong="' + escHtml(sib.s) + '">'
          + '<span class="lex-root-sib__h" dir="rtl">' + escHtml(sib.h) + '</span>'
          + '<span class="lex-root-sib__id">' + escHtml(sib.s) + '</span>'
          + (sib.g ? '<span class="lex-root-sib__g">' + escHtml(sib.g) + '</span>' : '')
          + '</a>';
      }
      if (hasMore) {
        html += '<button class="lex-root-more" type="button">+' + (siblings.length - showMax) + ' autres</button>';
        html += '<span class="lex-root-extra" hidden>';
        for (var si2 = showMax; si2 < siblings.length; si2++) {
          var sib2 = siblings[si2];
          html += '<a href="#' + escHtml(sib2.s) + '" class="lex-root-sib" data-strong="' + escHtml(sib2.s) + '">'
            + '<span class="lex-root-sib__h" dir="rtl">' + escHtml(sib2.h) + '</span>'
            + '<span class="lex-root-sib__id">' + escHtml(sib2.s) + '</span>'
            + (sib2.g ? '<span class="lex-root-sib__g">' + escHtml(sib2.g) + '</span>' : '')
            + '</a>';
        }
        html += '</span>';
      }
      html += '</div></div>';
    }

    // Dictionary links
    var links = findDictLinks(e);
    if (links.length > 0) {
      html += '<div class="lex-dict-links"><span class="lex-dict-label">Dans le dictionnaire :</span> ';
      links.forEach(function (link, i) {
        if (i > 0) html += ', ';
        html += '<a href="' + dictBaseUrl + link.slug + '/" class="lex-dict-link">' + escHtml(link.label) + '</a>';
      });
      html += '</div>';
    }

    html += '</div>';
    return html;
  }

  function findDictLinks(entry) {
    var links = [];
    var checked = {};
    var translit = normalize(entry.x || '');
    if (translit.length >= 3) {
      Object.keys(conceptIndex).forEach(function (label) {
        if (checked[label]) return;
        var labelN = normalize(label);
        var tCross = translit.replace(/[^a-z]/g, '').replace(/w/g, '').replace(/([aeiou])h([aeiou])/g, '$1$2');
        var lCross = labelN.replace(/[^a-z]/g, '').replace(/w/g, '').replace(/([aeiou])h([aeiou])/g, '$1$2');
        if (tCross.length >= 4 && lCross.length >= 4 && tCross === lCross) {
          checked[label] = true;
          links.push({ label: label.charAt(0).toUpperCase() + label.slice(1), slug: conceptIndex[label] });
        }
      });
    }
    return links.slice(0, 5);
  }

  function renderPagination() {
    var pag = document.getElementById('lex-pagination');
    if (!pag) return;
    var totalPages = Math.ceil(filteredEntries.length / PAGE_SIZE);
    if (totalPages <= 1) { pag.innerHTML = ''; return; }

    var html = '<div class="lex-pag-info">Page ' + (currentPage + 1) + ' / ' + totalPages + '</div><div class="lex-pag-btns">';
    if (currentPage > 0) {
      html += '<button class="lex-pag-btn" data-page="' + (currentPage - 1) + '">\u2190 Pr\u00e9c\u00e9dent</button>';
    }
    var start = Math.max(0, currentPage - 3);
    var end = Math.min(totalPages, currentPage + 4);
    for (var i = start; i < end; i++) {
      html += '<button class="lex-pag-btn' + (i === currentPage ? ' active' : '') + '" data-page="' + i + '">' + (i + 1) + '</button>';
    }
    if (currentPage < totalPages - 1) {
      html += '<button class="lex-pag-btn" data-page="' + (currentPage + 1) + '">Suivant \u2192</button>';
    }
    html += '</div>';
    pag.innerHTML = html;

    pag.querySelectorAll('.lex-pag-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        currentPage = parseInt(this.getAttribute('data-page'));
        renderEntries();
      });
    });
  }

  // ══════════════════════════════════════════════════════════
  //  ARBRE VIEW
  // ══════════════════════════════════════════════════════════

  function renderArbre() {
    var container = document.getElementById('lex-arbre');
    if (!container) return;

    var rootKeys = Object.keys(rootIndex).sort(function (a, b) {
      return (rootIndex[b].length || 0) - (rootIndex[a].length || 0);
    });
    var totalWords = 0;
    rootKeys.forEach(function (r) { totalWords += rootIndex[r].length; });

    var html = '';

    // Stats
    html += '<div class="arbre-stats">'
      + '<strong>' + rootKeys.length + '</strong> racines h\u00e9bra\u00efques \u00b7 '
      + '<strong>' + totalWords + '</strong> mots'
      + '</div>';

    // Search
    html += '<div class="arbre-search-wrap">'
      + '<input type="text" class="arbre-search" placeholder="Chercher une racine, un mot ou un sens\u2026" value="' + escHtml(arbreQuery) + '" autocomplete="off" />'
      + '</div>';

    // Filter featured roots
    var filteredFeatured = FEATURED;
    if (arbreQuery) {
      var q = arbreQuery.toLowerCase();
      filteredFeatured = FEATURED.filter(function (f) {
        return f.root.indexOf(arbreQuery) !== -1 || f.hint.toLowerCase().indexOf(q) !== -1;
      });
    }

    // Root pills
    html += '<div class="arbre-pills">';
    filteredFeatured.forEach(function (f) {
      var isActive = selectedRoot === f.root;
      html += '<button class="arbre-pill' + (isActive ? ' active' : '') + '" type="button" data-root="' + escHtml(f.root) + '">'
        + '<span class="arbre-pill__hebrew" dir="rtl">' + escHtml(f.root) + '</span>'
        + '<span class="arbre-pill__hint">' + escHtml(f.hint) + '</span>'
        + '</button>';
    });

    // Show non-featured filtered results
    if (arbreQuery && arbreQuery.length >= 1) {
      rootKeys.forEach(function (r) {
        var alreadyFeatured = FEATURED.some(function (f) { return f.root === r; });
        if (alreadyFeatured) return;
        var members = rootIndex[r];
        var match = r.indexOf(arbreQuery) !== -1;
        if (!match) {
          match = members.some(function (m) {
            return (m.g && m.g.toLowerCase().indexOf(arbreQuery.toLowerCase()) !== -1)
              || (m.h && m.h.indexOf(arbreQuery) !== -1);
          });
        }
        if (match) {
          var isActive = selectedRoot === r;
          var hint = members.slice(0, 3).map(function (m) { return m.g || ''; }).filter(Boolean).join(' \u00b7 ');
          html += '<button class="arbre-pill' + (isActive ? ' active' : '') + '" type="button" data-root="' + escHtml(r) + '">'
            + '<span class="arbre-pill__hebrew" dir="rtl">' + escHtml(r) + '</span>'
            + '<span class="arbre-pill__hint">' + escHtml(hint || r) + '</span>'
            + '</button>';
        }
      });
    }
    html += '</div>';

    // Tree visualization
    if (selectedRoot && rootIndex[selectedRoot]) {
      html += renderTree(selectedRoot, rootIndex[selectedRoot]);
    } else {
      html += '<div class="arbre-empty">'
        + '<div class="arbre-empty__hebrew" dir="rtl">\u05E9\u05C1\u05E8\u05E9\u05C1</div>'
        + '<p>S\u00e9lectionnez une racine ci-dessus pour d\u00e9ployer son arbre s\u00e9mantique</p>'
        + '</div>';
    }

    container.innerHTML = html;

    // Wire search
    var searchInput = container.querySelector('.arbre-search');
    var debounceTimer;
    searchInput.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      var val = this.value.trim();
      debounceTimer = setTimeout(function () {
        arbreQuery = val;
        renderArbre();
      }, 200);
    });

    // Wire pills
    container.querySelectorAll('.arbre-pill').forEach(function (pill) {
      pill.addEventListener('click', function () {
        selectedRoot = resolveRoot(pill.getAttribute('data-root'));
        expandedNode = '';
        renderArbre();
      });
    });

    // Wire member expand
    container.querySelectorAll('.arbre-member__btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var s = btn.getAttribute('data-strong');
        expandedNode = (expandedNode === s) ? '' : s;
        renderArbre();
      });
    });

    // Wire "Fiche Strong" links → switch to browse
    container.querySelectorAll('.arbre-link-browse').forEach(function (link) {
      link.addEventListener('click', function (evt) {
        evt.preventDefault();
        var s = link.getAttribute('data-strong');
        if (s) {
          currentQuery = s;
          switchView('browse');
          var searchInput = document.querySelector('#lex-browse .lex-search');
          if (searchInput) searchInput.value = s;
          doSearch(s);
        }
      });
    });

    // Restore search focus
    if (arbreQuery) {
      searchInput.focus();
      searchInput.setSelectionRange(arbreQuery.length, arbreQuery.length);
    }
  }

  function renderTree(rootHebrew, members) {
    // Group by POS
    var groups = {};
    var groupOrder = [];
    members.forEach(function (m) {
      var g = posGroup(m.p);
      if (!groups[g]) {
        groups[g] = [];
        groupOrder.push(g);
      }
      groups[g].push(m);
    });

    // Sort groups by POS_ORDER
    groupOrder.sort(function (a, b) {
      var ai = POS_ORDER.indexOf(a);
      var bi = POS_ORDER.indexOf(b);
      if (ai === -1) ai = 99;
      if (bi === -1) bi = 99;
      return ai - bi;
    });

    // Total occurrences
    var totalOcc = 0;
    var maxOcc = 0;
    members.forEach(function (m) {
      totalOcc += m.o || 0;
      if ((m.o || 0) > maxOcc) maxOcc = m.o;
    });

    // Find root verb or first member for translit + gloss
    var rootMember = null;
    for (var rm = 0; rm < members.length; rm++) {
      if (members[rm].p === 'v') { rootMember = members[rm]; break; }
    }
    if (!rootMember && members.length > 0) rootMember = members[0];
    var rootTranslit = rootMember ? (rootMember.x || '') : '';
    var rootGloss = rootMember ? (rootMember.g || '') : '';

    var html = '<div class="arbre-tree">';

    // Root center
    html += '<div class="arbre-root-center">'
      + '<div class="arbre-root-center__box">'
      + '<span class="arbre-root-center__hebrew" dir="rtl">' + escHtml(rootHebrew) + '</span>'
      + (rootTranslit ? '<span class="arbre-root-center__translit">' + escHtml(rootTranslit) + '</span>' : '')
      + (rootGloss ? '<span class="arbre-root-center__gloss">' + escHtml(rootGloss) + '</span>' : '')
      + '<span class="arbre-root-center__stats">' + members.length + ' mots \u00b7 ' + totalOcc.toLocaleString() + ' occurrences</span>'
      + '</div></div>';

    // Branches
    groupOrder.forEach(function (gKey) {
      var info = posInfo(gKey === 'n-pr' ? 'n-pr-m' : gKey);
      var gMembers = groups[gKey];
      html += '<div class="arbre-branch" style="border-color: ' + info.color + '22; background: ' + info.bg + '">';
      html += '<div class="arbre-branch__head">'
        + '<span class="arbre-branch__dot" style="background: ' + info.color + '"></span>'
        + '<span class="arbre-branch__label" style="color: ' + info.color + '">' + escHtml(info.label) + '</span>'
        + '<span class="arbre-branch__count">' + gMembers.length + ' mot' + (gMembers.length > 1 ? 's' : '') + '</span>'
        + '</div>';
      html += '<div class="arbre-branch__members">';

      gMembers.forEach(function (m) {
        var isExpanded = expandedNode === m.s;
        var occW = maxOcc > 0 ? Math.max(4, Math.round(((m.o || 0) / maxOcc) * 100)) : 4;

        html += '<div class="arbre-member' + (isExpanded ? ' is-expanded' : '') + '">';
        html += '<button class="arbre-member__btn" type="button" data-strong="' + escHtml(m.s) + '">'
          + '<span class="arbre-member__hebrew" dir="rtl">' + escHtml(m.h) + '</span>'
          + (m.x ? '<span class="arbre-member__translit">' + escHtml(m.x) + '</span>' : '')
          + '<span class="arbre-member__gloss">' + escHtml(m.g || '\u2014') + '</span>'
          + '<span class="arbre-occ-bar">'
          + '<span class="arbre-occ-bar__track"><span class="arbre-occ-bar__fill" style="width: ' + occW + '%; background: ' + info.color + '"></span></span>'
          + '<span class="arbre-occ-bar__num">' + (m.o || 0) + '</span>'
          + '</span>'
          + '<span class="arbre-member__arrow">\u25B6</span>'
          + '</button>';

        if (isExpanded) {
          html += '<div class="arbre-member__detail">'
            + '<div class="arbre-member__meta">'
            + '<span class="arbre-member__strong" style="color: ' + info.color + '">' + escHtml(m.s) + '</span>'
            + '<span class="arbre-member__pos">' + escHtml(m.p || '\u2014') + '</span>'
            + '<span class="arbre-member__occ">' + (m.o ? m.o + ' occ. dans le Tanakh' : 'Hapax / rare') + '</span>'
            + '</div>'
            + '<div class="arbre-member__actions">'
            + '<a href="#" class="arbre-link-browse" data-strong="' + escHtml(m.s) + '">Fiche ' + escHtml(m.s) + ' \u2192</a>'
            + '<a href="' + dictBaseUrl + '" class="arbre-link-dict">Dictionnaire \u2192</a>'
            + '</div></div>';
        }
        html += '</div>';
      });

      html += '</div></div>';
    });

    // Legend
    html += '<div class="arbre-legend">';
    ['v', 'n-m', 'n-f', 'a', 'n-pr-m'].forEach(function (key) {
      var info = posInfo(key);
      html += '<span class="arbre-legend__item">'
        + '<span class="arbre-legend__dot" style="background: ' + info.color + '"></span>'
        + escHtml(info.label)
        + '</span>';
    });
    html += '<span class="arbre-legend__item">'
      + '<span class="arbre-legend__bar"></span>Occurrences</span>';
    html += '</div>';

    html += '</div>';
    return html;
  }

  // ── Utilities ──
  function escHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  // ── Boot ──
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.addEventListener('hashchange', function () {
    handleHash();
  });
})();
