/* ================================================================
   BIBLE V3 HOTFIX — Hebrew Sidebar Label Lookup + Hero Hebrew
   Loaded AFTER bible-v3-patch.js to override specific behaviors.
   ================================================================ */

(function () {
  'use strict';

  var APP_SEL = '.figuier-bible-app[data-app="bible-v2"]';
  var CONCEPT_HERO_SEL = APP_SEL + ' .fb-concept-hero';
  var CONCEPT_BODY_SEL = APP_SEL + ' .fb-concept-body';
  var SOURCE_CONTENT_SEL = '.fb-source-content';
  var SIDEBAR_CLASS = 'fb-concept-sidebar';
  var config = window.FIGUIER_BIBLE_V2_CONFIG || {};
  var _strongMap = null; // concept_id → [Strong numbers]
  var _strongMapLoading = null;
  var _frenchStrongMap = null; // concept_id → [{ s, h, x, g }]
  var _frenchStrongMapLoading = null;
  var _hebrewMap = null; // concept_id → [{ s, h, x }] (unified)
  var _hebrewMapLoading = null;

  function loadStrongMap() {
    if (_strongMap) return Promise.resolve(_strongMap);
    if (_strongMapLoading) return _strongMapLoading;
    var url = (config.manifestUrl || '').replace(/source-manifest\.json.*$/, '') + 'concept-strong-map.json';
    _strongMapLoading = fetch(url).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (data) {
      _strongMap = data || {};
      return _strongMap;
    }).catch(function () {
      _strongMap = {};
      return _strongMap;
    });
    return _strongMapLoading;
  }

  function loadFrenchStrongMap() {
    if (_frenchStrongMap) return Promise.resolve(_frenchStrongMap);
    if (_frenchStrongMapLoading) return _frenchStrongMapLoading;
    var url = (config.manifestUrl || '').replace(/source-manifest\.json.*$/, '') + 'concept-french-strong-map.json';
    _frenchStrongMapLoading = fetch(url).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (data) {
      _frenchStrongMap = data || {};
      return _frenchStrongMap;
    }).catch(function () {
      _frenchStrongMap = {};
      return _frenchStrongMap;
    });
    return _frenchStrongMapLoading;
  }

  function loadHebrewMap() {
    if (_hebrewMap) return Promise.resolve(_hebrewMap);
    if (_hebrewMapLoading) return _hebrewMapLoading;
    var url = (config.manifestUrl || '').replace(/source-manifest\.json.*$/, '') + 'concept-hebrew-map.json';
    _hebrewMapLoading = fetch(url).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (data) {
      _hebrewMap = data || {};
      return _hebrewMap;
    }).catch(function () {
      _hebrewMap = {};
      return _hebrewMap;
    });
    return _hebrewMapLoading;
  }

  // ── BYM reader URL codes (book number → URL abbreviation) ────────
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

  // ── Helpers ───────────────────────────────────────────────────────

  function escapeHtml(s) {
    return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function truncate(s, n) {
    s = (s || '').trim();
    return s.length <= n ? s : s.slice(0, n).replace(/\s+\S*$/, '') + '\u2026';
  }

  /** Normalize a transliteration string for fuzzy matching */
  function normalizeTranslit(s) {
    return (s || '').toLowerCase()
      .replace(/[\u02BC\u02BB\u02BE\u02BF\u0027\u2018\u2019]/g, '') // ʼ ʻ ʾ ʿ ' ' '
      .replace(/[\u0103\u0101\u00E2\u00E0\u00E4]/g, 'a')  // ă ā â à ä
      .replace(/[\u0113\u00EA\u00E8\u00E9\u00EB]/g, 'e')   // ē ê è é ë
      .replace(/[\u012B\u00EE\u00EF]/g, 'i')               // ī î ï
      .replace(/[\u014D\u00F4\u00F6]/g, 'o')               // ō ô ö
      .replace(/[\u016B\u00FB\u00FC]/g, 'u')               // ū û ü
      .replace(/\u1E25/g, 'h')           // ḥ
      .replace(/\u1E33/g, 'k')           // ḳ
      .replace(/\u1E63/g, 's')           // ṣ
      .replace(/\u1E6D/g, 't')           // ṭ
      .replace(/[\u015B\u015D]/g, 's')   // ś ŝ
      .replace(/\s+/g, '');
  }

  /**
   * Aggressive normalization for cross-language matching.
   * Strips Hebrew transliteration artifacts (glottal stops, semivowels)
   * that French proper names typically drop.
   */
  function normalizeCrossLang(s) {
    return normalizeTranslit(s)
      .replace(/[^a-z]/g, '')    // strip anything non-alpha
      .replace(/w/g, '')         // Hebrew waw semivowel (ôwn → ôn)
      .replace(/([aeiou])h([aeiou])/g, '$1$2'); // medial h between vowels (Aharon → aaron)
  }

  // ── Lexicon access (reuse V3 patch's loaded data) ─────────────────

  var _lexiconData = null;
  var _lexiconIndex = null;

  function getLexicon() {
    if (_lexiconData) return Promise.resolve(_lexiconIndex);
    var url = config.hebrewLexiconUrl;
    if (!url) return Promise.reject('no_url');
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (data) {
      _lexiconData = Array.isArray(data) ? data : (data.value || []);
      _lexiconIndex = new Map();
      _lexiconData.forEach(function (entry) {
        if (entry.s) _lexiconIndex.set(entry.s.toUpperCase(), entry);
      });
      return _lexiconIndex;
    });
  }

  /** Search lexicon by concept label — strict match only (no substring) */
  function findByLabelStrict(label) {
    var results = [];
    var labelNorm = normalizeTranslit(label);
    if (labelNorm.length < 2 || !_lexiconData) return results;

    // Only exact transliteration match (basic normalization)
    _lexiconData.forEach(function (entry) {
      if (results.length >= 3) return;
      if (entry.x && normalizeTranslit(entry.x) === labelNorm) {
        results.push(entry);
      }
    });
    return results;
  }

  /** Find Strong entries for a concept using pre-calculated mapping + strict fallback */
  function findStrongForConcept(conceptId, label) {
    var results = [];
    // 1. Use unified hebrew map (concept-hebrew-map.json — richest source)
    if (_hebrewMap && conceptId) {
      var hebrewEntries = _hebrewMap[conceptId];
      if (hebrewEntries && Array.isArray(hebrewEntries) && _lexiconIndex) {
        for (var i = 0; i < hebrewEntries.length && results.length < 8; i++) {
          var strongId = hebrewEntries[i].s || '';
          var entry = _lexiconIndex.get(strongId.toUpperCase());
          if (entry) results.push(entry);
        }
      }
    }
    // 2. Fallback: concept-strong-map.json (transliteration-based)
    if (results.length === 0 && _strongMap && conceptId) {
      var strongNums = _strongMap[conceptId];
      if (strongNums && Array.isArray(strongNums) && _lexiconIndex) {
        for (var i = 0; i < strongNums.length && results.length < 5; i++) {
          var entry = _lexiconIndex.get(strongNums[i].toUpperCase());
          if (entry) results.push(entry);
        }
      }
    }
    // 3. Fallback: strict transliteration match only
    if (results.length === 0 && label) {
      results = findByLabelStrict(label);
    }
    return results;
  }

  // ── Hebrew card rendering ─────────────────────────────────────────

  // Root families loading
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

  // Concordance loading (shared with patch.js via same URL)
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

  // OSHB book → BYM ref badge (reuses patch.js OSHB_BOOK_MAP if available, else inline)
  var OSHB_BOOKS = {
    Gen:'Gn',Exod:'Ex',Lev:'Lv',Num:'Nb',Deut:'Dt',Josh:'Jos',Judg:'Jg',Ruth:'Rt',
    '1Sam':'1Sa','2Sam':'2Sa','1Kgs':'1R','2Kgs':'2R','1Chr':'1Ch','2Chr':'2Ch',
    Ezra:'Esd',Neh:'N\u00e9',Esth:'Est',Job:'Jb',Ps:'Ps',Prov:'Pr',Eccl:'Ec',Song:'Ct',
    Isa:'Es',Jer:'Jr',Lam:'Lm',Ezek:'Ez',Dan:'Dn',Hos:'Os',Joel:'Jl',Amos:'Am',
    Obad:'Ab',Jonah:'Jon',Mic:'Mi',Nah:'Na',Hab:'Ha',Zeph:'So',Hag:'Ag',Zech:'Za',Mal:'Ml'
  };
  // BYM GitLab file numbering (Tanakh order, not Protestant)
  var OSHB_FILES = {
    Gen:'01-Genese',Exod:'02-Exode',Lev:'03-Levitique',Num:'04-Nombres',Deut:'05-Deuteronome',
    Josh:'06-Josue',Judg:'07-Juges',Ruth:'31-Ruth','1Sam':'08-1Samuel','2Sam':'09-2Samuel',
    '1Kgs':'10-1Rois','2Kgs':'11-2Rois','1Chr':'38-1Chroniques','2Chr':'39-2Chroniques',
    Ezra:'36-Esdras',Neh:'37-Nehemie',Esth:'34-Esther',Job:'29-Job',Ps:'27-Psaumes',
    Prov:'28-Proverbes',Eccl:'33-Ecclesiaste',Song:'30-Cantiques',Isa:'12-Esaie',Jer:'13-Jeremie',
    Lam:'32-Lamentations',Ezek:'14-Ezechiel',Dan:'35-Daniel',Hos:'15-Osee',Joel:'16-Joel',
    Amos:'17-Amos',Obad:'18-Abdias',Jonah:'19-Jonas',Mic:'20-Michee',Nah:'21-Nahum',
    Hab:'22-Habakuk',Zeph:'23-Sophonie',Hag:'24-Aggee',Zech:'25-Zacharie',Mal:'26-Malachie'
  };

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

  // strongId (optionnel) permet de surligner le mot dans la vue interlineaire
  // de la bulle verset. bk = cle OSHB (Gen, Exod, Ruth, ...) utilisee pour
  // retrouver le fichier interlineaire cote bible-v3-patch.
  function oshbRefToBadge(ref, shortLabel, strongId) {
    var parts = ref.split('.');
    if (parts.length < 3) return '';
    var bk = parts[0], ch = parts[1], vs = parts[2];
    var fr = OSHB_BOOKS[bk];
    if (!fr) return '';
    var fileBase = OSHB_FILES[bk] || '';
    var code = fileBase.substring(0, 2);
    var label = shortLabel ? (ch + ':' + vs) : (fr + ' ' + ch + ':' + vs);
    return '<span class="fb-ref-badge fb-conc-ref"'
      + ' data-file="' + escapeHtml(fileBase + '.md') + '"'
      + ' data-code="' + escapeHtml(code) + '"'
      + ' data-chapter="' + ch + '"'
      + ' data-verse="' + vs + '"'
      + ' data-bk="' + escapeHtml(bk) + '"'
      + (strongId ? ' data-strong="' + escapeHtml(strongId) + '"' : '')
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

    html += '<div class="fb-conc-summary">';
    for (var g = 0; g < groups.length; g++) {
      var grp = groups[g];
      var bookName = OSHB_BOOK_FR_FULL[grp.key] || grp.key;
      html += '<button class="fb-conc-book-pill" type="button" data-conc-book="' + g + '">'
        + escapeHtml(bookName) + '&nbsp;<span class="fb-conc-book-pill__count">' + grp.refs.length + '</span>'
        + '</button>';
    }
    html += '</div>';

    for (var g = 0; g < groups.length; g++) {
      var grp = groups[g];
      html += '<div class="fb-conc-panel" data-conc-panel="' + g + '" hidden>';
      html += '<div class="fb-conc-panel__refs">';
      for (var r = 0; r < grp.refs.length; r++) {
        html += oshbRefToBadge(grp.refs[r], true, strongId);
      }
      html += '</div></div>';
    }

    html += '</div></div>';
    return html;
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

  // === AUDIO : prononciation via Web Speech API ===
  // Cache des voix + preference he-IL > translitteration (xlit) avec voix fr-FR / en-US
  var _voicesReady = false;
  var _hebrewVoice = null;
  var _fallbackVoice = null;

  function _loadVoices() {
    if (!('speechSynthesis' in window)) return;
    var voices = speechSynthesis.getVoices() || [];
    if (!voices.length) return;
    _voicesReady = true;
    _hebrewVoice = null;
    for (var i = 0; i < voices.length; i++) {
      var lv = (voices[i].lang || '').toLowerCase();
      if (lv.indexOf('he') === 0 || lv === 'iw' || lv.indexOf('iw-') === 0) {
        _hebrewVoice = voices[i];
        break;
      }
    }
    // Fallback : fr-FR, sinon en-US, sinon la default
    _fallbackVoice = null;
    for (var j = 0; j < voices.length; j++) {
      var lv2 = (voices[j].lang || '').toLowerCase();
      if (lv2.indexOf('fr') === 0) { _fallbackVoice = voices[j]; break; }
    }
    if (!_fallbackVoice) {
      for (var k = 0; k < voices.length; k++) {
        var lv3 = (voices[k].lang || '').toLowerCase();
        if (lv3.indexOf('en') === 0) { _fallbackVoice = voices[k]; break; }
      }
    }
    if (!_fallbackVoice && voices[0]) _fallbackVoice = voices[0];
  }

  if ('speechSynthesis' in window) {
    _loadVoices();
    // Chrome charge les voix de facon asynchrone : re-essayer sur voiceschanged
    if (typeof speechSynthesis.addEventListener === 'function') {
      speechSynthesis.addEventListener('voiceschanged', _loadVoices);
    } else {
      speechSynthesis.onvoiceschanged = _loadVoices;
    }
  }

  function pronounceWord(hebText, xlitText, btn) {
    if (!('speechSynthesis' in window)) {
      if (btn) btn.setAttribute('title', 'Synth\u00e8se vocale non support\u00e9e par ce navigateur');
      return;
    }
    if (!_voicesReady) _loadVoices();

    // Strategie : si voix hebreu dispo -> heb direct
    // Sinon -> translitteration avec voix fr-FR / en-US (plus fidele qu'hebreu lu en fr)
    var useHeb = !!_hebrewVoice && hebText;
    var text = useHeb ? hebText : (xlitText || hebText || '');
    if (!text) return;

    try {
      speechSynthesis.cancel();
      // Petit delai pour eviter bug Chrome cancel + speak race
      setTimeout(function () {
        var utt = new SpeechSynthesisUtterance(text);
        if (useHeb) {
          utt.voice = _hebrewVoice;
          utt.lang = _hebrewVoice.lang || 'he-IL';
          utt.rate = 0.75;
        } else if (_fallbackVoice) {
          utt.voice = _fallbackVoice;
          utt.lang = _fallbackVoice.lang || 'fr-FR';
          utt.rate = 0.85;
        } else {
          utt.lang = 'fr-FR';
          utt.rate = 0.85;
        }
        utt.onend = function () { if (btn) btn.classList.remove('is-playing'); };
        utt.onerror = function () { if (btn) btn.classList.remove('is-playing'); };
        speechSynthesis.speak(utt);
      }, 60);
    } catch (err) {
      if (btn) btn.classList.remove('is-playing');
    }
  }

  // Handler document-level pour boutons audio
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.fb-hebrew-card__audio');
    if (!btn) return;
    e.preventDefault();
    var heb  = btn.getAttribute('data-text') || '';
    var xlit = btn.getAttribute('data-xlit') || '';
    btn.classList.add('is-playing');
    pronounceWord(heb, xlit, btn);
    // Retire le feedback visuel apres 2s max (au cas ou onend ne fire pas)
    setTimeout(function () { btn.classList.remove('is-playing'); }, 2500);
  });

  // === HELPERS LEXIQUE HEBREU BIBLIQUE (tiers T1-T7) ===

  // OSIS -> BYM book info {file, code} (code numerique 2 chiffres, ordre BYM)
  // Ordre BYM : Torah 01-05, Prophetes 06-26, Ecrits 27-39
  var OSIS_TO_BYM_BOOK = {
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

  // Parse un osisRef (e.g. "Exod.3.12" ou "Exod.3.12-Exod.3.15") en objet compatible verse-bubble
  function parseBymRef(osisRef) {
    if (!osisRef || typeof osisRef !== 'string') return null;
    var parts = osisRef.split('-');
    var m1 = /^(\w+)\.(\d+)\.(\d+)$/.exec(parts[0]);
    if (!m1) return null;
    var book = OSIS_TO_BYM_BOOK[m1[1]];
    if (!book) return null;
    var out = {
      file: book.code + '-' + book.file + '.md',
      code: book.code,
      chapter: parseInt(m1[2], 10),
      verse: parseInt(m1[3], 10),
      verseEnd: null
    };
    // Range : prendre verseEnd si meme book/chapter
    if (parts.length > 1) {
      var m2 = /^(\w+)\.(\d+)\.(\d+)$/.exec(parts[1]);
      if (m2 && m2[1] === m1[1] && m2[2] === m1[2]) {
        out.verseEnd = parseInt(m2[3], 10);
      }
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
  function osterwaldRef(osisRef) {
    if (!osisRef || typeof osisRef !== 'string') return '';
    var parts = osisRef.split('-');
    function parseOne(s) {
      var m = /^(\w+)\.(\d+)\.(\d+)$/.exec(s);
      return m ? { book: m[1], chap: m[2], verse: m[3] } : null;
    }
    var a = parseOne(parts[0]);
    if (!a) return osisRef;
    var bookA = OSTERWALD_BOOKS[a.book] || a.book;
    if (parts.length === 1) return bookA + ' ' + a.chap + ':' + a.verse;
    var b = parseOne(parts[1]);
    if (!b) return bookA + ' ' + a.chap + ':' + a.verse;
    if (a.book === b.book && a.chap === b.chap) return bookA + ' ' + a.chap + ':' + a.verse + '-' + b.verse;
    if (a.book === b.book) return bookA + ' ' + a.chap + ':' + a.verse + ' \u2013 ' + b.chap + ':' + b.verse;
    var bookB = OSTERWALD_BOOKS[b.book] || b.book;
    return bookA + ' ' + a.chap + ':' + a.verse + ' \u2013 ' + bookB + ' ' + b.chap + ':' + b.verse;
  }
  // Wrap Hebrew runs with dir="rtl" span pour isoler bidi dans texte FR mixte
  function wrapHebrewInline(escapedText) {
    return escapedText.replace(/[\u0590-\u05FF]+(?:\s+[\u0590-\u05FF]+)*/g, function (m) {
      return '<span class="fb-inline-he" dir="rtl">' + m + '</span>';
    });
  }
  // Escape HTML + wrap runs hebreux (pour textes mixtes FR/HE inline)
  function escapeHtmlHe(text) {
    return wrapHebrewInline(escapeHtml(text));
  }
  function strongLinkify(text) {
    var html = wrapHebrewInline(escapeHtml(text));
    return html.replace(/\b(\d{1,4})\b/g, function (m, num) {
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
      subHtml = '<ol class="fb-hebrew-card__sense-sublist">' + s.c.map(renderSenseItem).join('') + '</ol>';
    }
    return '<li' + nAttr + '>' + def + subHtml + '</li>';
  }
  function renderSensesT5(entry) {
    var senses = entry.se;
    if (!Array.isArray(senses) || senses.length === 0) {
      if (Array.isArray(entry.bd) && entry.bd.length > 0) {
        return '<div class="fb-hebrew-card__senses-block">' +
          '<div class="fb-hebrew-card__senses-title">Sens et emplois</div>' +
          '<div class="fb-hebrew-card__stem-group">' +
          '<span class="fb-hebrew-card__stem-label" title="Usages principaux">Usages</span>' +
          '<ol class="fb-hebrew-card__sense-list">' +
          entry.bd.map(function (d) { return '<li>' + escapeHtmlHe(d) + '</li>'; }).join('') +
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
      }).join('') + '</div>';
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
          // Span compatible avec le handler verse-bubble de bible-v3-patch.js
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
      parts.join(' ') + '</div>';
  }

  function renderHebrewCard(entry, concRefs, rootData) {
    var concHtml = buildConcordanceHtml(entry.s, concRefs);

    // T1 : Identite (POS BDB precis si dispo via bp, sinon p)
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

    // T4 : Bouton expand vers df (BDB complete), fallback d long
    var expandHtml = (function () {
      var shortD = entry.d || '';
      var fullD = (entry.df && entry.df !== shortD) ? entry.df : (shortD.length > 120 ? shortD : '');
      if (!fullD) return '';
      return '<div class="fb-hebrew-card__def fb-hebrew-card__def--full" hidden>' + escapeHtmlHe(fullD) + '</div>' +
        '<button class="fb-hebrew-card__expand" type="button">D\u00e9finition compl\u00e8te BDB \u2192</button>';
    })();

    return '<div class="fb-hebrew-card">' +
      '<div class="fb-hebrew-card__head">' +
        '<span class="fb-hebrew-card__strong">' + escapeHtml(entry.s) + '</span>' +
        posHtml +
        rootPill +
      '</div>' +
      '<div class="fb-hebrew-card__hebrew" dir="rtl">' + escapeHtml(entry.h || '') +
        (entry.h ? ' <button class="fb-hebrew-card__audio" type="button" data-text="' + escapeHtml(entry.h) + '" data-xlit="' + escapeHtml(entry.x || '') + '" data-lang="he-IL" title="\u00c9couter la prononciation" aria-label="\u00c9couter la prononciation">\ud83d\udd0a</button>' : '') +
      '</div>' +
      (entry.x ? '<div class="fb-hebrew-card__translit">' + escapeHtml(entry.x) + '</div>' : '') +
      (entry.pr ? '<div class="fb-hebrew-card__pron">' + escapeHtml(entry.pr) + '</div>' : '') +
      '<div class="fb-hebrew-card__def fb-hebrew-card__def--short">' + escapeHtmlHe(truncate(entry.d || '', 120)) + '</div>' +
      expandHtml +
      renderSensesT5(entry) +
      renderBdbRefsT6(entry.br) +
      renderEtymT7(entry.et, entry.tw) +
      concHtml +
    '</div>';
  }

  function insertHebrewSidebar(conceptBody, cards) {
    var wrapper = document.createElement('div');
    wrapper.className = 'fb-hebrew-sidebar';
    wrapper.innerHTML =
      '<h3 class="fb-hebrew-sidebar__title">Lexique h\u00e9breu</h3>' +
      cards.join('');

    // Greek lexicon placeholder
    var greekPlaceholder = document.createElement('div');
    greekPlaceholder.className = 'fb-greek-placeholder';
    greekPlaceholder.innerHTML = '<div class="fb-greek-placeholder__icon">\u0391</div>'
      + '<div class="fb-greek-placeholder__label">Lexique grec (Thayer)</div>'
      + '<div class="fb-greek-placeholder__note">Bientôt disponible</div>';
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

    // Wire BDB refs expand buttons
    wrapper.querySelectorAll('.fb-hebrew-card__bdb-refs-expand').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var extra = btn.parentNode.querySelector('.fb-hebrew-card__bdb-refs-more');
        if (extra) { extra.hidden = false; btn.hidden = true; }
      });
    });

    // Wire root pill clicks — open root bubble
    wrapper.querySelectorAll('.fb-hebrew-card__root-pill').forEach(function (pill) {
      pill.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        showRootBubble(pill);
      });
    });
  }

  // ── Root Bubble ───────────────────────────────────────────────────

  function closeRootBubble() {
    var existing = document.querySelector('.fb-root-bubble');
    if (existing) existing.remove();
    var overlay = document.querySelector('.fb-root-bubble__overlay');
    if (overlay) overlay.remove();
  }

  function showRootBubble(pill) {
    closeRootBubble();
    // Also close any verse bubble
    var vb = document.querySelector('.fb-verse-bubble');
    if (vb) vb.remove();

    var rootHebrew = pill.getAttribute('data-root') || '';
    var strongId = pill.getAttribute('data-strong') || '';
    var rootData = _rootFamilies ? _rootFamilies[strongId] : null;
    if (!rootData || !rootData.f) {
      // Fallback: navigate directly to the root tree if bubble data unavailable
      if (rootHebrew) {
        window.location.href = '/lexique-hebreu-biblique/#racine=' + encodeURIComponent(rootHebrew);
      }
      return;
    }

    // Build members list with occurrences, sorted by frequency
    var members = [];
    // Add root entry itself
    var rootEntry = _lexiconIndex ? _lexiconIndex.get(strongId.toUpperCase()) : null;
    if (rootEntry) {
      members.push({
        s: strongId,
        h: rootEntry.h || '',
        x: rootEntry.x || '',
        g: (rootEntry.g && rootEntry.g[0]) || '',
        o: _concordance && _concordance[strongId] ? _concordance[strongId].length : 0
      });
    }
    // Add siblings
    for (var i = 0; i < rootData.f.length; i++) {
      var sib = rootData.f[i];
      var sibOcc = _concordance && _concordance[sib.s] ? _concordance[sib.s].length : 0;
      members.push({ s: sib.s, h: sib.h || '', x: sib.x || '', g: sib.g || '', o: sibOcc });
    }
    // Sort by occurrences descending
    members.sort(function (a, b) { return (b.o || 0) - (a.o || 0); });

    // Take top 5
    var top = members.slice(0, 5);
    var totalOcc = 0;
    for (var j = 0; j < members.length; j++) totalOcc += members[j].o || 0;

    var isMobile = window.innerWidth < (config.mobileBreakpoint || 900);
    var arbreHref = '/lexique-hebreu-biblique/#racine=' + encodeURIComponent(rootHebrew);

    // Build HTML
    var bodyHtml = '';
    for (var k = 0; k < top.length; k++) {
      var m = top[k];
      bodyHtml += '<div class="fb-root-bubble__member">'
        + '<span class="fb-root-bubble__hebrew" dir="rtl">' + escapeHtml(m.h) + '</span>'
        + (m.x ? '<span class="fb-root-bubble__translit">' + escapeHtml(m.x) + '</span>' : '')
        + '<span class="fb-root-bubble__gloss">' + escapeHtml(m.g || '\u2014') + '</span>'
        + '<span class="fb-root-bubble__occ">' + (m.o || 0) + '</span>'
        + '</div>';
    }
    if (members.length > 5) {
      bodyHtml += '<div class="fb-root-bubble__more">+ ' + (members.length - 5) + ' autres mots</div>';
    }

    var bubble = document.createElement('div');
    bubble.className = 'fb-verse-bubble fb-root-bubble' + (isMobile ? ' fb-verse-bubble--sheet' : '');
    bubble.setAttribute('role', 'dialog');
    // Root parent info: translit + primary gloss from the root entry
    var rootTranslit = rootEntry ? (rootEntry.x || '') : '';
    var rootGloss = rootEntry ? ((rootEntry.g && rootEntry.g[0]) || '') : '';

    bubble.innerHTML =
      '<div class="fb-verse-bubble__header">'
        + '<div class="fb-root-bubble__root-info">'
          + '<span class="fb-root-bubble__root" dir="rtl">' + escapeHtml(rootHebrew) + '</span>'
          + (rootTranslit ? '<span class="fb-root-bubble__root-translit">' + escapeHtml(rootTranslit) + '</span>' : '')
          + (rootGloss ? '<span class="fb-root-bubble__root-gloss">' + escapeHtml(rootGloss) + '</span>' : '')
        + '</div>'
        + '<span class="fb-root-bubble__stats">' + members.length + ' mots \u00b7 ' + totalOcc + ' occ.</span>'
        + '<button class="fb-verse-bubble__close" type="button" aria-label="Fermer">&times;</button>'
      + '</div>'
      + '<div class="fb-verse-bubble__body">' + bodyHtml + '</div>'
      + '<div class="fb-verse-bubble__footer">'
        + '<a href="' + escapeHtml(arbreHref) + '" target="_blank" rel="noopener">Voir l\'arbre complet \u2192</a>'
      + '</div>';

    // Position
    if (isMobile) {
      var overlay = document.createElement('div');
      overlay.className = 'fb-verse-bubble__overlay fb-root-bubble__overlay';
      overlay.addEventListener('click', closeRootBubble);
      document.body.appendChild(overlay);
    } else {
      var anchorRect = pill.getBoundingClientRect();
      var adminBar = document.getElementById('wpadminbar');
      var barH = adminBar ? adminBar.offsetHeight : 0;
      var left = Math.max(8, Math.min(anchorRect.left, window.innerWidth - 350));
      var spaceBelow = window.innerHeight - anchorRect.bottom;
      var topPos;
      if (spaceBelow > 280) {
        topPos = anchorRect.bottom + 8;
      } else {
        topPos = Math.max(barH + 8, anchorRect.top - 300);
      }
      topPos = Math.max(barH + 8, Math.min(topPos, window.innerHeight - 200));
      bubble.style.left = left + 'px';
      bubble.style.top = topPos + 'px';
    }

    document.body.appendChild(bubble);

    // Close button
    bubble.querySelector('.fb-verse-bubble__close').addEventListener('click', closeRootBubble);

    // Close on outside click
    setTimeout(function () {
      document.addEventListener('click', function handler(e) {
        if (!e.target.closest('.fb-root-bubble') && !e.target.closest('.fb-hebrew-card__root-pill')) {
          closeRootBubble();
          document.removeEventListener('click', handler);
        }
      });
    }, 100);
  }

  // ── HOTFIX 1: Hebrew sidebar with pre-calculated mapping ──────────

  function getConceptIdFromUrl() {
    var path = window.location.pathname || '';
    var base = (config.seoBaseUrl || '/dictionnaire-biblique/').replace(/^https?:\/\/[^\/]+/, '');
    if (path.indexOf(base) !== 0) return '';
    var slug = path.slice(base.length).replace(/\/$/, '');
    if (!slug) return '';
    // The concept_id is typically the slug or resolved by the app
    // Try to read from the app's state if available
    var appEl = document.querySelector(APP_SEL);
    if (appEl && appEl.__bibleApp && appEl.__bibleApp.state) {
      return appEl.__bibleApp.state.activeConceptId || '';
    }
    // Fallback: use slug as-is (works for most concepts)
    return decodeURIComponent(slug);
  }

  function hotfixHebrewSidebar() {
    var conceptBody = document.querySelector(CONCEPT_BODY_SEL);
    if (!conceptBody) return;
    // Skip if already injected (by V3 patch or previous hotfix run)
    if (conceptBody.getAttribute('data-hebrew-injected')) return;

    // Check if V3 patch already found Strong numbers (sidebar present)
    if (conceptBody.querySelector('.fb-hebrew-sidebar')) return;

    var titleEl = document.querySelector(CONCEPT_HERO_SEL + ' .fb-concept-title');
    if (!titleEl) return;

    var label = titleEl.textContent.trim();
    var conceptId = getConceptIdFromUrl();
    conceptBody.setAttribute('data-hebrew-injected', 'hotfix');

    Promise.all([getLexicon(), loadStrongMap(), loadConcordance(), loadRootFamilies(), loadHebrewMap()]).then(function (results) {
      var lexIdx = results[0];
      var conc = results[2] || {};
      var roots = results[3] || {};
      if (!lexIdx || lexIdx.size === 0) {
        console.warn('[hotfix-hebrew] Lexicon index empty — sidebar skipped for', conceptId);
        return;
      }
      var matches = findStrongForConcept(conceptId, label);
      if (matches.length === 0) {
        console.warn('[hotfix-hebrew] No matches for', conceptId, '(label:', label, ') — hebrewMap entries:', (_hebrewMap && _hebrewMap[conceptId]) ? _hebrewMap[conceptId].length : 0);
        return;
      }
      var cards = matches.map(function (entry) {
        return renderHebrewCard(entry, conc[entry.s] || [], roots[entry.s] || null);
      });
      insertHebrewSidebar(conceptBody, cards);
    }).catch(function (err) {
      console.warn('[hotfix-hebrew] Promise error for', conceptId, ':', err);
    });
  }

  // ── HOTFIX 2: Hebrew in concept hero ──────────────────────────────

  function injectHeroHebrew() {
    var hero = document.querySelector(CONCEPT_HERO_SEL);
    if (!hero || hero.getAttribute('data-hebrew-hero')) return;
    hero.setAttribute('data-hebrew-hero', '1');

    var conceptId = getConceptIdFromUrl();
    if (!conceptId) return;

    loadHebrewMap().then(function () {
      var allEntries = (_hebrewMap && _hebrewMap[conceptId]) || [];
      if (allEntries.length === 0) return;

      var heading = hero.querySelector('.fb-concept-heading');
      var meta = hero.querySelector('.fb-concept-meta');

      if (allEntries.length === 1) {
        // Single Strong → show Hebrew + transliteration inline in hero title
        var e = allEntries[0];
        if (heading && e.h) {
          var hebrewSpan = document.createElement('span');
          hebrewSpan.className = 'fb-hero-hebrew';
          hebrewSpan.setAttribute('dir', 'rtl');
          hebrewSpan.textContent = e.h;
          heading.appendChild(hebrewSpan);

          if (e.x) {
            var translitSpan = document.createElement('span');
            translitSpan.className = 'fb-hero-translit';
            translitSpan.textContent = e.x;
            heading.appendChild(translitSpan);
          }
        }
        // Also add Strong badge in meta
        if (meta) {
          var badge = document.createElement('span');
          badge.className = 'fb-pill fb-pill--strong';
          badge.textContent = e.s;
          meta.appendChild(badge);
        }
      } else {
        // Multiple Strongs → show count badge in meta
        if (meta) {
          var badge = document.createElement('span');
          badge.className = 'fb-pill fb-pill--strong-multi';
          badge.textContent = allEntries.length + ' termes h\u00e9breux';
          meta.appendChild(badge);
        }
      }
    }).catch(function () { /* silent */ });
  }

  // ── Orchestration ─────────────────────────────────────────────────

  function applyHotfixes() {
    hotfixHebrewSidebar();
    injectHeroHebrew();
  }

  function init() {
    var app = document.querySelector(APP_SEL);
    if (!app) {
      if (document.readyState !== 'complete') {
        window.addEventListener('load', init);
      }
      return;
    }

    // Wait a bit for V3 patch to finish its initial run
    setTimeout(function () {
      applyHotfixes();

      // Re-apply on hash change (new concept loaded)
      window.addEventListener('hashchange', function () {
        setTimeout(applyHotfixes, 500);
      });

      // Re-apply on DOM changes
      var timer = null;
      var observer = new MutationObserver(function () {
        if (timer) clearTimeout(timer);
        timer = setTimeout(applyHotfixes, 300);
      });
      observer.observe(app, { childList: true, subtree: true });
    }, 500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ── Exports for bible-interlineaire-app.js (et autres modules externes) ──
  // Expose renderHebrewCard + helpers pour reutilisation sans dupliquer le code.
  window.FIGUIER_HEBREW_CARD = {
    render: renderHebrewCard,
    wrapHebrewInline: wrapHebrewInline,
    escapeHtml: escapeHtml,
    escapeHtmlHe: escapeHtmlHe,
    truncate: truncate,
    buildConcordanceHtml: buildConcordanceHtml,
    renderSensesT5: renderSensesT5,
    renderBdbRefsT6: renderBdbRefsT6,
    renderEtymT7: renderEtymT7,
  };

})();
