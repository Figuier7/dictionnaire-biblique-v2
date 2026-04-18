/**
 * Bible Hebrew Utils — translitte\u0301ration automatique des mots he\u0301breu inline.
 * Utilise\u0301 par :
 *   - kadence-child/js/lexique-strong-app.js   (page lexique d\u00e9die\u00e9e)
 *   - kadence-child/js/bible-v3-patch.js       (dictionnaire concept — sidebar fb-hebrew-card)
 *   - kadence-child/js/bible-interlineaire-app.js  (bible interline\u00e9aire — sidebar bi-sidebar)
 *
 * Expose : window.FIGUIER_HEBREW_UTILS = {
 *   hebrewToTranslit, applyHebrewPrefs, injectTranslitsInContainer
 * }
 *
 * Comportement : translitte\u0301ration [xxx] injecte\u0301e apr\u00e8s chaque .fb-inline-he
 * automatiquement et de fac\u0327on permanente (pas de toggle, pas de pre\u0301fe\u0301rence).
 *
 * Performance :
 *   - Cache me\u0301moire _translitCache : chaque mot traduit 1× max
 *   - MutationObserver debounc\u00e9 a\u0300 200ms pour le contenu injecte\u0301 dynamiquement
 */
(function (global) {
  'use strict';

  // ============================================================
  // Translitte\u0301ration he\u0301breu \u2192 latin (scholarly simplifie\u0301e)
  // ============================================================

  // Consonnes : forme avec daguesh, sans daguesh (begad-kephat)
  var CONSONANT_MAP = {
    '\u05D0': '\u02BE',   // alef → ʾ
    '\u05D1': 'b',        // bet
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

  var _translitCache = {};

  function hebrewToTranslit(heb) {
    if (!heb) return '';
    if (_translitCache[heb]) return _translitCache[heb];

    // Normaliser NFC pour ordre canonique des combining marks
    var s = (typeof heb.normalize === 'function') ? heb.normalize('NFC') : heb;
    // Retirer ta'amim (cantillation U+0591–U+05AF)
    s = s.replace(/[\u0591-\u05AF]/g, '');

    var out = [];
    var prevChar = '';
    for (var i = 0; i < s.length; i++) {
      var c = s[i];
      var next = s[i + 1] || '';

      if (CONSONANT_MAP.hasOwnProperty(c)) {
        var cons = CONSONANT_MAP[c];
        // Shin / Sin : distinction par pointage suivant
        if (c === '\u05E9') {
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
        out.push(cons);
        prevChar = cons;
        continue;
      }

      if (VOWEL_MAP.hasOwnProperty(c)) {
        var vow = VOWEL_MAP[c];

        // Shureq : waw + daguesh (וּ) → û
        if (c === '\u05BC' && prevChar === 'w') {
          out.pop();
          out.push('\u00FB');
          prevChar = '\u00FB';
          continue;
        }
        // Holam haser pour waw : וֹ → ō
        if (c === '\u05B9' && prevChar === 'w') {
          out.pop();
          out.push('\u014D');
          prevChar = '\u014D';
          continue;
        }
        // Hiriq + yod = î
        if (c === '\u05B4' && next === '\u05D9') {
          out.push('\u00EE');
          i++;
          prevChar = '\u00EE';
          continue;
        }
        // Tsere + yod = ê
        if (c === '\u05B5' && next === '\u05D9') {
          out.push('\u00EA');
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

      if (c === ' ') out.push(' ');
    }

    var result = out.join('').replace(/\s+/g, ' ').trim();
    _translitCache[heb] = result;
    return result;
  }

  // ============================================================
  // Injection des translitte\u0301rations dans le DOM
  // ============================================================

  /**
   * Injecte [translit] apr\u00e8s chaque <span class="fb-inline-he"> du conteneur.
   * Lazy : ne fait rien si la translit est de\u0301ja\u0300 injecte\u0301e.
   */
  function injectTranslitsInContainer(container) {
    if (!container || !container.querySelectorAll) return;
    var spans = container.querySelectorAll('.fb-inline-he');
    for (var i = 0; i < spans.length; i++) {
      var span = spans[i];
      if (span.nextElementSibling && span.nextElementSibling.classList.contains('fb-inline-translit')) {
        continue;
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

  /**
   * Applique les translits sur tout le document. A\u0300 appeler apr\u00e8s chaque render.
   */
  function applyHebrewPrefs() {
    if (document.body) {
      injectTranslitsInContainer(document.body);
    }
  }

  // ============================================================
  // MutationObserver : auto-apply quand de nouveaux .fb-inline-he apparaissent
  // ============================================================
  var _moDebounceTimer = null;
  function _setupMutationObserver() {
    if (typeof MutationObserver === 'undefined') return;
    if (!document.body) return;
    var observer = new MutationObserver(function (mutations) {
      var needsApply = false;
      for (var i = 0; i < mutations.length; i++) {
        var m = mutations[i];
        if (m.addedNodes && m.addedNodes.length > 0) {
          for (var j = 0; j < m.addedNodes.length; j++) {
            var n = m.addedNodes[j];
            if (n.nodeType !== 1) continue;
            if (n.classList && n.classList.contains('fb-inline-he')) { needsApply = true; break; }
            if (n.querySelector && n.querySelector('.fb-inline-he')) { needsApply = true; break; }
          }
        }
        if (needsApply) break;
      }
      if (!needsApply) return;
      if (_moDebounceTimer) clearTimeout(_moDebounceTimer);
      _moDebounceTimer = setTimeout(function () {
        injectTranslitsInContainer(document.body);
      }, 200);
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  // ============================================================
  // Init
  // ============================================================
  function init() {
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

  // ============================================================
  // Export global (API simplifie\u0301e)
  // ============================================================
  global.FIGUIER_HEBREW_UTILS = {
    hebrewToTranslit: hebrewToTranslit,
    applyHebrewPrefs: applyHebrewPrefs,
    injectTranslitsInContainer: injectTranslitsInContainer,
  };

  init();

})(typeof window !== 'undefined' ? window : this);
