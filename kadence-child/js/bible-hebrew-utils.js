/**
 * Bible Hebrew Utils — fonctions partage\u0301es pour la lisibilite\u0301 pedagogique
 * Utilise\u0301 par :
 *   - kadence-child/js/lexique-strong-app.js   (page lexique d\u00e9die\u00e9e)
 *   - kadence-child/js/bible-v3-patch.js       (dictionnaire concept — sidebar fb-hebrew-card)
 *   - kadence-child/js/bible-interlineaire-app.js  (bible interline\u00e9aire — sidebar bi-sidebar)
 *
 * Expose : window.FIGUIER_HEBREW_UTILS = {
 *   hebrewToTranslit, initHebrewControls, toggleHideHebrew, toggleTranslitAuto,
 *   applyHebrewPrefs, isHideHebrewOn, isTranslitAutoOn
 * }
 *
 * Performance :
 *   - Translittération calcul\u00e9e lazy (seulement si option active) + cache memoire
 *   - Toggle hide he\u0301breu = CSS class globale sur <body> (0 cost JS)
 *   - localStorage pour persister les pr\u00e9f\u00e9rences utilisateur
 */
(function (global) {
  'use strict';

  // ============================================================
  // Translitteration he\u0301breu \u2192 latin (scholarly simplifie\u0301e)
  // ============================================================

  // Consonnes : forme avec daguesh, sans daguesh (begad-kephat)
  var CONSONANT_MAP = {
    '\u05D0': '\u02BE',   // alef → ʾ
    '\u05D1': 'b',        // bet (avec daguesh)
    '\u05D2': 'g',        // gimel
    '\u05D3': 'd',        // dalet
    '\u05D4': 'h',        // he
    '\u05D5': 'w',        // waw (vav)
    '\u05D6': 'z',        // zayin
    '\u05D7': '\u1E25',   // het → ḥ
    '\u05D8': '\u1E6D',   // tet → ṭ
    '\u05D9': 'y',        // yod
    '\u05DA': 'k',        // kaph final
    '\u05DB': 'k',        // kaph
    '\u05DC': 'l',        // lamed
    '\u05DD': 'm',        // mem final
    '\u05DE': 'm',        // mem
    '\u05DF': 'n',        // nun final
    '\u05E0': 'n',        // nun
    '\u05E1': 's',        // samekh
    '\u05E2': '\u02BF',   // ayin → ʿ
    '\u05E3': 'p',        // pe final
    '\u05E4': 'p',        // pe
    '\u05E5': '\u1E63',   // tsade final → ṣ
    '\u05E6': '\u1E63',   // tsade → ṣ
    '\u05E7': 'q',        // qoph
    '\u05E8': 'r',        // resh
    '\u05E9': 's',        // shin/sin (default s, refined by shin/sin dot below)
    '\u05EA': 't',        // tav
  };

  // Voyelles / niqqud
  var VOWEL_MAP = {
    '\u05B0': '\u0259',   // shewa → ə
    '\u05B1': '\u0115',   // hataf segol → ĕ
    '\u05B2': '\u0103',   // hataf patah → ă
    '\u05B3': '\u014F',   // hataf qamats → ŏ
    '\u05B4': 'i',        // hiriq → i
    '\u05B5': '\u0113',   // tsere → ē
    '\u05B6': 'e',        // segol → e
    '\u05B7': 'a',        // patah → a
    '\u05B8': '\u0101',   // qamats → ā
    '\u05B9': '\u014D',   // holam → ō
    '\u05BA': '\u014D',   // holam haser for vav → ō
    '\u05BB': 'u',        // qibbuts → u
    '\u05BC': '',         // daguesh (handled separately)
    '\u05BD': '',         // meteg (ignored)
    '\u05BE': '-',        // maqaf → hyphen
    '\u05C1': '',         // shin dot (handled in context)
    '\u05C2': '',         // sin dot (handled in context)
    '\u05C4': '',         // upper dot (ignored)
    '\u05C5': '',         // lower dot (ignored)
  };

  // Begad-kephat : b/g/d/k/p/t sans daguesh → begadkephat spirants (ḇ/ḡ/ḏ/ḵ/p̄/ṯ)
  // Pour simplifier on garde les formes dures — un usage scholarly strict demanderait plus de contexte.

  // Cache translit : heb → translit
  var _translitCache = {};

  function hebrewToTranslit(heb) {
    if (!heb) return '';
    if (_translitCache[heb]) return _translitCache[heb];

    // Normaliser NFC pour ordre canonique des combining marks
    var s = (typeof heb.normalize === 'function') ? heb.normalize('NFC') : heb;

    // Retirer ta'amim (cantillation U+0591–U+05AF) mais garder niqqud (U+05B0-U+05BC, U+05C1-U+05C5)
    s = s.replace(/[\u0591-\u05AF]/g, '');

    var out = [];
    var prevChar = '';
    for (var i = 0; i < s.length; i++) {
      var c = s[i];
      var next = s[i + 1] || '';

      // Consonne de base
      if (CONSONANT_MAP.hasOwnProperty(c)) {
        var cons = CONSONANT_MAP[c];

        // Shin / Sin : distinction par pointage suivant
        if (c === '\u05E9') {
          // Chercher shin/sin dot dans les chars suivants (peut être après niqqud)
          var hasShinDot = false, hasSinDot = false;
          for (var j = i + 1; j < s.length && j < i + 4; j++) {
            if (s[j] === '\u05C1') { hasShinDot = true; break; }
            if (s[j] === '\u05C2') { hasSinDot = true; break; }
            if (s[j] < '\u05B0' || s[j] > '\u05C7') break;
          }
          if (hasShinDot) cons = '\u0161';  // š
          else if (hasSinDot) cons = '\u015B';  // ś
          else cons = '\u0161';  // default à š
        }

        // Begadkephat : bet, gimel, dalet, kaph, pe, tav
        //   → si suivi de daguesh (U+05BC) = dur, sinon spirant
        // On simplifie : garder forme dure par défaut (pour lisibilité étudiante)
        // (une translittération scholarly pleine demanderait bgdkpt différencié)

        out.push(cons);
        prevChar = cons;
        continue;
      }

      // Voyelles / niqqud
      if (VOWEL_MAP.hasOwnProperty(c)) {
        var vow = VOWEL_MAP[c];

        // Holam suivi de waw → ō (bugpass : on a déjà ajouté w pour waw)
        // Shureq : waw + daguesh (וּ) → û
        if (c === '\u05BC' && prevChar === 'w') {
          out.pop();  // retirer le 'w' ajouté
          out.push('\u00FB');  // û
          prevChar = '\u00FB';
          continue;
        }

        // Holam haser pour waw : les chars sont souvent וֹ → ō
        if (c === '\u05B9' && prevChar === 'w') {
          out.pop();  // retirer 'w'
          out.push('\u014D');  // ō
          prevChar = '\u014D';
          continue;
        }

        // Hiriq + yod = î
        if (c === '\u05B4' && next === '\u05D9') {
          out.push('\u00EE');  // î
          i++;  // skip yod
          prevChar = '\u00EE';
          continue;
        }

        // Tsere + yod = ê
        if (c === '\u05B5' && next === '\u05D9') {
          out.push('\u00EA');  // ê
          i++;
          prevChar = '\u00EA';
          continue;
        }

        if (vow) {
          out.push(vow);
          prevChar = vow;
        }
        continue;
      }

      // Char non-hebrew (espace, ponctuation)
      if (c === ' ') {
        out.push(' ');
      }
    }

    var result = out.join('').replace(/\s+/g, ' ').trim();
    _translitCache[heb] = result;
    return result;
  }

  // ============================================================
  // Pre\u0301fe\u0301rences utilisateur (localStorage)
  // ============================================================

  var PREF_KEYS = {
    HIDE_HEBREW: 'figuier_hide_hebrew',
    TRANSLIT_AUTO: 'figuier_translit_auto',
  };

  function _readPref(key) {
    try {
      return localStorage.getItem(key) === '1';
    } catch (e) { return false; }
  }

  function _writePref(key, val) {
    try {
      localStorage.setItem(key, val ? '1' : '0');
    } catch (e) { /* localStorage indisponible, ignore */ }
  }

  function isHideHebrewOn() { return _readPref(PREF_KEYS.HIDE_HEBREW); }
  function isTranslitAutoOn() { return _readPref(PREF_KEYS.TRANSLIT_AUTO); }

  // ============================================================
  // Application des pre\u0301fe\u0301rences au DOM
  // ============================================================

  /**
   * Met a\u0300 jour le body avec les classes correspondant aux pre\u0301fs.
   * - body.figuier-hide-hebrew : CSS global masque les .fb-inline-he
   * - body.figuier-translit-auto : CSS global peut affecter affichage translit
   * Translit est injecte\u0301e dynamiquement dans injectTranslitsInContainer().
   */
  function applyHebrewPrefs() {
    var body = document.body;
    if (!body) return;
    body.classList.toggle('figuier-hide-hebrew', isHideHebrewOn());
    body.classList.toggle('figuier-translit-auto', isTranslitAutoOn());
    // Si translit auto on, injecter dans tous les containers d\u00e9ja pre\u0301sents
    if (isTranslitAutoOn()) {
      injectTranslitsInContainer(document);
    } else {
      removeInjectedTranslits(document);
    }
    // Synchroniser e\u0301tat des boutons toggles existants
    _syncToggleButtons();
  }

  /**
   * Injecte [translit] apr\u00e8s chaque <span class="fb-inline-he"> du conteneur.
   * Lazy : ne fait rien si la translit est de\u0301ja\u0300 injecte\u0301e.
   * Cache via _translitCache pour ne pas recalculer.
   */
  function injectTranslitsInContainer(container) {
    if (!container || !container.querySelectorAll) return;
    var spans = container.querySelectorAll('.fb-inline-he');
    for (var i = 0; i < spans.length; i++) {
      var span = spans[i];
      if (span.nextElementSibling && span.nextElementSibling.classList.contains('fb-inline-translit')) {
        continue;  // de\u0301ja\u0300 injecte\u0301
      }
      var heb = span.textContent || '';
      if (!heb.trim()) continue;
      var translit = hebrewToTranslit(heb);
      if (!translit) continue;
      var tr = document.createElement('span');
      tr.className = 'fb-inline-translit';
      tr.setAttribute('aria-label', 'Translitte\u0301ration');
      tr.textContent = ' [' + translit + ']';
      span.parentNode.insertBefore(tr, span.nextSibling);
    }
  }

  function removeInjectedTranslits(container) {
    if (!container || !container.querySelectorAll) return;
    var trs = container.querySelectorAll('.fb-inline-translit');
    for (var i = 0; i < trs.length; i++) {
      trs[i].parentNode.removeChild(trs[i]);
    }
  }

  // ============================================================
  // Toggles
  // ============================================================

  function toggleHideHebrew() {
    var next = !isHideHebrewOn();
    _writePref(PREF_KEYS.HIDE_HEBREW, next);
    applyHebrewPrefs();
    return next;
  }

  function toggleTranslitAuto() {
    var next = !isTranslitAutoOn();
    _writePref(PREF_KEYS.TRANSLIT_AUTO, next);
    applyHebrewPrefs();
    return next;
  }

  // ============================================================
  // UI : bouton(s) toggle
  // ============================================================

  /**
   * Cre\u0301e un composant barre de pre\u0301fs a\u0300 inse\u0301rer dans un conteneur.
   * Structure : <div class="figuier-hebrew-controls">[toggle hide] [toggle translit]</div>
   */
  function createHebrewControlsBar() {
    var wrap = document.createElement('div');
    wrap.className = 'figuier-hebrew-controls';
    wrap.setAttribute('role', 'group');
    wrap.setAttribute('aria-label', 'Options d\u2019affichage he\u0301breu');

    var btnHide = document.createElement('button');
    btnHide.type = 'button';
    btnHide.className = 'figuier-hebrew-btn figuier-hebrew-btn--hide';
    btnHide.setAttribute('data-pref', 'hide');
    btnHide.setAttribute('aria-pressed', isHideHebrewOn() ? 'true' : 'false');
    btnHide.title = 'Masquer les caracte\u0300res he\u0301breu dans le texte explicatif (pour lecture facile)';
    btnHide.innerHTML = '<span class="figuier-hebrew-btn__icon">\u05D0</span> <span class="figuier-hebrew-btn__label">Masquer he\u0301breu</span>';
    btnHide.addEventListener('click', function () { toggleHideHebrew(); });
    wrap.appendChild(btnHide);

    var btnTranslit = document.createElement('button');
    btnTranslit.type = 'button';
    btnTranslit.className = 'figuier-hebrew-btn figuier-hebrew-btn--translit';
    btnTranslit.setAttribute('data-pref', 'translit');
    btnTranslit.setAttribute('aria-pressed', isTranslitAutoOn() ? 'true' : 'false');
    btnTranslit.title = 'Afficher [translitte\u0301ration] apre\u0300s chaque mot he\u0301breu';
    btnTranslit.innerHTML = '<span class="figuier-hebrew-btn__icon">[\u02BE]</span> <span class="figuier-hebrew-btn__label">Translit. auto</span>';
    btnTranslit.addEventListener('click', function () { toggleTranslitAuto(); });
    wrap.appendChild(btnTranslit);

    return wrap;
  }

  /**
   * Synchronise visuellement l'e\u0301tat aria-pressed des boutons toggle existants.
   */
  function _syncToggleButtons() {
    document.querySelectorAll('.figuier-hebrew-btn').forEach(function (btn) {
      var pref = btn.getAttribute('data-pref');
      var on = pref === 'hide' ? isHideHebrewOn() : isTranslitAutoOn();
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  /**
   * Initialise les contr\u00f4les h\u00e9breu : applique les pre\u0301fs sauvegarde\u0301es au chargement.
   * Les bouton(s) sont inse\u0301re\u0301s via createHebrewControlsBar() dans chaque app qui l'appelle.
   *
   * Met aussi en place un MutationObserver global qui re-applique les pre\u0301fs
   * quand de nouveaux .fb-inline-he apparaissent (sidebar concept, popups, etc.)
   * Debounc\u00e9 a\u0300 200ms pour ne pas impacter les perfs.
   */
  function initHebrewControls() {
    // Applique les pre\u0301fs au chargement
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () {
        applyHebrewPrefs();
        _setupMutationObserver();
      });
    } else {
      applyHebrewPrefs();
      _setupMutationObserver();
    }
  }

  // MutationObserver debounced : auto-apply quand de nouveaux nodes Hebrew apparaissent
  var _moDebounceTimer = null;
  function _setupMutationObserver() {
    if (typeof MutationObserver === 'undefined') return;
    if (!document.body) return;

    var observer = new MutationObserver(function (mutations) {
      // Quick check : au moins une mutation a ajoute\u0301 un node contenant potentiellement du .fb-inline-he
      var needsApply = false;
      for (var i = 0; i < mutations.length; i++) {
        var m = mutations[i];
        if (m.addedNodes && m.addedNodes.length > 0) {
          for (var j = 0; j < m.addedNodes.length; j++) {
            var n = m.addedNodes[j];
            if (n.nodeType !== 1) continue;  // pas un element
            if (n.classList && n.classList.contains('fb-inline-he')) { needsApply = true; break; }
            if (n.querySelector && n.querySelector('.fb-inline-he')) { needsApply = true; break; }
          }
        }
        if (needsApply) break;
      }
      if (!needsApply) return;

      // Debounce
      if (_moDebounceTimer) clearTimeout(_moDebounceTimer);
      _moDebounceTimer = setTimeout(function () {
        // Ne re-applique que si l'option translit est ON (hide hebrew = pure CSS, pas besoin)
        if (isTranslitAutoOn()) {
          injectTranslitsInContainer(document.body);
        }
      }, 200);
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  // ============================================================
  // Export global
  // ============================================================
  global.FIGUIER_HEBREW_UTILS = {
    hebrewToTranslit: hebrewToTranslit,
    isHideHebrewOn: isHideHebrewOn,
    isTranslitAutoOn: isTranslitAutoOn,
    toggleHideHebrew: toggleHideHebrew,
    toggleTranslitAuto: toggleTranslitAuto,
    applyHebrewPrefs: applyHebrewPrefs,
    createHebrewControlsBar: createHebrewControlsBar,
    injectTranslitsInContainer: injectTranslitsInContainer,
    removeInjectedTranslits: removeInjectedTranslits,
    initHebrewControls: initHebrewControls,
  };

  // Auto-init au chargement
  initHebrewControls();

})(typeof window !== 'undefined' ? window : this);
