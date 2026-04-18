/* ================================================================
   BIBLE V3 PATCH — DOM Restructuring, Verse Bubbles, Hebrew Lexicon
   alombredufiguier.org/dictionnaire-biblique/
   ================================================================
   Ce fichier NE modifie PAS la logique de bible-v2-app.js.
   Il réarrange le DOM après chaque rendu pour activer le layout V3
   et ajoute : bulles verset BYM, cartes du lexique hébreu biblique,
   journey sources, recherche (numéro Strong / hébreu / translittération).
   ================================================================ */

(function () {
  'use strict';

  // ── 0. CONSTANTES & HELPERS ───────────────────────────────────────
  var APP_SEL = '.figuier-bible-app[data-app="bible-v2"]';
  var TOPBAR_SEL = APP_SEL + ' .fb-topbar';
  var CONCEPT_BODY_SEL = APP_SEL + ' .fb-concept-body';
  var CONCEPT_HERO_SEL = APP_SEL + ' .fb-concept-hero';
  var READING_PANEL_SEL = APP_SEL + ' .fb-reading-panel';
  var SEARCH_INPUT_SEL = APP_SEL + ' .fb-search-input';
  var SOURCE_CONTENT_SEL = '.fb-source-content';
  var LAYOUT_CLASS = 'fb-concept-layout';
  var SIDEBAR_CLASS = 'fb-concept-sidebar';
  var BREADCRUMB_CLASS = 'fb-breadcrumb';
  var config = window.FIGUIER_BIBLE_V2_CONFIG || {};

  function escapeHtml(s) {
    return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function truncate(s, n) {
    s = (s || '').trim();
    return s.length <= n ? s : s.slice(0, n).replace(/\s+\S*$/, '') + '…';
  }

  // ── 0b. ROOT FAMILIES ────────────────────────────────────────────────
  var _rootFamilies = null;
  var _rootFamiliesLoading = null;

  function loadRootFamilies() {
    if (_rootFamilies) return Promise.resolve(_rootFamilies);
    if (_rootFamiliesLoading) return _rootFamiliesLoading;
    var baseUrl = (config.manifestUrl || '').replace(/source-manifest\.json.*$/, '');
    _rootFamiliesLoading = fetch(baseUrl + 'strong-root-families.json')
      .then(function (r) { return r.json(); })
      .then(function (data) { _rootFamilies = data; return data; })
      .catch(function () { _rootFamilies = {}; return {}; });
    return _rootFamiliesLoading;
  }

  // ── 0c. CONCORDANCE OSHB ────────────────────────────────────────────
  var _concordance = null;
  var _concordanceLoading = null;

  function loadConcordance() {
    if (_concordance) return Promise.resolve(_concordance);
    if (_concordanceLoading) return _concordanceLoading;
    var baseUrl = (config.manifestUrl || '').replace(/source-manifest\.json.*$/, '');
    _concordanceLoading = fetch(baseUrl + 'strong-concordance-oshb.json')
      .then(function (r) { return r.json(); })
      .then(function (data) { _concordance = data; return data; })
      .catch(function () { _concordance = {}; return {}; });
    return _concordanceLoading;
  }

  // OSHB book abbreviation → BYM file info
  // Format: { file: '01-Genese.md', code: '01', fr: 'Genèse' }
  // BYM GitLab file numbering (Tanakh order, not Protestant)
  var OSHB_BOOK_MAP = {
    Gen:  { file: '01-Genese.md', code: '01', fr: 'Gn' },
    Exod: { file: '02-Exode.md', code: '02', fr: 'Ex' },
    Lev:  { file: '03-Levitique.md', code: '03', fr: 'Lv' },
    Num:  { file: '04-Nombres.md', code: '04', fr: 'Nb' },
    Deut: { file: '05-Deuteronome.md', code: '05', fr: 'Dt' },
    Josh: { file: '06-Josue.md', code: '06', fr: 'Jos' },
    Judg: { file: '07-Juges.md', code: '07', fr: 'Jg' },
    Ruth: { file: '31-Ruth.md', code: '31', fr: 'Rt' },
    '1Sam': { file: '08-1Samuel.md', code: '08', fr: '1Sa' },
    '2Sam': { file: '09-2Samuel.md', code: '09', fr: '2Sa' },
    '1Kgs': { file: '10-1Rois.md', code: '10', fr: '1R' },
    '2Kgs': { file: '11-2Rois.md', code: '11', fr: '2R' },
    '1Chr': { file: '38-1Chroniques.md', code: '38', fr: '1Ch' },
    '2Chr': { file: '39-2Chroniques.md', code: '39', fr: '2Ch' },
    Ezra: { file: '36-Esdras.md', code: '36', fr: 'Esd' },
    Neh:  { file: '37-Nehemie.md', code: '37', fr: 'N\u00e9' },
    Esth: { file: '34-Esther.md', code: '34', fr: 'Est' },
    Job:  { file: '29-Job.md', code: '29', fr: 'Jb' },
    Ps:   { file: '27-Psaumes.md', code: '27', fr: 'Ps' },
    Prov: { file: '28-Proverbes.md', code: '28', fr: 'Pr' },
    Eccl: { file: '33-Ecclesiaste.md', code: '33', fr: 'Ec' },
    Song: { file: '30-Cantiques.md', code: '30', fr: 'Ct' },
    Isa:  { file: '12-Esaie.md', code: '12', fr: 'Es' },
    Jer:  { file: '13-Jeremie.md', code: '13', fr: 'Jr' },
    Lam:  { file: '32-Lamentations.md', code: '32', fr: 'Lm' },
    Ezek: { file: '14-Ezechiel.md', code: '14', fr: 'Ez' },
    Dan:  { file: '35-Daniel.md', code: '35', fr: 'Dn' },
    Hos:  { file: '15-Osee.md', code: '15', fr: 'Os' },
    Joel: { file: '16-Joel.md', code: '16', fr: 'Jl' },
    Amos: { file: '17-Amos.md', code: '17', fr: 'Am' },
    Obad: { file: '18-Abdias.md', code: '18', fr: 'Ab' },
    Jonah:{ file: '19-Jonas.md', code: '19', fr: 'Jon' },
    Mic:  { file: '20-Michee.md', code: '20', fr: 'Mi' },
    Nah:  { file: '21-Nahum.md', code: '21', fr: 'Na' },
    Hab:  { file: '22-Habakuk.md', code: '22', fr: 'Ha' },
    Zeph: { file: '23-Sophonie.md', code: '23', fr: 'So' },
    Hag:  { file: '24-Aggee.md', code: '24', fr: 'Ag' },
    Zech: { file: '25-Zacharie.md', code: '25', fr: 'Za' },
    Mal:  { file: '26-Malachie.md', code: '26', fr: 'Ml' }
  };

  // French book names (full) for accordion headers
  var OSHB_BOOK_FR_FULL = {
    Gen:'Gen\u00e8se',Exod:'Exode',Lev:'L\u00e9vitique',Num:'Nombres',Deut:'Deut\u00e9ronome',
    Josh:'Josu\u00e9',Judg:'Juges',Ruth:'Ruth','1Sam':'1 Samuel','2Sam':'2 Samuel',
    '1Kgs':'1 Rois','2Kgs':'2 Rois','1Chr':'1 Chroniques','2Chr':'2 Chroniques',
    Ezra:'Esdras',Neh:'N\u00e9h\u00e9mie',Esth:'Esther',Job:'Job',Ps:'Psaumes',
    Prov:'Proverbes',Eccl:'Eccl\u00e9siaste',Song:'Cantique',Isa:'\u00c9sa\u00efe',
    Jer:'J\u00e9r\u00e9mie',Lam:'Lamentations',Ezek:'\u00c9z\u00e9chiel',Dan:'Daniel',
    Hos:'Os\u00e9e',Joel:'Jo\u00ebl',Amos:'Amos',Obad:'Abdias',Jonah:'Jonas',
    Mic:'Mich\u00e9e',Nah:'Nahoum',Hab:'Habaquq',Zeph:'Sophonie',Hag:'Agg\u00e9e',
    Zech:'Zacharie',Mal:'Malachie'
  };

  function oshbRefToBadge(ref, shortLabel) {
    // ref format: "Gen.1.1" → badge HTML
    var parts = ref.split('.');
    if (parts.length < 3) return '';
    var bookKey = parts[0];
    var chapter = parts[1];
    var verse = parts[2];
    var info = OSHB_BOOK_MAP[bookKey];
    if (!info) return '';
    // shortLabel: only "ch:v" inside accordion, full label otherwise
    var label = shortLabel ? (chapter + ':' + verse) : (info.fr + ' ' + chapter + ':' + verse);
    return '<span class="fb-ref-badge fb-conc-ref"'
      + ' data-file="' + escapeHtml(info.file) + '"'
      + ' data-code="' + escapeHtml(info.code) + '"'
      + ' data-chapter="' + chapter + '"'
      + ' data-verse="' + verse + '"'
      + '>' + escapeHtml(label) + '</span>';
  }

  function groupRefsByBook(refs) {
    var groups = [];
    var groupMap = {};
    for (var i = 0; i < refs.length; i++) {
      var bookKey = refs[i].split('.')[0];
      if (!groupMap[bookKey]) {
        groupMap[bookKey] = { key: bookKey, refs: [] };
        groups.push(groupMap[bookKey]);
      }
      groupMap[bookKey].refs.push(refs[i]);
    }
    return groups;
  }

  function buildConcordanceHtml(strongId, refs) {
    if (!refs || refs.length === 0) return '';
    var total = refs.length;
    var groups = groupRefsByBook(refs);

    var html = '<div class="fb-hebrew-card__conc">'
      + '<div class="fb-hebrew-card__conc-head">'
      + '<span class="fb-hebrew-card__conc-count">' + total + ' occurrence' + (total > 1 ? 's' : '') + ' dans le Tanakh</span>'
      + '</div>'
      + '<div class="fb-hebrew-card__conc-books">';

    // Show book summary line (clickable pills)
    html += '<div class="fb-conc-summary">';
    for (var g = 0; g < groups.length; g++) {
      var grp = groups[g];
      var bookName = OSHB_BOOK_FR_FULL[grp.key] || grp.key;
      html += '<button class="fb-conc-book-pill" type="button" data-conc-book="' + g + '">'
        + escapeHtml(bookName) + '&nbsp;<span class="fb-conc-book-pill__count">' + grp.refs.length + '</span>'
        + '</button>';
    }
    html += '</div>';

    // Accordion panels (all hidden by default)
    for (var g = 0; g < groups.length; g++) {
      var grp = groups[g];
      html += '<div class="fb-conc-panel" data-conc-panel="' + g + '" hidden>';
      html += '<div class="fb-conc-panel__refs">';
      for (var r = 0; r < grp.refs.length; r++) {
        html += oshbRefToBadge(grp.refs[r], true);
      }
      html += '</div></div>';
    }

    html += '</div></div>';
    return html;
  }

  // ── 1. PATCHES EXISTANTS ──────────────────────────────────────────

  /* ── 1a. Images Optimole ── */
  function fixOptimoleImages() {
    var imgs = document.querySelectorAll('.figuier-bible-app img');
    for (var i = 0; i < imgs.length; i++) {
      var img = imgs[i];
      if (!img.complete || img.naturalWidth === 0) {
        var src = img.getAttribute('src') || '';
        if (src.indexOf('optimole.com') !== -1) {
          var parts = src.split('/http');
          if (parts.length > 1) {
            img.loading = 'eager';
            img.src = 'http' + parts[parts.length - 1];
          }
        }
      }
    }
  }

  /* ── 1b. Mobile layout fix ── */
  function applyMobileLayout() {
    if (!document.body.classList.contains('page-id-1978')) return;
    document.documentElement.style.overflowX = 'hidden';
    document.body.style.overflowX = 'hidden';
    var site = document.querySelector('.site');
    if (site) site.style.overflowX = 'hidden';
    var isMobile = window.innerWidth < 600;
    var isTablet = window.innerWidth >= 600 && window.innerWidth < 900;
    var cc = document.querySelector('.content-container');
    var cw = document.querySelector('.content-wrap');
    var ecw = document.querySelector('.entry-content-wrap');
    var sc = document.querySelector('.site-container');
    var app = document.querySelector('.figuier-bible-app');
    if (isMobile) {
      if (cc) { cc.style.paddingLeft = '0'; cc.style.paddingRight = '0'; cc.style.maxWidth = '100vw'; }
      if (cw) { cw.style.paddingLeft = '0'; cw.style.paddingRight = '0'; cw.style.maxWidth = '100vw'; }
      if (ecw) { ecw.style.paddingLeft = '0'; ecw.style.paddingRight = '0'; }
      if (sc) { sc.style.paddingLeft = '0'; sc.style.paddingRight = '0'; sc.style.maxWidth = '100vw'; }
      if (app) { app.style.paddingLeft = '10px'; app.style.paddingRight = '10px'; app.style.maxWidth = '100vw'; app.style.boxSizing = 'border-box'; }
    } else if (isTablet) {
      if (cc) { cc.style.paddingLeft = '8px'; cc.style.paddingRight = '8px'; }
      if (cw) { cw.style.paddingLeft = '0'; cw.style.paddingRight = '0'; }
    }
  }

  function injectMobileFix() {
    if (document.getElementById('v3-mobile-fix')) return;
    var s = document.createElement('style');
    s.id = 'v3-mobile-fix';
    s.textContent =
      'html, body.page-id-1978, body.page-id-1978 .site { overflow-x: hidden !important; }\n' +
      '@media (max-width: 599px) {\n' +
      '  body.page-id-1978 .figuier-bible-app * { max-width: 100% !important; box-sizing: border-box !important; }\n' +
      '  body.page-id-1978 .fb-home-hero__grid { grid-template-columns: 1fr !important; }\n' +
      '  body.page-id-1978 .fb-home-hero__aside { display: block !important; padding: 0 !important; }\n' +
      '  body.page-id-1978 .fb-home-hero__actions { display: flex !important; flex-direction: row !important; flex-wrap: wrap !important; gap: 8px; margin-top: 12px; }\n' +
      '  body.page-id-1978 .fb-home-media { max-height: 200px !important; overflow: hidden !important; border-radius: 12px !important; }\n' +
      '  body.page-id-1978 .fb-home-media img { width: 100% !important; height: auto !important; }\n' +
      '  body.page-id-1978 .fb-browse-grid { grid-template-columns: 1fr !important; }\n' +
      '  body.page-id-1978 .fb-home-stats { flex-direction: column !important; }\n' +
      '}';
    document.head.appendChild(s);
    applyMobileLayout();
    fixOptimoleImages();
    window.addEventListener('resize', applyMobileLayout);
    var appEl = document.querySelector('.figuier-bible-app');
    if (appEl) {
      new MutationObserver(function () { fixOptimoleImages(); })
        .observe(appEl, { childList: true, subtree: true });
    }
  }
  injectMobileFix();

  /* ── 1c. Topbar scroll shadow ── */
  function initTopbarScroll() {
    var topbar = document.querySelector(TOPBAR_SEL);
    if (!topbar) return;
    var app = document.querySelector(APP_SEL);
    if (app) {
      var h = topbar.offsetHeight;
      if (h > 0) app.style.setProperty('--fb-topbar-height', h + 'px');
    }
    var scrolled = false;
    function onScroll() {
      var y = window.scrollY || window.pageYOffset;
      if (y > 8 && !scrolled) { topbar.classList.add('is-scrolled'); scrolled = true; }
      else if (y <= 8 && scrolled) { topbar.classList.remove('is-scrolled'); scrolled = false; }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ── 1d. 2-panel concept layout ── */
  function restructureConceptLayout() {
    var conceptBody = document.querySelector(CONCEPT_BODY_SEL);
    if (!conceptBody || conceptBody.querySelector('.' + LAYOUT_CLASS)) return;
    var mainStack = conceptBody.querySelector('.fb-main-stack');
    if (!mainStack) return;

    var layout = document.createElement('div');
    layout.className = LAYOUT_CLASS;
    var sidebar = document.createElement('aside');
    sidebar.className = SIDEBAR_CLASS;
    sidebar.setAttribute('role', 'complementary');
    sidebar.setAttribute('aria-label', 'Langues originales');

    // Move legacy boxes into sidebar if they exist
    var relatedBox = mainStack.querySelector('.fb-related-box');
    var sourcesBox = mainStack.querySelector('.fb-sources-box');
    if (relatedBox) sidebar.appendChild(relatedBox);
    if (sourcesBox) sidebar.appendChild(sourcesBox);

    conceptBody.removeChild(mainStack);
    layout.appendChild(mainStack);
    layout.appendChild(sidebar);
    conceptBody.appendChild(layout);
  }

  /* ── 1d-bis. Source Journey Indicator (ux-proposal-concept-page.jsx) ── */

  // Map source → display role + label for the journey indicator
  var SOURCE_ROLE_MAP = {
    'bym_lexicon': { role: 'quick_gloss', label: 'Lexique' },
    'easton':      { role: 'main_definition', label: 'Définition' },
    'smith':       { role: 'detailed_reference', label: 'Référence' },
    'isbe':        { role: 'deep_read', label: 'Encyclopédie' },
    'hebrew':      { role: 'hebrew_lexicon', label: 'Hébreu' },
    'related':     { role: 'related', label: 'Liés' }
  };

  // Gradient line colors per role pair
  var ROLE_DOT_COLORS = {
    'quick_gloss': '#d4a95a',
    'main_definition': '#7e5d43',
    'detailed_reference': '#5a7a55',
    'deep_read': '#6b5b8a',
    'hebrew_lexicon': '#c17a3a',
    'related': '#83776c'
  };

  function getTocRoleInfo(sourceKey, fullLabel) {
    if (sourceKey && SOURCE_ROLE_MAP[sourceKey]) {
      return SOURCE_ROLE_MAP[sourceKey];
    }
    var normalized = (fullLabel || '').toLowerCase();
    if (normalized.indexOf('bym') !== -1) return SOURCE_ROLE_MAP['bym_lexicon'];
    if (normalized.indexOf('easton') !== -1) return SOURCE_ROLE_MAP['easton'];
    if (normalized.indexOf('smith') !== -1) return SOURCE_ROLE_MAP['smith'];
    if (normalized.indexOf('isbe') !== -1 || normalized.indexOf('encyclop') !== -1) return SOURCE_ROLE_MAP['isbe'];
    if (normalized.indexOf('hébreu') !== -1 || normalized.indexOf('hebreu') !== -1) return SOURCE_ROLE_MAP['hebrew'];
    if (normalized.indexOf('lié') !== -1) return SOURCE_ROLE_MAP['related'];
    return { role: 'main_definition', label: fullLabel || 'Section' };
  }

  /** Installe un IntersectionObserver qui marque la chip .is-active
   *  en fonction de la section actuellement la plus haute visible. */
  function setupTocIntersectionObserver(nav, sections) {
    if (!window.IntersectionObserver) return null;

    // Track which sections are currently visible
    var visibleSet = Object.create(null);

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          visibleSet[entry.target.id] = true;
        } else {
          delete visibleSet[entry.target.id];
        }
      });

      // L'active link = la section la plus haute (dans l'ordre du document)
      // parmi celles actuellement visibles
      var activeId = null;
      for (var i = 0; i < sections.length; i++) {
        if (visibleSet[sections[i].id]) {
          activeId = sections[i].id;
          break;
        }
      }

      nav.querySelectorAll('.fb-mobile-toc__link').forEach(function (link) {
        var isActive = link.getAttribute('data-toc-id') === activeId;
        link.classList.toggle('is-active', isActive);
      });
    }, {
      // -100px en haut = décalage pour le sticky header + TOC
      // -60% en bas = on considère "active" une section uniquement
      // quand elle est dans la moitié supérieure du viewport
      rootMargin: '-100px 0px -60% 0px',
      threshold: 0
    });

    sections.forEach(function (s) {
      var el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });

    return observer;
  }

  function buildMobileTOC() {
    var conceptBody = document.querySelector(CONCEPT_BODY_SEL);
    if (!conceptBody) return;
    var existing = conceptBody.querySelector('.fb-mobile-toc');
    // Desktop: remove any previously-injected mobile TOC (e.g. on resize)
    if (window.innerWidth >= 900) {
      if (existing) {
        if (existing._tocObserver) {
          try { existing._tocObserver.disconnect(); } catch (_) {}
        }
        existing.parentNode.removeChild(existing);
      }
      return;
    }

    var sections = [];

    // Collect source sections
    conceptBody.querySelectorAll('.fb-source-section').forEach(function (sec) {
      var title = sec.querySelector('.fb-source-section__title, .fb-source-section__title-row .fb-source-section__title');
      var fullLabel = title ? title.textContent.trim() : '';
      var src = sec.getAttribute('data-source') || '';
      if (!sec.id) {
        sec.id = 'fb-sec-' + Math.random().toString(36).slice(2, 8);
      }
      var info = getTocRoleInfo(src, fullLabel);
      sections.push({
        id: sec.id,
        role: info.role,
        label: info.label,
        fullLabel: fullLabel || info.label,
        source: src
      });
    });

    // Hebrew lexicon section
    var hebSidebar = conceptBody.querySelector('.fb-hebrew-sidebar');
    if (hebSidebar) {
      if (!hebSidebar.id) hebSidebar.id = 'fb-sec-hebrew';
      sections.push({ id: hebSidebar.id, role: 'hebrew_lexicon', label: 'Hébreu', fullLabel: 'Lexique hébreu', source: 'hebrew' });
    }

    // Related concepts
    var related = document.querySelector('.fb-related-standalone');
    if (related) {
      if (!related.id) related.id = 'fb-sec-related';
      sections.push({ id: related.id, role: 'related', label: 'Liés', fullLabel: 'Concepts liés', source: 'related' });
    }

    if (sections.length < 2) return;

    // Avoid unnecessary rebuilds
    if (existing) {
      var existingIds = Array.prototype.map.call(
        existing.querySelectorAll('.fb-mobile-toc__link'),
        function (a) { return a.getAttribute('data-toc-id'); }
      ).join('|');
      var newIds = sections.map(function (s) { return s.id; }).join('|');
      if (existingIds === newIds) return;
      if (existing._tocObserver) {
        try { existing._tocObserver.disconnect(); } catch (_) {}
      }
      existing.parentNode.removeChild(existing);
    }

    var nav = document.createElement('nav');
    nav.className = 'fb-mobile-toc';
    nav.setAttribute('aria-label', 'Parcours des sources');

    // Build Source Journey HTML : dots + labels + connector lines
    var html = '<div class="fb-mobile-toc__list">';
    for (var i = 0; i < sections.length; i++) {
      var s = sections[i];
      var dotColor = ROLE_DOT_COLORS[s.role] || '#83776c';

      html += '<div class="fb-mobile-toc__step">';

      // The clickable pill (dot + label)
      html += '<a class="fb-mobile-toc__link" data-role="' + escapeHtml(s.role) + '"'
            + ' href="#' + s.id + '"'
            + ' data-toc-id="' + s.id + '"'
            + ' title="' + escapeHtml(s.fullLabel) + '"'
            + ' aria-label="' + escapeHtml(s.fullLabel) + '">'
            + '<span class="fb-mobile-toc__dot" style="background:' + dotColor + '"></span>'
            + '<span class="fb-mobile-toc__text">' + escapeHtml(s.label) + '</span>'
            + '</a>';

      // Connector line (gradient between this dot color and the next)
      if (i < sections.length - 1) {
        var nextColor = ROLE_DOT_COLORS[sections[i + 1].role] || '#83776c';
        html += '<div class="fb-mobile-toc__line" style="background:linear-gradient(90deg,' + dotColor + '40,' + nextColor + '40)"></div>';
      }

      html += '</div>';
    }
    html += '</div>';
    nav.innerHTML = html;

    // Insert at the very top of the concept-body (before the layout)
    conceptBody.insertBefore(nav, conceptBody.firstChild);

    // Smooth scroll on click, prevent default hash change
    nav.querySelectorAll('.fb-mobile-toc__link').forEach(function (link) {
      link.addEventListener('click', function (e) {
        e.preventDefault();
        var id = link.getAttribute('data-toc-id');
        var target = document.getElementById(id);
        if (!target) return;
        var topbar = document.querySelector(TOPBAR_SEL);
        var tocHeight = nav.offsetHeight || 0;
        var offset = (topbar ? topbar.offsetHeight : 0) + tocHeight + 12;
        var y = target.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({ top: y, behavior: 'smooth' });
      });
    });

    // Active-section tracking via IntersectionObserver
    nav._tocObserver = setupTocIntersectionObserver(nav, sections);
  }

  /* ── 1e. Breadcrumb ── */
  function injectBreadcrumb() {
    var hero = document.querySelector(CONCEPT_HERO_SEL);
    if (!hero || hero.querySelector('.' + BREADCRUMB_CLASS)) return;
    var breadcrumb = document.createElement('nav');
    breadcrumb.className = BREADCRUMB_CLASS;
    breadcrumb.setAttribute('aria-label', 'Fil d\u0027ariane');
    breadcrumb.innerHTML =
      '<a href="#" data-action="go-home" aria-label="Accueil dictionnaire">Dictionnaire</a>' +
      ' <span aria-hidden="true">\u203a</span> ';
    var titleEl = hero.querySelector('.fb-concept-title');
    var span = document.createElement('span');
    span.setAttribute('aria-current', 'page');
    span.textContent = titleEl ? titleEl.textContent.trim() : '';
    breadcrumb.appendChild(span);
    hero.insertBefore(breadcrumb, hero.firstChild);
  }

  /* ── 1f. Reading panel shell ── */
  function enhanceReadingPanel() {
    var panel = document.querySelector(READING_PANEL_SEL);
    if (!panel || panel.hidden || panel.querySelector('.fb-reading-shell')) return;
    var children = Array.prototype.slice.call(panel.childNodes);
    if (children.length === 0) return;

    var shell = document.createElement('div');
    shell.className = 'fb-reading-shell';
    var head = document.createElement('div');
    head.className = 'fb-reading-head';
    var headCopy = document.createElement('div');
    headCopy.className = 'fb-reading-head-copy';
    var existingTitle = panel.querySelector('.fb-reading-title, .fb-panel-title, h2');
    if (existingTitle) {
      var title = document.createElement('h2');
      title.className = 'fb-reading-title';
      title.textContent = existingTitle.textContent;
      headCopy.appendChild(title);
    }
    var existingClose = panel.querySelector('.fb-reading-close, [data-action="close-reading"]');
    head.appendChild(headCopy);
    if (existingClose) head.appendChild(existingClose.cloneNode(true));

    var body = document.createElement('div');
    body.className = 'fb-reading-body';
    children.forEach(function (child) {
      if (child !== existingTitle && child !== existingClose && child.parentNode === panel) {
        body.appendChild(child);
      }
    });
    if (existingTitle && existingTitle.parentNode === panel) panel.removeChild(existingTitle);
    shell.appendChild(head);
    shell.appendChild(body);
    panel.innerHTML = '';
    panel.appendChild(shell);
    panel.addEventListener('click', function (e) {
      if (e.target === panel) {
        var btn = panel.querySelector('[data-action="close-reading"]');
        if (btn) btn.click();
      }
    });
  }

  /* ── 1g. Keyboard shortcuts ── */
  function initKeyboard() {
    document.addEventListener('keydown', function (e) {
      var tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
      if (e.target.isContentEditable) return;
      if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        var inp = document.querySelector(SEARCH_INPUT_SEL);
        if (inp) { e.preventDefault(); inp.focus(); inp.select(); }
      }
      if (e.key === 'Escape') {
        closeVerseBubble();
        var rp = document.querySelector(READING_PANEL_SEL);
        if (rp && !rp.hidden) {
          var btn = rp.querySelector('[data-action="close-reading"]');
          if (btn) { e.preventDefault(); btn.click(); }
        }
      }
    });
  }

  /* ── 1h. Breadcrumb nav delegation ── */
  function initBreadcrumbNav() {
    document.addEventListener('click', function (e) {
      var link = e.target.closest('[data-action="go-home"]');
      if (link) { e.preventDefault(); window.location.hash = ''; }
    });
  }

  // ── 2. MODULE VERSE BUBBLE ────────────────────────────────────────

  var BYM_SOURCE_BASE = config.bymSourceBase || '';
  var BYM_READER_BASE = config.bymReaderBase || '';
  var BYM_PROXY_URL = config.bymProxyUrl || '';
  var bookCache = new Map();

  // BYM reader URL codes — maps BYM file number to reader abbreviation
  var BYM_URL_CODES = {
    '01':'GN','02':'EX','03':'LV','04':'NB','05':'DT','06':'JS','07':'JG',
    '08':'1S','09':'2S','10':'1R','11':'2R','12':'IS','13':'JR','14':'EZ',
    '15':'OS','16':'JL','17':'AM','18':'AB','19':'JO','20':'MI','21':'NA',
    '22':'HA','23':'SO','24':'AG','25':'ZA','26':'ML','27':'PS','28':'PR',
    '29':'JB','30':'CT','31':'RT','32':'LM','33':'EC','34':'ET','35':'DN',
    '36':'ES','37':'NE','38':'1CH','39':'2CH',
    '40':'MT','41':'MC','42':'LC','43':'JN','44':'AC','45':'RM','46':'1CO','47':'2CO',
    '48':'GA','49':'EP','50':'PH','51':'CO','52':'1TH','53':'2TH','54':'1TM','55':'2TM',
    '56':'TT','57':'PM','58':'HE','59':'JC','60':'1P','61':'2P','62':'1JN','63':'2JN',
    '64':'3JN','65':'JD','66':'AP'
  };

  // Book data: [num, file_suffix, ...abbreviations (FR + EN)]
  var BOOKS = [
    [1,'Genese','Genèse','Genesis','Gen','Gn'],
    [2,'Exode','Exode','Exodus','Ex'],
    [3,'Levitique','Lévitique','Leviticus','Lev','Lv'],
    [4,'Nombres','Nombres','Numbers','Num','Nb'],
    [5,'Deuteronome','Deutéronome','Deuteronomy','Deut','Dt'],
    [6,'Josue','Josué','Joshua','Jos'],
    [7,'Juges','Juges','Judges','Jug','Jg'],
    [8,'Ruth','Ruth','Ru','Rt'],
    [9,'1Samuel','1 Samuel','1Sam','1Sa'],
    [10,'2Samuel','2 Samuel','2Sam','2Sa'],
    [11,'1Rois','1 Rois','1Kings','1Ki','1R'],
    [12,'2Rois','2 Rois','2Kings','2Ki','2R'],
    [13,'1Chroniques','1 Chroniques','1Chronicles','1Chr','1Ch'],
    [14,'2Chroniques','2 Chroniques','2Chronicles','2Chr','2Ch'],
    [15,'Esdras','Esdras','Ezra','Esd'],
    [16,'Nehemie','Néhémie','Nehemiah','Neh'],
    [17,'Esther','Esther','Est'],
    [18,'Job','Job','Jb'],
    [19,'Psaumes','Psaumes','Psalms','Psalm','Ps'],
    [20,'Proverbes','Proverbes','Proverbs','Prov','Pr'],
    [21,'Ecclesiaste','Ecclésiaste','Ecclesiastes','Eccl','Ec','Qo'],
    [22,'Cantique','Cantique des Cantiques','Song of Solomon','Cant','Ct'],
    [23,'Esaie','Ésaïe','Isaïe','Isaiah','Isa','Is','Es'],
    [24,'Jeremie','Jérémie','Jeremiah','Jer','Jr'],
    [25,'Lamentations','Lamentations','Lam','Lm'],
    [26,'Ezechiel','Ézéchiel','Ezekiel','Ezek','Ez'],
    [27,'Daniel','Daniel','Dan','Dn'],
    [28,'Osee','Osée','Hosea','Hos','Os'],
    [29,'Joel','Joël','Joel','Jl'],
    [30,'Amos','Amos','Am'],
    [31,'Abdias','Abdias','Obadiah','Obad','Ab'],
    [32,'Jonas','Jonas','Jonah','Jon'],
    [33,'Michee','Michée','Micah','Mic','Mi'],
    [34,'Nahoum','Nahoum','Nahum','Nah','Na'],
    [35,'Habaquq','Habaquq','Habakkuk','Hab'],
    [36,'Sophonie','Sophonie','Zephaniah','Zeph','So'],
    [37,'Aggee','Aggée','Haggai','Hag','Ag'],
    [38,'Zacharie','Zacharie','Zechariah','Zech','Za'],
    [39,'Malachie','Malachie','Malachi','Mal','Ml'],
    [40,'Matthieu','Matthieu','Matthew','Matt','Mt'],
    [41,'Marc','Marc','Mark','Mc'],
    [42,'Luc','Luc','Luke','Lc'],
    [43,'Jean','Jean','John','Jn'],
    [44,'Actes','Actes','Acts','Ac'],
    [45,'Romains','Romains','Romans','Rom','Rm'],
    [46,'1Corinthiens','1 Corinthiens','1Corinthians','1Cor','1Co'],
    [47,'2Corinthiens','2 Corinthiens','2Corinthians','2Cor','2Co'],
    [48,'Galates','Galates','Galatians','Gal','Ga'],
    [49,'Ephesiens','Éphésiens','Ephesians','Eph','Ep'],
    [50,'Philippiens','Philippiens','Philippians','Phil','Ph'],
    [51,'Colossiens','Colossiens','Colossians','Col'],
    [52,'1Thessaloniciens','1 Thessaloniciens','1Thessalonians','1Th'],
    [53,'2Thessaloniciens','2 Thessaloniciens','2Thessalonians','2Th'],
    [54,'1Timothee','1 Timothée','1Timothy','1Tim','1Tm'],
    [55,'2Timothee','2 Timothée','2Timothy','2Tim','2Tm'],
    [56,'Tite','Tite','Titus','Tt'],
    [57,'Philemon','Philémon','Philemon','Phm'],
    [58,'Hebreux','Hébreux','Hebrews','Heb'],
    [59,'Jacques','Jacques','James','Jas','Jc'],
    [60,'1Pierre','1 Pierre','1Peter','1Pi','1P'],
    [61,'2Pierre','2 Pierre','2Peter','2Pi','2P'],
    [62,'1Jean','1 Jean','1John','1Jn'],
    [63,'2Jean','2 Jean','2John','2Jn'],
    [64,'3Jean','3 Jean','3John','3Jn'],
    [65,'Jude','Jude','Jd'],
    [66,'Apocalypse','Apocalypse','Revelation','Rev','Ap']
  ];

  var BOOK_MAP = {};
  BOOKS.forEach(function (b) {
    var num = ('0' + b[0]).slice(-2);
    var info = { file: num + '-' + b[1] + '.md', code: num, name: b[2] };
    for (var i = 2; i < b.length; i++) {
      var key = b[i].toLowerCase().replace(/\s+/g, '');
      BOOK_MAP[key] = info;
    }
  });

  // Regex: optional leading digit, book name (possibly with period), chapter:verse
  var REF_REGEX = /((?:[123]\s*)?[A-ZÀ-Ü][a-zà-ü]{1,20}\.?)\s+(\d{1,3})\s*[:.,]\s*(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?/g;

  function resolveBook(name) {
    var norm = name.toLowerCase().replace(/\.\s*$/, '').replace(/\s+/g, '').trim();
    return BOOK_MAP[norm] || null;
  }

  function cleanVerse(raw) {
    return raw
      .replace(/<!--[\s\S]*?-->/g, '')
      .replace(/<[^>]+>/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function parseBookText(text) {
    var verses = new Map();
    text.split('\n').forEach(function (line) {
      var idx = line.indexOf('\t');
      if (idx > 0) verses.set(line.slice(0, idx).trim(), cleanVerse(line.slice(idx + 1)));
    });
    return verses;
  }

  function fetchBook(file) {
    if (bookCache.has(file)) return Promise.resolve(bookCache.get(file));
    if (!BYM_PROXY_URL && !BYM_SOURCE_BASE) return Promise.reject('no_base');

    // Use WP proxy to avoid CORS; fallback to direct GitLab
    var proxyUrl = BYM_PROXY_URL
      ? BYM_PROXY_URL + '?action=figuier_bym_proxy&file=' + encodeURIComponent(file)
      : '';
    var directUrl = BYM_SOURCE_BASE ? BYM_SOURCE_BASE + '/' + file : '';

    var fetchUrl = proxyUrl || directUrl;
    return fetch(fetchUrl).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.text();
    }).then(function (text) {
      var verses = parseBookText(text);
      bookCache.set(file, verses);
      return verses;
    }).catch(function (err) {
      // Fallback to direct GitLab if proxy failed
      if (proxyUrl && directUrl) {
        return fetch(directUrl).then(function (r) {
          if (!r.ok) throw new Error(r.status);
          return r.text();
        }).then(function (text) {
          var verses = parseBookText(text);
          bookCache.set(file, verses);
          return verses;
        });
      }
      throw err;
    });
  }

  function showVerseBubble(ref, anchorRect) {
    closeVerseBubble();
    var isMobile = window.innerWidth < (config.mobileBreakpoint || 900);

    var bubble = document.createElement('div');
    bubble.className = 'fb-verse-bubble' + (isMobile ? ' fb-verse-bubble--sheet' : '');
    bubble.setAttribute('role', 'dialog');
    bubble.setAttribute('aria-label', ref.text);

    var urlCode = BYM_URL_CODES[ref.code] || ref.code;
    var readerHref = BYM_READER_BASE
      ? BYM_READER_BASE + '?w1=bible&t1=local%3ABYM&v1=' + urlCode + ref.chapter + '_' + ref.verse
      : '';

    bubble.innerHTML =
      '<div class="fb-verse-bubble__header">' +
        '<span class="fb-verse-bubble__ref">' + escapeHtml(ref.text) + '</span>' +
        '<button class="fb-verse-bubble__close" type="button" aria-label="Fermer">&times;</button>' +
      '</div>' +
      '<div class="fb-verse-bubble__body">' +
        '<div class="fb-verse-bubble__loading">Chargement\u2026</div>' +
      '</div>' +
      (readerHref
        ? '<div class="fb-verse-bubble__footer">' +
            '<a href="' + escapeHtml(readerHref) + '" target="_blank" rel="noopener">Lire dans la BYM \u2192</a>' +
          '</div>'
        : '');

    if (isMobile) {
      var overlay = document.createElement('div');
      overlay.className = 'fb-verse-bubble__overlay';
      overlay.addEventListener('click', closeVerseBubble);
      document.body.appendChild(overlay);
    } else {
      var adminBar = document.getElementById('wpadminbar');
      var barH = adminBar ? adminBar.offsetHeight : 0;
      var left = Math.max(8, Math.min(anchorRect.left, window.innerWidth - 430));
      var spaceBelow = window.innerHeight - anchorRect.bottom;
      var top;
      if (spaceBelow > 280) {
        top = anchorRect.bottom + 8;
      } else {
        top = Math.max(barH + 8, anchorRect.top - 300);
      }
      // Clamp within viewport
      top = Math.max(barH + 8, Math.min(top, window.innerHeight - 200));
      bubble.style.left = left + 'px';
      bubble.style.top = top + 'px';
    }
    document.body.appendChild(bubble);

    // Fetch verses
    fetchBook(ref.file).then(function (verses) {
      var html = '';
      var vStart = ref.verse;
      var vEnd = ref.verseEnd || ref.verse;
      for (var v = Math.max(1, vStart - 2); v <= vEnd + 2; v++) {
        var key = ref.chapter + ':' + v;
        var text = verses.get(key);
        if (!text) continue;
        var isTarget = v >= vStart && v <= vEnd;
        html += '<div class="fb-verse-bubble__verse' + (isTarget ? ' is-target' : '') + '">' +
          '<span class="fb-verse-bubble__vnum">' + v + '</span> ' +
          escapeHtml(text) + '</div>';
      }
      if (!html) html = '<p class="fb-verse-bubble__empty">Verset non disponible dans la source BYM</p>';
      var body = bubble.querySelector('.fb-verse-bubble__body');
      if (body) body.innerHTML = html;
    }).catch(function () {
      var body = bubble.querySelector('.fb-verse-bubble__body');
      if (body) body.innerHTML = '<p class="fb-verse-bubble__empty">Source indisponible</p>';
    });

    bubble.querySelector('.fb-verse-bubble__close').addEventListener('click', closeVerseBubble);
  }

  function closeVerseBubble() {
    var existing = document.querySelector('.fb-verse-bubble');
    if (existing) existing.remove();
    var overlay = document.querySelector('.fb-verse-bubble__overlay');
    if (overlay) overlay.remove();
  }

  function wrapBiblicalReferences(container) {
    if (!container || container.getAttribute('data-refs-wrapped')) return;
    container.setAttribute('data-refs-wrapped', '1');

    var walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
    var textNodes = [];
    var node;
    while ((node = walker.nextNode())) {
      if (node.parentNode.closest && node.parentNode.closest('.fb-ref-badge,.fb-verse-bubble')) continue;
      textNodes.push(node);
    }

    textNodes.forEach(function (textNode) {
      var text = textNode.textContent;
      REF_REGEX.lastIndex = 0;
      if (!REF_REGEX.test(text)) return;

      var frag = document.createDocumentFragment();
      var lastIdx = 0;
      REF_REGEX.lastIndex = 0;
      var m;
      while ((m = REF_REGEX.exec(text)) !== null) {
        var info = resolveBook(m[1]);
        if (!info) continue;
        if (m.index > lastIdx) frag.appendChild(document.createTextNode(text.slice(lastIdx, m.index)));
        var badge = document.createElement('span');
        badge.className = 'fb-ref-badge';
        badge.textContent = m[0];
        badge.setAttribute('data-file', info.file);
        badge.setAttribute('data-code', info.code);
        badge.setAttribute('data-chapter', m[2]);
        badge.setAttribute('data-verse', m[3]);
        if (m[4]) badge.setAttribute('data-verse-end', m[4]);
        frag.appendChild(badge);
        lastIdx = REF_REGEX.lastIndex;
      }
      if (lastIdx === 0) return;
      if (lastIdx < text.length) frag.appendChild(document.createTextNode(text.slice(lastIdx)));
      textNode.parentNode.replaceChild(frag, textNode);
    });
  }

  function initVerseBubbleClicks() {
    document.addEventListener('click', function (e) {
      var badge = e.target.closest('.fb-ref-badge');
      if (badge) {
        e.preventDefault();
        showVerseBubble({
          file: badge.getAttribute('data-file'),
          code: badge.getAttribute('data-code'),
          chapter: parseInt(badge.getAttribute('data-chapter'), 10),
          verse: parseInt(badge.getAttribute('data-verse'), 10),
          verseEnd: badge.getAttribute('data-verse-end') ? parseInt(badge.getAttribute('data-verse-end'), 10) : null,
          text: badge.textContent
        }, badge.getBoundingClientRect());
        return;
      }
      if (!e.target.closest('.fb-verse-bubble')) closeVerseBubble();
    });
  }

  // ── 3. MODULE HEBREW LEXICON ──────────────────────────────────────

  var lexiconData = null;
  var lexiconIndex = null; // Map<strongNum, entry>

  function loadLexicon() {
    if (lexiconData) return Promise.resolve(lexiconIndex);
    var url = config.hebrewLexiconUrl;
    if (!url) return Promise.reject('no_url');
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (data) {
      lexiconData = Array.isArray(data) ? data : (data.value || []);
      lexiconIndex = new Map();
      lexiconData.forEach(function (entry) {
        if (entry.s) lexiconIndex.set(entry.s.toUpperCase(), entry);
      });
      return lexiconIndex;
    });
  }

  var STRONG_REGEX = /\b([HG]\d{1,5})\b/g;

  function detectStrongNumbers(html) {
    var found = new Set();
    var m;
    STRONG_REGEX.lastIndex = 0;
    while ((m = STRONG_REGEX.exec(html)) !== null) {
      found.add(m[1].toUpperCase());
    }
    return found;
  }

  function buildRootFamilyHtml(strongId, rootData) {
    if (!rootData || !rootData.r || !rootData.f || rootData.f.length === 0) return '';
    var root = rootData.r;
    var siblings = rootData.f;
    var html = '<div class="fb-hebrew-card__root">'
      + '<div class="fb-hebrew-card__root-head">'
      + '<span class="fb-hebrew-card__root-label">Racine</span>'
      + '<span class="fb-hebrew-card__root-hebrew" dir="rtl">' + escapeHtml(root) + '</span>'
      + '<span class="fb-hebrew-card__root-count">' + (siblings.length + 1) + ' mots</span>'
      + '</div>'
      + '<div class="fb-root-family">';
    for (var i = 0; i < siblings.length; i++) {
      var sib = siblings[i];
      var glossTxt = sib.g ? escapeHtml(truncate(sib.g, 30)) : '';
      html += '<span class="fb-root-sibling" data-strong="' + escapeHtml(sib.s) + '">'
        + '<span class="fb-root-sibling__hebrew" dir="rtl">' + escapeHtml(sib.h) + '</span>'
        + '<span class="fb-root-sibling__info">'
        + '<span class="fb-root-sibling__strong">' + escapeHtml(sib.s) + '</span>'
        + (glossTxt ? ' <span class="fb-root-sibling__gloss">' + glossTxt + '</span>' : '')
        + '</span>'
        + '</span>';
    }
    html += '</div></div>';
    return html;
  }

  // === HELPERS LEXIQUE HEBREU BIBLIQUE (tiers T1-T7) ===

  // OSIS -> BYM book info {file, code} (code numerique 2 chiffres, ordre BYM)
  var OSIS_TO_BYM_BOOK_T6 = {
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
  function parseBymRef(osisRef) {
    if (!osisRef || typeof osisRef !== 'string') return null;
    var parts = osisRef.split('-');
    var m1 = /^(\w+)\.(\d+)\.(\d+)$/.exec(parts[0]);
    if (!m1) return null;
    var book = OSIS_TO_BYM_BOOK_T6[m1[1]];
    if (!book) return null;
    var out = {
      file: book.code + '-' + book.file + '.md', code: book.code,
      chapter: parseInt(m1[2], 10), verse: parseInt(m1[3], 10), verseEnd: null
    };
    if (parts.length > 1) {
      var m2 = /^(\w+)\.(\d+)\.(\d+)$/.exec(parts[1]);
      if (m2 && m2[1] === m1[1] && m2[2] === m1[2]) {
        out.verseEnd = parseInt(m2[3], 10);
      }
    }
    return out;
  }

  // OSIS -> Ostervald book abbreviations
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

  function osterwaldRef(osisRef) {
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

  // Wrap Hebrew runs with dir="rtl" span pour isoler bidi dans texte FR mixte
  function wrapHebrewInline(escapedText) {
    return escapedText.replace(/[\u0590-\u05FF]+(?:\s+[\u0590-\u05FF]+)*/g, function (m) {
      return '<span class="fb-inline-he" dir="rtl">' + m + '</span>';
    });
  }
  function escapeHtmlHe(text) {
    return wrapHebrewInline(escapeHtml(text));
  }
  function strongLinkify(text) {
    var html = wrapHebrewInline(escapeHtml(text));
    return html.replace(/\b(\d{1,4})\b/g, function (match, num) {
      return '<a class="fb-hebrew-card__strong-link" href="#H' + num + '" data-strong="H' + num + '">' + num + '</a>';
    });
  }

  function stemTooltip(stem) {
    var tips = {
      'Qal':   'Qal : forme verbale simple, active, basique',
      'Niph':  'Niphal : forme verbale passive ou r\u00e9fl\u00e9chie',
      'Pi':    'Piel : intensif actif',
      'Pu':    'Pual : intensif passif',
      'Hiph':  'Hiphil : causatif actif',
      'Hoph':  'Hophal : causatif passif',
      'Hithp': 'Hithpael : r\u00e9fl\u00e9chi',
      'Hithpo':'Hithpolel : r\u00e9fl\u00e9chi intensif'
    };
    return tips[stem] || '';
  }

  function renderSenseItem(s) {
    var nAttr = s.n ? ' data-n="' + escapeHtml(s.n) + '"' : '';
    var def = escapeHtmlHe(s.d || '');
    var subHtml = '';
    if (Array.isArray(s.c) && s.c.length > 0) {
      subHtml = '<ol class="fb-hebrew-card__sense-sublist">' +
        s.c.map(renderSenseItem).join('') + '</ol>';
    }
    return '<li' + nAttr + '>' + def + subHtml + '</li>';
  }

  function renderSensesT5(entry) {
    // T5 : Sens et emplois -- groupement par stem (Qal, Niph, Piel...)
    // Fallback sur bd (flat) si pas de `se`.
    var senses = entry.se;
    if (!Array.isArray(senses) || senses.length === 0) {
      if (Array.isArray(entry.bd) && entry.bd.length > 0) {
        return '<div class="fb-hebrew-card__senses-block">' +
          '<div class="fb-hebrew-card__senses-title">Sens et emplois</div>' +
          '<div class="fb-hebrew-card__stem-group">' +
          '<span class="fb-hebrew-card__stem-label" title="Usages principales">Usages</span>' +
          '<ol class="fb-hebrew-card__sense-list">' +
          entry.bd.map(function (d) { return '<li>' + escapeHtmlHe(d) + '</li>'; }).join('') +
          '</ol></div></div>';
      }
      return '';
    }

    // Regrouper par stem (ordre d'apparition preserve)
    var groups = [];
    var byStem = {};
    senses.forEach(function (s) {
      var st = (s.st || '').trim();
      if (!(st in byStem)) { byStem[st] = []; groups.push({ stem: st, items: byStem[st] }); }
      byStem[st].push(s);
    });

    var hasAnyStem = groups.some(function (g) { return g.stem; });

    return '<div class="fb-hebrew-card__senses-block">' +
      '<div class="fb-hebrew-card__senses-title">Sens et emplois</div>' +
      groups.map(function (g) {
        var label = g.stem || (hasAnyStem ? 'Autres' : 'Usages');
        var tip = g.stem ? stemTooltip(g.stem) : '';
        var tipAttr = tip ? ' title="' + escapeHtml(tip) + '"' : '';
        return '<div class="fb-hebrew-card__stem-group">' +
          '<span class="fb-hebrew-card__stem-label"' + tipAttr + '>' + escapeHtml(label) + '</span>' +
          '<ol class="fb-hebrew-card__sense-list">' +
          g.items.map(renderSenseItem).join('') +
          '</ol></div>';
      }).join('') +
    '</div>';
  }

  function renderBdbRefsT6(br) {
    if (!Array.isArray(br) || br.length === 0) return '';
    return '<div class="fb-hebrew-card__refs">' +
      '<div class="fb-hebrew-card__refs-label">Passages bibliques</div>' +
      '<div class="fb-hebrew-card__refs-list">' +
      br.map(function (r) {
        var info = parseBymRef(r);
        var label = escapeHtml(osterwaldRef(r));
        if (info) {
          var verseEndAttr = info.verseEnd ? ' data-verse-end="' + info.verseEnd + '"' : '';
          return '<span class="fb-hebrew-card__ref-link fb-ref-badge"' +
            ' data-file="' + escapeHtml(info.file) + '"' +
            ' data-code="' + escapeHtml(info.code) + '"' +
            ' data-chapter="' + info.chapter + '"' +
            ' data-verse="' + info.verse + '"' +
            verseEndAttr +
            ' title="Ouvrir la bulle verset BYM">' + label + '</span>';
        }
        return '<span class="fb-hebrew-card__ref-link">' + label + '</span>';
      }).join(' \u00b7 ') +
      '</div></div>';
  }

  function renderEtymT7(etymText, twot) {
    if (!etymText && !twot) return '';
    var parts = [];
    if (etymText) parts.push(strongLinkify(etymText));
    if (twot) parts.push('<span class="fb-hebrew-card__twot">TWOT #' + escapeHtml(twot) + '</span>');
    return '<div class="fb-hebrew-card__etym">' +
      '<span class="fb-hebrew-card__etym-label">\u00c9tymologie</span> ' +
      parts.join(' ') +
    '</div>';
  }

  function renderHebrewCard(entry, concRefs, rootData) {
    var concHtml = buildConcordanceHtml(entry.s, concRefs);

    // T1 : Identite -- Strong + POS (bp si plus precis que p) + racine pill
    var posLabel = entry.bp || entry.p || '';
    var posTitle = (entry.bp && entry.p && entry.bp !== entry.p) ? (entry.bp + ' (Strong: ' + entry.p + ')') : posLabel;
    var posHtml = posLabel ? '<span class="fb-hebrew-card__pos" title="' + escapeHtml(posTitle) + '">' + escapeHtml(posLabel) + '</span>' : '';

    var rootPill = '';
    if (rootData && rootData.r && rootData.f) {
      var rootCount = rootData.f.length + 1;
      rootPill = '<button class="fb-hebrew-card__root-pill" type="button"'
        + ' data-root="' + escapeHtml(rootData.r) + '"'
        + ' data-root-count="' + rootCount + '"'
        + ' data-strong="' + escapeHtml(entry.s) + '">'
        + 'Racine <span dir="rtl">' + escapeHtml(rootData.r) + '</span> \u2192 ' + rootCount
        + '</button>';
    }

    // T4 : Bouton expand vers BDB complete (df)
    var expandHtml = (function () {
      var shortD = entry.d || '';
      var fullD = (entry.df && entry.df !== shortD) ? entry.df : (shortD.length > 120 ? shortD : '');
      if (!fullD) return '';
      return '<div class="fb-hebrew-card__def fb-hebrew-card__def--full" hidden>' + escapeHtmlHe(fullD) + '</div>' +
        '<button class="fb-hebrew-card__expand" type="button">D\u00e9finition compl\u00e8te BDB \u2192</button>';
    })();

    return '<div class="fb-hebrew-card">' +
      // T1
      '<div class="fb-hebrew-card__head">' +
        '<span class="fb-hebrew-card__strong">' + escapeHtml(entry.s) + '</span>' +
        posHtml +
        rootPill +
      '</div>' +
      // T2
      '<div class="fb-hebrew-card__hebrew" dir="rtl">' + escapeHtml(entry.h || '') +
        (entry.h ? ' <button class="fb-hebrew-card__audio" type="button" data-text="' + escapeHtml(entry.h) + '" data-lang="he-IL" title="\u00c9couter la prononciation" aria-label="\u00c9couter la prononciation">\ud83d\udd0a</button>' : '') +
      '</div>' +
      (entry.x ? '<div class="fb-hebrew-card__translit">' + escapeHtml(entry.x) + '</div>' : '') +
      (entry.pr ? '<div class="fb-hebrew-card__pron">' + escapeHtml(entry.pr) + '</div>' : '') +
      // T3
      '<div class="fb-hebrew-card__def fb-hebrew-card__def--short">' + escapeHtmlHe(truncate(entry.d || '', 120)) + '</div>' +
      // T4
      expandHtml +
      // T5-T7
      renderSensesT5(entry) +
      renderBdbRefsT6(entry.br) +
      renderEtymT7(entry.et, entry.tw) +
      // Concordance BYM (bonus)
      concHtml +
    '</div>';
  }

  function injectHebrewCards(conceptBody) {
    if (!conceptBody || conceptBody.getAttribute('data-hebrew-injected')) return;
    var contents = conceptBody.querySelectorAll(SOURCE_CONTENT_SEL);
    var allHtml = '';
    for (var i = 0; i < contents.length; i++) allHtml += contents[i].innerHTML;

    var strongs = detectStrongNumbers(allHtml);
    if (strongs.size === 0) return;
    conceptBody.setAttribute('data-hebrew-injected', '1');

    Promise.all([loadLexicon(), loadConcordance(), loadRootFamilies()]).then(function (results) {
      var index = results[0];
      var conc = results[1];
      var roots = results[2];
      var cards = [];
      strongs.forEach(function (num) {
        var entry = index.get(num);
        if (entry) cards.push(renderHebrewCard(entry, conc[num] || [], roots[num] || null));
      });
      if (cards.length === 0) return;

      var wrapper = document.createElement('div');
      wrapper.className = 'fb-hebrew-sidebar';
      wrapper.innerHTML =
        '<h3 class="fb-hebrew-sidebar__title">Lexique hébreu biblique</h3>' +
        cards.join('') +
        '<p class="fb-hebrew-sidebar__sources"><strong>Sources :</strong> Brown-Driver-Briggs (BDB) · Open Scriptures Hebrew Bible (OSHB) · Numérotation Strong</p>';

      // Greek lexicon placeholder
      var greekPlaceholder = document.createElement('div');
      greekPlaceholder.className = 'fb-greek-placeholder';
      greekPlaceholder.innerHTML = '<div class="fb-greek-placeholder__icon">\u0391</div>'
        + '<div class="fb-greek-placeholder__label">Lexique grec (Thayer)</div>'
        + '<div class="fb-greek-placeholder__note">Bient\u00f4t disponible</div>';
      wrapper.appendChild(greekPlaceholder);

      var sidebar = conceptBody.querySelector('.' + SIDEBAR_CLASS);
      if (sidebar) {
        sidebar.insertBefore(wrapper, sidebar.firstChild);
      } else {
        var mainStack = conceptBody.querySelector('.fb-main-stack');
        if (mainStack) mainStack.appendChild(wrapper);
      }

      // Wire BDB expand buttons
      wrapper.querySelectorAll('.fb-hebrew-card__expand').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var card = btn.closest('.fb-hebrew-card');
          if (!card) return;
          var shortDef = card.querySelector('.fb-hebrew-card__def--short');
          var fullDef = card.querySelector('.fb-hebrew-card__def--full');
          if (shortDef && fullDef) {
            shortDef.hidden = true;
            fullDef.hidden = false;
            btn.hidden = true;
          }
        });
      });

      // Wire concordance book accordion
      wrapper.querySelectorAll('.fb-conc-book-pill').forEach(function (pill) {
        pill.addEventListener('click', function () {
          var idx = pill.getAttribute('data-conc-book');
          var conc = pill.closest('.fb-hebrew-card__conc');
          if (!conc) return;
          var panel = conc.querySelector('[data-conc-panel="' + idx + '"]');
          if (!panel) return;
          // Toggle: close if already open, else close all and open this one
          var wasOpen = !panel.hidden;
          conc.querySelectorAll('.fb-conc-panel').forEach(function (p) { p.hidden = true; });
          conc.querySelectorAll('.fb-conc-book-pill').forEach(function (p) { p.classList.remove('is-active'); });
          if (!wasOpen) {
            panel.hidden = false;
            pill.classList.add('is-active');
          }
        });
      });
      // Wire root sibling clicks — scroll to card if on page
      wrapper.querySelectorAll('.fb-root-sibling').forEach(function (sib) {
        sib.addEventListener('click', function () {
          var strong = sib.getAttribute('data-strong');
          if (!strong) return;
          var allCards = wrapper.querySelectorAll('.fb-hebrew-card');
          for (var c = 0; c < allCards.length; c++) {
            var s = allCards[c].querySelector('.fb-hebrew-card__strong');
            if (s && s.textContent.trim() === strong) {
              var found = allCards[c];
              found.classList.add('fb-hebrew-card--highlight');
              found.scrollIntoView({ behavior: 'smooth', block: 'center' });
              setTimeout(function () { found.classList.remove('fb-hebrew-card--highlight'); }, 1500);
              return;
            }
          }
        });
      });
    }).catch(function () { /* silent */ });
  }

  // ── 4. MODULE SOURCE JOURNEY ──────────────────────────────────────

  var ROLE_META = {
    quick_gloss:          { color: '#B28C64', label: 'Résumé' },
    main_definition:      { color: '#7e5d43', label: 'Définition' },
    detailed_reference:   { color: '#5a7a55', label: 'Référence' },
    secondary_definition: { color: '#7e5d43', label: 'Secondaire' },
    deep_read:            { color: '#6b5b8a', label: 'Lecture' }
  };

  function injectSourceJourney(conceptBody) {
    if (!conceptBody || conceptBody.querySelector('.fb-source-journey')) return;
    var cards = conceptBody.querySelectorAll('.fb-source-card');
    if (cards.length < 2) return;

    var seen = {};
    var steps = [];
    for (var i = 0; i < cards.length; i++) {
      var role = cards[i].getAttribute('data-role');
      if (!role || seen[role]) continue;
      seen[role] = true;
      var meta = ROLE_META[role];
      if (!meta) continue;
      steps.push(
        '<div class="fb-source-journey__step" data-role="' + escapeHtml(role) + '" style="--dot-color:' + meta.color + '">' +
          '<span class="fb-source-journey__dot"></span>' +
          '<span class="fb-source-journey__label">' + escapeHtml(meta.label) + '</span>' +
        '</div>'
      );
    }
    if (steps.length < 2) return;

    var journey = document.createElement('nav');
    journey.className = 'fb-source-journey';
    journey.setAttribute('aria-label', 'Parcours des sources');
    journey.innerHTML = steps.join('<span class="fb-source-journey__line"></span>');

    var mainStack = conceptBody.querySelector('.fb-main-stack');
    if (mainStack) mainStack.insertBefore(journey, mainStack.firstChild);

    // Scroll-to on dot click
    journey.addEventListener('click', function (e) {
      var step = e.target.closest('.fb-source-journey__step');
      if (!step) return;
      var targetRole = step.getAttribute('data-role');
      var card = conceptBody.querySelector('.fb-source-card[data-role="' + targetRole + '"]');
      if (card) card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  // ── 5. MODULE SEARCH EXTEND ───────────────────────────────────────

  var SEARCH_TYPES = {
    strong:   { label: 'Strong',          color: '#B28C64' },
    hebrew:   { label: 'Hébreu',          color: '#8B6914' },
    translit: { label: 'Translitération', color: '#5a7a55' },
    french:   { label: null,              color: null }
  };

  function detectSearchType(query) {
    query = (query || '').trim();
    if (/^[HG]\d{1,5}$/i.test(query)) return 'strong';
    if (/[\u0590-\u05FF]/.test(query)) return 'hebrew';
    if (/[ʼʻʾʿāēīōūâêîôûḥḳṣṭ]/.test(query)) return 'translit';
    return 'french';
  }

  function showTypeIndicator(type, inputEl) {
    var existing = inputEl.parentNode.querySelector('.fb-search-type-indicator');
    if (existing) existing.remove();
    var meta = SEARCH_TYPES[type];
    if (!meta || !meta.label) return;
    var pill = document.createElement('span');
    pill.className = 'fb-search-type-indicator';
    pill.textContent = meta.label;
    pill.style.setProperty('--indicator-color', meta.color);
    inputEl.parentNode.style.position = 'relative';
    inputEl.parentNode.appendChild(pill);
  }

  function searchLexicon(query, type) {
    return loadLexicon().then(function (index) {
      var results = [];
      var q = query.trim();
      if (type === 'strong') {
        var entry = index.get(q.toUpperCase());
        if (entry) results.push(entry);
      } else {
        var qLow = q.toLowerCase();
        lexiconData.forEach(function (entry) {
          if (results.length >= 20) return;
          if (type === 'hebrew' && entry.h && entry.h.indexOf(q) !== -1) {
            results.push(entry);
          } else if (type === 'translit' && entry.x && entry.x.toLowerCase().indexOf(qLow) !== -1) {
            results.push(entry);
          }
        });
      }
      return results;
    });
  }

  function renderLexiconResults(entries) {
    if (entries.length === 0) return '';
    return '<div class="fb-lexicon-results">' +
      '<h3 class="fb-lexicon-results__title">Résultats du lexique hébreu</h3>' +
      entries.map(function (e) {
        return '<div class="fb-lexicon-result">' +
          '<span class="fb-lexicon-result__strong">' + escapeHtml(e.s) + '</span>' +
          '<span class="fb-lexicon-result__hebrew" dir="rtl">' + escapeHtml(e.h || '') + '</span>' +
          '<span class="fb-lexicon-result__translit">' + escapeHtml(e.x || '') + '</span>' +
          '<div class="fb-lexicon-result__def">' + escapeHtml(truncate(e.d || '', 150)) + '</div>' +
        '</div>';
      }).join('') +
    '</div>';
  }

  function interceptSearch() {
    var input = document.querySelector(SEARCH_INPUT_SEL);
    if (!input || input.getAttribute('data-v3-search')) return;
    input.setAttribute('data-v3-search', '1');

    var debounce = null;
    input.addEventListener('input', function () {
      clearTimeout(debounce);
      var query = input.value;
      var type = detectSearchType(query);
      showTypeIndicator(type, input);

      if (type === 'french') {
        removeLexiconResults();
        return;
      }
      debounce = setTimeout(function () {
        searchLexicon(query, type).then(function (results) {
          injectLexiconSearchResults(results);
        }).catch(function () { /* silent */ });
      }, 300);
    });
  }

  function injectLexiconSearchResults(entries) {
    removeLexiconResults();
    var html = renderLexiconResults(entries);
    if (!html) return;
    var app = document.querySelector(APP_SEL);
    if (!app) return;
    var searchResults = app.querySelector('.fb-search-results, .fb-browse-shell');
    if (!searchResults) return;
    var container = document.createElement('div');
    container.className = 'fb-lexicon-results-wrapper';
    container.innerHTML = html;
    searchResults.parentNode.insertBefore(container, searchResults);
  }

  function removeLexiconResults() {
    var existing = document.querySelector('.fb-lexicon-results-wrapper');
    if (existing) existing.remove();
  }

  // ── 6. ORCHESTRATION ──────────────────────────────────────────────

  function applyPatches() {
    restructureConceptLayout();
    injectBreadcrumb();
    enhanceReadingPanel();
    injectSourceJourney(document.querySelector(CONCEPT_BODY_SEL));

    // Wrap biblical references in all source content blocks
    var contents = document.querySelectorAll(SOURCE_CONTENT_SEL);
    for (var i = 0; i < contents.length; i++) wrapBiblicalReferences(contents[i]);

    // Also wrap in reading panel body
    var readingBody = document.querySelector(READING_PANEL_SEL + ' .fb-reading-body');
    if (readingBody) wrapBiblicalReferences(readingBody);

    // Inject Hebrew cards
    injectHebrewCards(document.querySelector(CONCEPT_BODY_SEL));

    // Mobile-only: build a table of contents at the top of the concept body
    buildMobileTOC();

    // Sync topbar height
    var topbar = document.querySelector(TOPBAR_SEL);
    var app = document.querySelector(APP_SEL);
    if (topbar && app) {
      var h = topbar.offsetHeight;
      if (h > 0) app.style.setProperty('--fb-topbar-height', h + 'px');
    }

    // Extend search if available
    interceptSearch();
  }

  function initObserver() {
    var app = document.querySelector(APP_SEL);
    if (!app) return;
    var timer = null;
    var observer = new MutationObserver(function () {
      if (timer) clearTimeout(timer);
      timer = setTimeout(applyPatches, 60);
    });
    observer.observe(app, { childList: true, subtree: true });
    window.addEventListener('hashchange', function () { setTimeout(applyPatches, 150); });
    applyPatches();
  }

  function markV3() {
    document.documentElement.classList.add('bible-v3');
    var app = document.querySelector(APP_SEL);
    if (app) app.classList.add('v3-patched');
  }

  var _verseBubbleHandlerAttached = false;
  function init() {
    // Handler verse-bubble — toujours actif (handler document-level, utile aussi
    // sur page lexique ou ailleurs ou des .fb-ref-badge apparaitraient sans app v2)
    if (!_verseBubbleHandlerAttached) {
      initVerseBubbleClicks();
      _verseBubbleHandlerAttached = true;
    }

    var app = document.querySelector(APP_SEL);
    if (!app) {
      if (document.readyState !== 'complete') window.addEventListener('load', init);
      return;
    }
    markV3();
    initTopbarScroll();
    initKeyboard();
    initBreadcrumbNav();
    initObserver();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
