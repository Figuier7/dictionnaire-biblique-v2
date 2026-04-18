/**
 * bible-interlineaire-app.js - Bible interlineaire AT (hebreu+FR)
 *
 * 23 213 versets · 306 785 mots · 39 livres du Tanakh
 * Donnees : uploads/dictionnaires/interlinear/NN-BookOsis.json (chunk par livre)
 *
 * 6 lignes par mot :
 *   1. Hebreu pointe (RTL)
 *   2. Translitteration (italique)
 *   3. Numero Strong (lien vers lexique)
 *   4. Morphologie decodee FR
 *   5. Gloss FR mot-a-mot
 *   6. Traduction BYM (ligne entiere sous le verset)
 *
 * Clic sur un mot -> sidebar avec fiche lexique hebreu 7 tiers
 * (reutilise window.FIGUIER_HEBREW_CARD.render depuis bible-v3-hotfix.js)
 *
 * Depend de figuierInterlineaireConfig injecte par PHP.
 */
(function () {
  'use strict';

  var CFG = window.figuierInterlineaireConfig || {};
  var interlinearBaseUrl = CFG.interlinearBaseUrl || '';
  var lexiconUrl = CFG.lexiconUrl || '';
  var posDescUrl = CFG.posDescUrl || '';
  var concordanceUrl = CFG.concordanceUrl || '';
  var rootFamiliesUrl = CFG.rootFamiliesUrl || '';
  var strongConceptsUrl = CFG.strongConceptsUrl || '';
  var conceptBaseUrl = CFG.conceptBaseUrl || '/dictionnaire-biblique/';
  var bymProxyUrl = CFG.bymProxyUrl || '';
  var bymReaderBase = CFG.bymReaderBase || 'https://www.bibledeyehoshouahamashiah.org/lire.html';

  var root = document.getElementById('bible-interlineaire-app');
  if (!root) return;

  // ── Metadonnees des 39 livres AT ──
  // Ordre du Tanakh : Torah (5) / Nevi'im (8 livres, compte\u0301s en 21) / Ketouvim (11, compte\u0301s en 13)
  // Champ bym = nom he\u0301breu translitte\u0301re\u0301 selon la convention Bible de Yehoshoua HaMashiah
  // Champ group = 'torah' | 'neviim' | 'ketuvim'
  // Champ subgroup = sous-groupe (optionnel, pour affichage nuance\u0301)
  var BOOKS = [
    // \u2500\u2500 Torah (La Loi) \u2500\u2500
    { osis:'Gen',  fr:'Gen\u00e8se',       bym:'Bereshit',         code:'01', chapters:50, slug:'genese',        bymFile:'01-Genese',  osterwald:'Gn',    group:'torah' },
    { osis:'Exod', fr:'Exode',             bym:'Shemot',           code:'02', chapters:40, slug:'exode',         bymFile:'02-Exode', osterwald:'Ex',    group:'torah' },
    { osis:'Lev',  fr:'L\u00e9vitique',    bym:'Vayiqra',          code:'03', chapters:27, slug:'levitique',     bymFile:'03-Levitique',  osterwald:'Lv',    group:'torah' },
    { osis:'Num',  fr:'Nombres',           bym:'Bamidbar',         code:'04', chapters:36, slug:'nombres',       bymFile:'04-Nombres',  osterwald:'Nb',    group:'torah' },
    { osis:'Deut', fr:'Deut\u00e9ronome',  bym:'Devarim',          code:'05', chapters:34, slug:'deuteronome',   bymFile:'05-Deuteronome', osterwald:'Dt',    group:'torah' },

    // \u2500\u2500 Nevi'im (Les Prophe\u0300tes) \u2500\u2500
    // Premiers prophe\u0300tes (historiques)
    { osis:'Josh', fr:'Josu\u00e9',        bym:'Y\u00e9hoshoua',   code:'06', chapters:24, slug:'josue',         bymFile:'06-Josue', osterwald:'Jos',   group:'neviim', subgroup:'nev_first' },
    { osis:'Judg', fr:'Juges',             bym:'Shoftim',          code:'07', chapters:21, slug:'juges',         bymFile:'07-Juges', osterwald:'Jg',    group:'neviim', subgroup:'nev_first' },
    { osis:'1Sam', fr:'1 Samuel',          bym:'1 Shemou\u00e9l',  code:'09', chapters:31, slug:'1-samuel',      bymFile:'08-1Samuel', osterwald:'1 S',   group:'neviim', subgroup:'nev_first' },
    { osis:'2Sam', fr:'2 Samuel',          bym:'2 Shemou\u00e9l',  code:'10', chapters:24, slug:'2-samuel',      bymFile:'09-2Samuel', osterwald:'2 S',   group:'neviim', subgroup:'nev_first' },
    { osis:'1Kgs', fr:'1 Rois',            bym:'1 Melakhim',       code:'11', chapters:22, slug:'1-rois',        bymFile:'10-1Rois', osterwald:'1 R',   group:'neviim', subgroup:'nev_first' },
    { osis:'2Kgs', fr:'2 Rois',            bym:'2 Melakhim',       code:'12', chapters:25, slug:'2-rois',        bymFile:'11-2Rois', osterwald:'2 R',   group:'neviim', subgroup:'nev_first' },

    // Derniers prophe\u0300tes (majeurs)
    { osis:'Isa',  fr:'\u00c9sa\u00efe',   bym:'Yesha\u2019yah',   code:'23', chapters:66, slug:'esaie',         bymFile:'12-Esaie',  osterwald:'\u00c9s', group:'neviim', subgroup:'nev_last' },
    { osis:'Jer',  fr:'J\u00e9r\u00e9mie', bym:'Yirmeyah',         code:'24', chapters:52, slug:'jeremie',       bymFile:'13-Jeremie',  osterwald:'Jr',    group:'neviim', subgroup:'nev_last' },
    { osis:'Ezek', fr:'\u00c9z\u00e9chiel',bym:'Yehezkel',         code:'26', chapters:48, slug:'ezechiel',      bymFile:'14-Ezechiel', osterwald:'\u00c9z', group:'neviim', subgroup:'nev_last' },

    // Douze petits prophe\u0300tes (Terei Asar)
    { osis:'Hos',  fr:'Os\u00e9e',         bym:'Hoshea',           code:'28', chapters:14, slug:'osee',          bymFile:'15-Osee',  osterwald:'Os',    group:'neviim', subgroup:'nev_twelve' },
    { osis:'Joel', fr:'Jo\u00ebl',         bym:'Yoel',             code:'29', chapters:3,  slug:'joel',          bymFile:'16-Joel', osterwald:'Jl',    group:'neviim', subgroup:'nev_twelve' },
    { osis:'Amos', fr:'Amos',              bym:'Amowc',            code:'30', chapters:9,  slug:'amos',          bymFile:'17-Amos', osterwald:'Am',    group:'neviim', subgroup:'nev_twelve' },
    { osis:'Obad', fr:'Abdias',            bym:'Obadyah',          code:'31', chapters:1,  slug:'abdias',        bymFile:'18-Abdias', osterwald:'Ab',    group:'neviim', subgroup:'nev_twelve' },
    { osis:'Jonah',fr:'Jonas',             bym:'Yonah',            code:'32', chapters:4,  slug:'jonas',         bymFile:'19-Jonas',osterwald:'Jon',   group:'neviim', subgroup:'nev_twelve' },
    { osis:'Mic',  fr:'Mich\u00e9e',       bym:'Miykayah',         code:'33', chapters:7,  slug:'michee',        bymFile:'20-Michee',  osterwald:'Mi',    group:'neviim', subgroup:'nev_twelve' },
    { osis:'Nah',  fr:'Nahum',             bym:'Nahoum',           code:'34', chapters:3,  slug:'nahoum',        bymFile:'21-Nahum',  osterwald:'Na',    group:'neviim', subgroup:'nev_twelve' },
    { osis:'Hab',  fr:'Habaquq',           bym:'Chabaqquwq',       code:'35', chapters:3,  slug:'habacuc',       bymFile:'22-Habakuk',  osterwald:'Ha',    group:'neviim', subgroup:'nev_twelve' },
    { osis:'Zeph', fr:'Sophonie',          bym:'Tsephanyah',       code:'36', chapters:3,  slug:'sophonie',      bymFile:'23-Sophonie', osterwald:'So',    group:'neviim', subgroup:'nev_twelve' },
    { osis:'Hag',  fr:'Agg\u00e9e',        bym:'Chaggay',          code:'37', chapters:2,  slug:'aggee',         bymFile:'24-Aggee',  osterwald:'Ag',    group:'neviim', subgroup:'nev_twelve' },
    { osis:'Zech', fr:'Zacharie',          bym:'Zekaryah',         code:'38', chapters:14, slug:'zacharie',      bymFile:'25-Zacharie', osterwald:'Za',    group:'neviim', subgroup:'nev_twelve' },
    { osis:'Mal',  fr:'Malachie',          bym:'Malakhi',          code:'39', chapters:4,  slug:'malachie',      bymFile:'26-Malachie',  osterwald:'Ml',    group:'neviim', subgroup:'nev_twelve' },

    // \u2500\u2500 Ketouvim (Les \u00c9crits) \u2500\u2500
    { osis:'Ps',   fr:'Psaumes',           bym:'Tehilim',          code:'19', chapters:150,slug:'psaumes',       bymFile:'27-Psaumes',   osterwald:'Ps',    group:'ketuvim' },
    { osis:'Prov', fr:'Proverbes',         bym:'Mishlei',          code:'20', chapters:31, slug:'proverbes',     bymFile:'28-Proverbes', osterwald:'Pr',    group:'ketuvim' },
    { osis:'Job',  fr:'Job',               bym:'Iyov',             code:'18', chapters:42, slug:'job',           bymFile:'29-Job',  osterwald:'Jb',    group:'ketuvim' },

    // Megilot (5 rouleaux)
    { osis:'Song', fr:'Cantique',          bym:'Shir Hashirim',    code:'22', chapters:8,  slug:'cantique',      bymFile:'30-Cantiques', osterwald:'Ct',    group:'ketuvim', subgroup:'megilot' },
    { osis:'Ruth', fr:'Ruth',              bym:'Routh',            code:'08', chapters:4,  slug:'ruth',          bymFile:'31-Ruth', osterwald:'Rt',    group:'ketuvim', subgroup:'megilot' },
    { osis:'Lam',  fr:'Lamentations',      bym:'Eikha',            code:'25', chapters:5,  slug:'lamentations',  bymFile:'32-Lamentations',  osterwald:'Lm',    group:'ketuvim', subgroup:'megilot' },
    { osis:'Eccl', fr:'Eccl\u00e9siaste',  bym:'Qohelet',          code:'21', chapters:12, slug:'ecclesiaste',   bymFile:'33-Ecclesiaste', osterwald:'Ec',    group:'ketuvim', subgroup:'megilot' },
    { osis:'Esth', fr:'Esther',            bym:'Meguila Esther',   code:'17', chapters:10, slug:'esther',        bymFile:'34-Esther', osterwald:'Est',   group:'ketuvim', subgroup:'megilot' },

    // Derniers \u00e9crits
    { osis:'Dan',  fr:'Daniel',            bym:'Daniye\u2019l',    code:'27', chapters:12, slug:'daniel',        bymFile:'35-Daniel',  osterwald:'Dn',    group:'ketuvim' },
    { osis:'Ezra', fr:'Esdras',            bym:'Ezra',             code:'15', chapters:10, slug:'esdras',        bymFile:'36-Esdras', osterwald:'Esd',   group:'ketuvim' },
    { osis:'Neh',  fr:'N\u00e9h\u00e9mie', bym:'Nehemyah',         code:'16', chapters:13, slug:'nehemie',       bymFile:'37-Nehemie',  osterwald:'N\u00e9',  group:'ketuvim' },
    { osis:'1Chr', fr:'1 Chroniques',      bym:'1 Hayyamim dibre', code:'13', chapters:29, slug:'1-chroniques',  bymFile:'38-1Chroniques', osterwald:'1 Ch',  group:'ketuvim' },
    { osis:'2Chr', fr:'2 Chroniques',      bym:'2 Hayyamim dibre', code:'14', chapters:36, slug:'2-chroniques',  bymFile:'39-2Chroniques', osterwald:'2 Ch',  group:'ketuvim' }
  ];

  // Me\u0301ta-donne\u0301es des groupes pour affichage
  var TANAKH_GROUPS = [
    { key:'torah',   title:'Torah',      subtitle:'La Loi',            description:'Les cinq livres de Mo\u00efse' },
    { key:'neviim',  title:'Nevi\u2019im', subtitle:'Les Prophe\u0300tes', description:'Livres historiques et oracles prophe\u0301tiques' },
    { key:'ketuvim', title:'Ketouvim',   subtitle:'Les \u00c9crits',   description:'Poe\u0301sie, sagesse, rouleaux liturgiques et livres tardifs' }
  ];

  var BOOK_BY_SLUG = {};
  var BOOK_BY_OSIS = {};
  BOOKS.forEach(function (b) { BOOK_BY_SLUG[b.slug] = b; BOOK_BY_OSIS[b.osis] = b; });

  // Helper : nom d'affichage d'un livre (ex: "Bereshit (Gene\u0300se)")
  function bookDisplayName(b) {
    if (!b) return '';
    if (b.bym && b.bym !== b.fr) return b.bym + ' (' + b.fr + ')';
    return b.fr;
  }

  // ── State ──
  var state = {
    book: null,          // current book object
    chapter: 1,          // current chapter number
    bookData: null,      // { book, code, name_fr, chapters: {1: {1: [words...]}} }
    focusVerse: null,    // verse to scroll to
  };
  var _lexicon = null;           // full Strong lexicon array
  var _lexiconIndex = {};        // Strong (H####) -> entry
  var _posDesc = {};             // POS code -> FR description
  var _concordance = {};         // Strong -> [refs OSIS]
  var _rootFamilies = {};        // Strong -> { r, f[] }
  var _strongConcepts = {};      // Strong -> [ {slug,l,c,u}, ... ]
  var _bymCache = {};            // 'NN-File' -> parsed { chap: { verse: 'text' } }
  var _bymLoading = {};          // 'NN-File' -> Promise

  // ── Utils ──
  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }
  function el(tag, attrs, children) {
    var e = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === 'class') e.className = attrs[k];
      else if (k === 'html') e.innerHTML = attrs[k];
      else if (k === 'text') e.textContent = attrs[k];
      else if (k === 'on') for (var ev in attrs[k]) e.addEventListener(ev, attrs[k][ev]);
      else e.setAttribute(k, attrs[k]);
    }
    if (children) children.forEach(function (c) {
      if (c == null) return;
      if (typeof c === 'string') e.appendChild(document.createTextNode(c));
      else e.appendChild(c);
    });
    return e;
  }

  // ── Morphologie : decoder HR/Ncfsa -> "Preposition + Nom fem. sing. absolu" ──
  function decodeMorph(morph) {
    if (!morph) return '';
    // Strip leading 'H' (hebrew language tag) or 'A' (aramaic)
    var raw = String(morph);
    var lang = raw.charAt(0);
    var payload = raw;
    if (lang === 'H' || lang === 'A') payload = raw.slice(1);

    // Split by '/' for prefixes/segments
    var segments = payload.split('/');
    var decoded = segments.map(decodeSegment).filter(function (d) { return d; });
    return decoded.join(' + ');
  }

  function decodeSegment(seg) {
    if (!seg) return '';
    // OSHB morph format: part-of-speech letter, then subcategory letters
    // Examples:
    //   R        = Preposition
    //   Ncfsa    = Noun, common, feminine, singular, absolute
    //   Vqp3ms   = Verb, Qal, perfect, 3rd person, masculine, singular
    //   C        = Conjunction
    //   Td       = Article definite
    //   To       = direct object marker (et/accusatif)
    //   Pp3ms    = Pronoun, personal, 3rd person, masc, sing
    var pos = seg.charAt(0);
    var rest = seg.slice(1);

    var parts = [];

    if (pos === 'A') parts.push('Adjectif');
    else if (pos === 'C') parts.push('Conjonction');
    else if (pos === 'D') parts.push('Adverbe');
    else if (pos === 'N') { parts.push('Nom'); parseNounDetails(rest, parts); return parts.join(' '); }
    else if (pos === 'P') { parts.push('Pronom'); parsePronounDetails(rest, parts); return parts.join(' '); }
    else if (pos === 'R') parts.push('Pr\u00e9position');
    else if (pos === 'S') parts.push('Suffixe'); // pronominal suffix (rare standalone)
    else if (pos === 'T') { parts.push('Particule'); parseParticleDetails(rest, parts); return parts.join(' '); }
    else if (pos === 'V') { parts.push('Verbe'); parseVerbDetails(rest, parts); return parts.join(' '); }
    else return pos + rest; // unknown

    // For adjective, parse like noun
    if (pos === 'A') parseNounDetails(rest, parts);
    return parts.join(' ');
  }

  function parseNounDetails(rest, parts) {
    // Nc<gender><number><state>
    // c=common, p=proper
    // f=feminine, m=masculine, b=both/common
    // s=singular, p=plural, d=dual
    // a=absolute, c=construct, d=determined
    var props = rest.charAt(0);
    var rest2 = rest.slice(1);
    if (props === 'c') parts.push('commun');
    else if (props === 'p') parts.push('propre');
    else if (props === 'g') parts.push('gentilice');
    if (rest2.length >= 1) {
      var g = rest2.charAt(0);
      if (g === 'f') parts.push('f\u00e9m.');
      else if (g === 'm') parts.push('masc.');
      else if (g === 'b') parts.push('genre commun');
    }
    if (rest2.length >= 2) {
      var n = rest2.charAt(1);
      if (n === 's') parts.push('sing.');
      else if (n === 'p') parts.push('pl.');
      else if (n === 'd') parts.push('duel');
    }
    if (rest2.length >= 3) {
      var st = rest2.charAt(2);
      if (st === 'a') parts.push('absolu');
      else if (st === 'c') parts.push('construit');
      else if (st === 'd') parts.push('d\u00e9termin\u00e9');
    }
  }

  function parseVerbDetails(rest, parts) {
    // V<stem><aspect><person><gender><number>
    // Stems: q=Qal, N=Niphal, p=Piel, P=Pual, h=Hiphil, H=Hophal, t=Hithpael, etc.
    var STEMS = {
      q:'Qal', N:'Niphal', p:'Piel', P:'Pual', h:'Hiphil', H:'Hophal',
      t:'Hithpael', o:'Polel', O:'Polal', r:'Polpal', m:'Polel', M:'Polal',
      s:'Pilpel', S:'Pilpal', l:'Hithpolel', L:'Hithpalpel', f:'Hithpoel',
      D:'Po\u00ebl', c:'Peal', // Aramaic
    };
    // Aspects: p=perfect, q=sequential perfect (waw), i=imperfect, w=sequential imperfect (waw),
    //          r=participle active, s=participle passive, a=infinitive absolute, c=infinitive construct,
    //          v=imperative, j=jussive, h=cohortative
    var ASPECTS = {
      p:'parfait', q:'parfait conv.', i:'imparfait', w:'imparfait conv.',
      r:'participe act.', s:'participe pas.',
      a:'infinitif abs.', c:'infinitif cstr.',
      v:'imp\u00e9ratif', j:'jussif', h:'cohortatif'
    };
    if (rest.length >= 1) parts.push(STEMS[rest.charAt(0)] || rest.charAt(0));
    if (rest.length >= 2) parts.push(ASPECTS[rest.charAt(1)] || rest.charAt(1));
    if (rest.length >= 3) {
      var p3 = rest.charAt(2);
      if (p3 === '1') parts.push('1re p.');
      else if (p3 === '2') parts.push('2e p.');
      else if (p3 === '3') parts.push('3e p.');
      if (rest.length >= 4) {
        var g = rest.charAt(3);
        if (g === 'f') parts.push('f\u00e9m.');
        else if (g === 'm') parts.push('masc.');
        else if (g === 'b') parts.push('g.c.');
      }
      if (rest.length >= 5) {
        var n = rest.charAt(4);
        if (n === 's') parts.push('sing.');
        else if (n === 'p') parts.push('pl.');
        else if (n === 'd') parts.push('duel');
      }
    }
  }

  function parsePronounDetails(rest, parts) {
    // Pp<person><gender><number>
    var t = rest.charAt(0);
    var TYPES = { p:'personnel', d:'d\u00e9mo.', i:'interrog.', r:'relatif', f:'ind\u00e9fini', x:'suffixe' };
    if (TYPES[t]) parts.push(TYPES[t]);
    // Skip advanced parsing for compactness
  }

  function parseParticleDetails(rest, parts) {
    var t = rest.charAt(0);
    var TYPES = { d:'article', o:'obj. direct (\u00e9t)', i:'interrogatif', n:'n\u00e9gatif', m:'d\u00e9mo.', e:'existentiel', j:'jussif', r:'relatif' };
    if (TYPES[t]) parts.push(TYPES[t]);
  }

  // Version courte (pour le 4e tier compact)
  function decodeMorphShort(morph) {
    if (!morph) return '';
    var segs = String(morph).replace(/^[HA]/, '').split('/');
    return segs.map(function (s) {
      var pos = s.charAt(0);
      var map = { A:'adj', C:'conj', D:'adv', N:'n', P:'pron', R:'pr\u00e9p', S:'sfx', T:'part', V:'vb' };
      var label = map[pos] || pos;
      // Add stem/aspect suffix for verbs
      if (pos === 'V' && s.length >= 3) {
        var stems = { q:'Qal', N:'Ni', p:'Pi', P:'Pu', h:'Hi', H:'Ho', t:'Hit' };
        var asps = { p:'pf', q:'pfC', i:'impf', w:'impfC', r:'ptcA', s:'ptcP', a:'infA', c:'infC', v:'imp', j:'juss', h:'coh' };
        label = (stems[s.charAt(1)] || s.charAt(1)) + '.' + (asps[s.charAt(2)] || s.charAt(2));
      } else if (pos === 'N' && s.length >= 4) {
        // Nc + gender + number + state: e.g. Ncfsa -> n.f.sg.a
        var g = s.charAt(2) === 'f' ? 'f' : (s.charAt(2) === 'm' ? 'm' : 'c');
        var n = s.charAt(3) === 'p' ? 'pl' : (s.charAt(3) === 'd' ? 'du' : 'sg');
        label = 'n.' + g + '.' + n;
      }
      return label;
    }).join('/');
  }

  // ── B2 : parsing et rendu des morphèmes ──

  // Translitte\u0301rations standard des pre\u0301fixes et suffixes massore\u0301tiques les plus courants.
  // Cle\u0301 = forme he\u0301breue normalise\u0301e (sans ta'amim). Valeur = translit latine.
  var PREFIX_TRANSLIT = {
    // Be\u0301t \u00ab dans / au / avec \u00bb
    '\u05D1\u05B0\u05BC':  'be', '\u05D1\u05B8\u05BC':  'b\u0101', '\u05D1\u05B7\u05BC':  'ba',  '\u05D1\u05B4\u05BC':  'bi',
    // La\u0308med \u00ab a\u0300 / pour \u00bb
    '\u05DC\u05B0':        'le', '\u05DC\u05B8':        'l\u0101', '\u05DC\u05B7':        'la',  '\u05DC\u05B4':        'li',
    // Ka\u0308ph \u00ab comme / selon \u00bb
    '\u05DB\u05B0\u05BC':  'ke', '\u05DB\u05B8\u05BC':  'k\u0101', '\u05DB\u05B7\u05BC':  'ka',
    // Me\u0308m \u00ab de / depuis \u00bb
    '\u05DE\u05B4':        'mi', '\u05DE\u05B5':        'm\u0113', '\u05DE\u05B6':        'me',
    // Article de\u0301fini \u00ab le / la \u00bb
    '\u05D4\u05B7':        'ha', '\u05D4\u05B8':        'h\u0101', '\u05D4\u05B6':        'he',
    // Particule interrogative
    '\u05D4\u05B2':        'h\u0103',
    // Conjonction \u00ab et \u00bb (forme avec chewa)
    '\u05D5\u05B0':        'we', '\u05D5\u05B7':        'wa', '\u05D5\u05B8':        'w\u0101', '\u05D5\u05B4':        'wi', '\u05D5\u05B6':        'we',
    // Conjonction avec shureq (avant consonne labiale ou chewa)
    '\u05D5\u05BC':        '\u00FB',
    // Relative \u00ab qui / que \u00bb
    '\u05E9\u05B6\u05C1':  'she', '\u05E9\u05B7\u05C1':  'sha', '\u05E9\u05B8\u05C1':  'sh\u0101'
  };

  var SUFFIX_TRANSLIT = {
    // Suffixes pronominaux nominaux / verbaux
    '\u05D5\u05B9':        '\u00F4',     // 3ms his/him
    '\u05D4\u05D5\u05BC':  'h\u00FB',    // 3ms long "hu\u0304"
    '\u05D4\u05BC':        '\u0101h',    // 3fs her
    '\u05DA\u05B8':        'k\u0101',    // 2ms (final kaph + qamats)
    '\u05DA\u05B0':        'k',          // 2fs
    '\u05D9':              '\u00EE',     // 1cs my
    '\u05E0\u05B4\u05D9':  'n\u00EE',    // 1cs objective (verbal "ni")
    '\u05E0\u05D5\u05BC':  'n\u00FB',    // 1cp us
    '\u05DB\u05B6\u05DD':  'kem',        // 2mp
    '\u05DB\u05B6\u05DF':  'ken',        // 2fp
    '\u05D4\u05B6\u05DD':  'hem',        // 3mp
    '\u05D4\u05B6\u05DF':  'hen',        // 3fp
    '\u05DD':              '\u0101m',    // 3mp plural suffix (short form)
    '\u05DF':              '\u0101n'     // 3fp plural suffix (short form)
  };

  // Normalisation NFC (Unicode canonique) \u2014 l'ordre des combining marks peut diffe\u0301rer
  // entre les sources OSHB ; NFC impose l'ordre canonique (ccc ascendant).
  function _nfc(s) {
    var str = String(s || '');
    return (typeof str.normalize === 'function') ? str.normalize('NFC') : str;
  }

  // Supprime les ta'amim (cantillation) et autres marques non vocaliques pour comparer les formes.
  function _normalizeHeb(s) {
    return _nfc(s).replace(/[\u0591-\u05AF]/g, '');
  }

  // Cherche une forme dans un mapping (essaie exact NFC, puis sans ta'amim).
  function _lookupMorphemeTranslit(hebText, map) {
    if (!hebText) return null;
    var nfc = _nfc(hebText);
    if (map[nfc]) return map[nfc];
    var stripped = _normalizeHeb(hebText);
    return map[stripped] || null;
  }

  // Reconstruit la translitte\u0301ration globale d'un mot en concate\u0301nant pre\u0301fixes + racine + suffixes.
  // Fallback : si un pre\u0301fixe/suffixe n'est pas dans la table, il est omis (la racine reste visible).
  function computeGlobalXlit(morphemes, rootXlit) {
    if (!morphemes || morphemes.length === 0) return rootXlit || '';
    var parts = [];
    for (var i = 0; i < morphemes.length; i++) {
      var seg = morphemes[i];
      if (seg.isRoot) {
        parts.push(rootXlit || '');
      } else if (seg.isPrefix) {
        var p = _lookupMorphemeTranslit(seg.text, PREFIX_TRANSLIT);
        if (p) parts.push(p);
      } else if (seg.isSuffix) {
        var s = _lookupMorphemeTranslit(seg.text, SUFFIX_TRANSLIT);
        if (s) parts.push(s);
      }
    }
    return parts.filter(Boolean).join('');
  }

  // Table des particules courantes (rendu popup grammatical)
  // Clé = code morph abrégé (depuis decodeSegment); valeur = {title, hebLetter, pronounce, sense, examples}
  var PARTICLE_TABLE = {
    'R': {
      title: 'Pr\u00e9position insp\u00e9parable',
      pronounce: 'b\u0259- / l\u0259- / k\u0259- / mi-',
      sense: 'D\u00e9signe une relation (dans, \u00e0, comme, depuis). S\u2019attache directement au mot suivant, sans espace.',
      examples: [
        { heb: '\u05D1\u05B0\u05BC\u05E8\u05B5\u05D0\u05E9\u05B4\u05C1\u05D9\u05EA', fr: '\u00AB au commencement \u00BB (b\u0259- + r\u00EA\u02BCshi\u0301yth)' },
        { heb: '\u05DC\u05B0\u05D0\u05B5\u05DC', fr: '\u00AB \u00E0 Dieu \u00BB (l\u0259- + \u02BC\u0113l)' }
      ]
    },
    'C': {
      title: 'Conjonction inspe\u0301parable',
      pronounce: 'w\u0259-  \u2192 \u00AB et \u00BB',
      sense: 'Conjonction copulative, additionnelle ou cons\u00E9cutive. S\u2019attache au d\u00E9but du mot.',
      examples: [
        { heb: '\u05D5\u05B0\u05D4\u05B8\u05D0\u05B8\u05E8\u05B6\u05E5', fr: '\u00AB et la terre \u00BB' }
      ]
    },
    'Td': {
      title: 'Article de\u0301fini',
      pronounce: 'ha- (parfois h\u0101- / he-)',
      sense: 'Marque la d\u00E9finition (\u00AB le/la/les \u00BB). Double la consonne suivante (daguesh).',
      examples: [
        { heb: '\u05D4\u05B7\u05D9\u05BC\u05D5\u05B9\u05DD', fr: '\u00AB le jour \u00BB' }
      ]
    },
    'Ti': {
      title: 'Particule interrogative',
      pronounce: 'h\u0103- ',
      sense: 'Introduit une question oui/non. Plac\u00E9e en t\u00EAte du mot ou de la proposition.',
      examples: [
        { heb: '\u05D4\u05B2\u05E9\u05B8\u05C1\u05DE\u05B9\u05E8\u05B0\u05EA\u05B4\u05D9', fr: '\u00AB ai-je gard\u00E9\u2026 ? \u00BB' }
      ]
    },
    'Tr': {
      title: 'Conjonction relative',
      pronounce: 'she- / sha-',
      sense: 'Conjonction relative rare (alternative \u00E0 \u02BEash\u0259r). Introduit une proposition relative.',
      examples: []
    },
    'To': {
      title: 'Marqueur d\u2019objet direct',
      pronounce: '\u02BCeth (ou \u02BCe\u0304th)',
      sense: 'Particule non traduisible introduisant l\u2019objet direct d\u00E9fini du verbe.',
      examples: [
        { heb: '\u05D0\u05B5\u05EA', fr: '(introduit l\u2019objet ; non traduit)' }
      ]
    },
    'S': {
      title: 'Suffixe pronominal',
      pronounce: 'selon la personne (-\u00F4, -e\u0304m, -\u0101n\u00FB\u2026)',
      sense: 'Pronom personnel attach\u00E9 \u00E0 un nom (possessif) ou \u00E0 un verbe (objet). S\u2019ajoute en fin de mot.',
      examples: [
        { heb: '\u05D3\u05B0\u05D1\u05B8\u05E8\u05B0\u05D5\u05B9', fr: '\u00AB sa parole \u00BB (d\u0259\u0304ba\u0304r + -\u00F4)' }
      ]
    }
  };

  /**
   * parseMorphemes(hebText, morphCode)
   *   Split a word into morphological segments.
   *   Returns an array of { text, morph, pos, role, isRoot, isPrefix, isSuffix, particle }
   *
   *   - text    : Hebrew characters for that segment
   *   - morph   : morph code for that segment (without H/A prefix)
   *   - pos     : first letter of morph (R, C, T, N, V, A, P, S...)
   *   - role    : 'prefix' | 'root' | 'suffix'
   *   - particle: entry from PARTICLE_TABLE if applicable, else null
   */
  function parseMorphemes(hebText, morphCode) {
    if (!hebText) return [];
    var hebSegs = String(hebText).split('/');
    var morphRaw = String(morphCode || '').replace(/^[HA]/, '');
    var morphSegs = morphRaw.split('/');
    var n = hebSegs.length;
    // For each segment decide its role
    // Root = the segment carrying the Strong (usually N/V/A/P or the longest content word)
    // Prefix = before the root (R, C, T particles usually)
    // Suffix = after the root (S pronominal suffix)
    var rootIdx = -1;
    for (var i = 0; i < n; i++) {
      var p = (morphSegs[i] || '').charAt(0);
      if (p === 'N' || p === 'V' || p === 'A' || p === 'P' || p === 'D') {
        rootIdx = i;
        break;
      }
    }
    // Fallback: if no N/V/A found, the root is the first non-particle segment or last
    if (rootIdx < 0) {
      for (var j = 0; j < n; j++) {
        var p2 = (morphSegs[j] || '').charAt(0);
        if (p2 !== 'R' && p2 !== 'C' && p2 !== 'T' && p2 !== 'S') { rootIdx = j; break; }
      }
      if (rootIdx < 0) rootIdx = n - 1;
    }

    var out = [];
    for (var k = 0; k < n; k++) {
      var m = morphSegs[k] || '';
      var pos = m.charAt(0);
      var role;
      if (k < rootIdx) role = 'prefix';
      else if (k === rootIdx) role = 'root';
      else role = 'suffix';
      // Lookup particle table: for multi-char codes (Td, Ti, Tr, To), prefer full match first
      var particle = PARTICLE_TABLE[m.slice(0, 2)] || PARTICLE_TABLE[pos] || null;
      out.push({
        text: hebSegs[k] || '',
        morph: m,
        pos: pos,
        role: role,
        isRoot: role === 'root',
        isPrefix: role === 'prefix',
        isSuffix: role === 'suffix',
        particle: particle
      });
    }
    return out;
  }

  // ── Chargement lexique + POS ──
  function loadLexicon() {
    if (_lexicon) return Promise.resolve(_lexicon);
    if (!lexiconUrl) return Promise.resolve([]);
    return fetch(lexiconUrl).then(function (r) { return r.json(); }).then(function (lex) {
      _lexicon = lex;
      lex.forEach(function (e) { _lexiconIndex[e.s] = e; });
      return lex;
    });
  }
  function loadPosDesc() {
    if (Object.keys(_posDesc).length) return Promise.resolve(_posDesc);
    if (!posDescUrl) return Promise.resolve({});
    return fetch(posDescUrl).then(function (r) { return r.json(); })
      .then(function (d) { _posDesc = d || {}; return _posDesc; })
      .catch(function () { return {}; });
  }
  function loadConcordance() {
    if (Object.keys(_concordance).length) return Promise.resolve(_concordance);
    if (!concordanceUrl) return Promise.resolve({});
    return fetch(concordanceUrl).then(function (r) { return r.json(); })
      .then(function (d) { _concordance = d || {}; return _concordance; })
      .catch(function () { return {}; });
  }
  function loadRootFamilies() {
    if (Object.keys(_rootFamilies).length) return Promise.resolve(_rootFamilies);
    if (!rootFamiliesUrl) return Promise.resolve({});
    return fetch(rootFamiliesUrl).then(function (r) { return r.json(); })
      .then(function (d) { _rootFamilies = d || {}; return _rootFamilies; })
      .catch(function () { return {}; });
  }
  function loadStrongConcepts() {
    if (Object.keys(_strongConcepts).length) return Promise.resolve(_strongConcepts);
    if (!strongConceptsUrl) return Promise.resolve({});
    return fetch(strongConceptsUrl).then(function (r) { return r.json(); })
      .then(function (d) { _strongConcepts = d || {}; return _strongConcepts; })
      .catch(function () { return {}; });
  }

  // ── Chargement d'un livre interlineaire (cache une fois charge) ──
  var _bookCache = {};
  function loadBook(book) {
    if (_bookCache[book.osis]) return Promise.resolve(_bookCache[book.osis]);
    var url = interlinearBaseUrl + book.code + '-' + book.osis + '.json';
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error('Livre indisponible (HTTP ' + r.status + ')');
      return r.json();
    }).then(function (data) {
      _bookCache[book.osis] = data;
      return data;
    });
  }

  // ── Chargement BYM markdown (proxy WP) + parse verset par verset ──
  function loadBymBook(bymFile) {
    if (_bymCache[bymFile]) return Promise.resolve(_bymCache[bymFile]);
    if (_bymLoading[bymFile]) return _bymLoading[bymFile];
    if (!bymProxyUrl) return Promise.resolve({});
    var url = bymProxyUrl + '?action=figuier_bym_proxy&file=' + encodeURIComponent(bymFile + '.md');
    _bymLoading[bymFile] = fetch(url).then(function (r) {
      if (!r.ok) return '';
      return r.text();
    }).then(function (text) {
      var parsed = parseBymMarkdown(text);
      _bymCache[bymFile] = parsed;
      delete _bymLoading[bymFile];
      return parsed;
    }).catch(function () { _bymCache[bymFile] = {}; delete _bymLoading[bymFile]; return {}; });
    return _bymLoading[bymFile];
  }

  // Parse BYM markdown : format BJC officiel (gitlab.com/anjc/bjc-source)
  // Chaque verset sur sa propre ligne : "CH:VS<TAB ou espaces>TEXTE"
  // Le texte peut contenir :
  //   - balises <w lemma="strong:HXXXX">mot</w> (hyperlien Strong)
  //   - commentaires HTML <!--note exegetique--> (notes)
  //   - autres balises inline (em, i, strong, span, etc.)
  // On nettoie tout pour afficher un texte lisible.
  function parseBymMarkdown(text) {
    if (!text) return {};
    var chapters = {};
    var lines = text.split(/\r?\n/);
    var verseRe = /^\s*(\d+)\s*:\s*(\d+)\s*[\t ]+(.+)$/;
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      if (!line) continue;
      // Skip headings Markdown et HTML metadata
      var trimmed = line.replace(/^\s+/, '');
      if (trimmed.charAt(0) === '#' || trimmed.charAt(0) === '<') continue;

      var m = verseRe.exec(line);
      if (!m) continue;
      var ch = parseInt(m[1], 10);
      var vs = parseInt(m[2], 10);
      var txt = m[3];

      // Nettoyage pour affichage
      txt = txt.replace(/<!--[\s\S]*?-->/g, '');
      txt = txt.replace(/<w\b[^>]*>([\s\S]*?)<\/w>/gi, '$1');
      txt = txt.replace(/<\/?(?:em|i|b|strong|u|span|sup|sub|small|big)(?:\s[^>]*)?>/gi, '');
      txt = txt.replace(/\s+/g, ' ').trim();

      if (!chapters[ch]) chapters[ch] = {};
      chapters[ch][vs] = txt;
    }
    return chapters;
  }

  // ── Rendering ──

  function renderHome() {
    root.innerHTML = '';
    var wrapper = el('div', { class: 'bi-home' });
    var header = el('div', { class: 'bi-home__header' }, [
      el('h1', { class: 'bi-home__title', text: 'Bible interlin\u00e9aire' }),
      el('p',  { class: 'bi-home__subtitle', text: 'Tanakh h\u00e9breu \u00b7 Texte pointu + translitt\u00e9ration + Strong + morphologie + gloss FR + BYM' })
    ]);
    wrapper.appendChild(header);

    var intro = el('p', { class: 'bi-home__intro', html:
      'Chaque mot du texte h\u00e9breu est d\u00e9compos\u00e9 en 5 lignes (h\u00e9breu \u00b7 translitt\u00e9ration \u00b7 Strong \u00b7 morphologie \u00b7 gloss FR), ' +
      'avec la traduction BYM (Bible de Y\u00e9hoshoua HaMashiah) en dessous de chaque verset. ' +
      'Cliquez sur un mot pour ouvrir sa fiche lexicale compl\u00e8te (racine h\u00e9braique, s\u00e9mantique BDB, occurrences bibliques).'
    });
    wrapper.appendChild(intro);

    // Groupements selon l'ordre du Tanakh (Torah \u00b7 Nevi'im \u00b7 Ketouvim)
    // Les sous-groupes (premiers prophe\u0300tes, derniers prophe\u0300tes, 12 petits, megilot) sont
    // ge\u0301re\u0301s via un petit label de se\u0301paration dans la grille.
    var subgroupLabels = {
      'nev_first': 'Premiers prophe\u0300tes (livres historiques)',
      'nev_last':  'Derniers prophe\u0300tes',
      'nev_twelve': 'Les douze petits prophe\u0300tes (Terei Asar)',
      'megilot':    'Megilot (les cinq rouleaux)'
    };

    TANAKH_GROUPS.forEach(function (g) {
      var section = el('section', { class: 'bi-home__group bi-home__group--' + g.key });
      var heading = el('div', { class: 'bi-home__group-heading' }, [
        el('h2', { class: 'bi-home__group-title', text: g.title }),
        el('span', { class: 'bi-home__group-subtitle', text: g.subtitle })
      ]);
      section.appendChild(heading);
      if (g.description) {
        section.appendChild(el('p', { class: 'bi-home__group-desc', text: g.description }));
      }

      // Filtrer les livres de ce groupe dans l'ordre de BOOKS
      var groupBooks = BOOKS.filter(function (b) { return b.group === g.key; });

      // De\u0301terminer les subgroupes pre\u0301sents pour introduire les sous-labels
      // Sentinel '__UNSET__' pour garantir la cre\u0301ation d'une grille au premier livre,
      // m\u00eame s'il n'a pas de subgroup (cas Torah / 1res entr\u00e9es Ketouvim).
      var lastSubgroup = '__UNSET__';
      var grid = null;
      groupBooks.forEach(function (b) {
        var sg = b.subgroup || null;
        if (sg !== lastSubgroup) {
          // Clo\u0302turer grille pre\u0301ce\u0301dente si existante
          if (grid) section.appendChild(grid);
          // Nouveau sous-label si applicable
          if (sg && subgroupLabels[sg]) {
            section.appendChild(el('h3', { class: 'bi-home__subgroup', text: subgroupLabels[sg] }));
          }
          grid = el('div', { class: 'bi-home__grid' });
          lastSubgroup = sg;
        }
        var card = el('button', {
          class: 'bi-home__book-card',
          type: 'button',
          'data-osis': b.osis,
          on: { click: function () { navigateTo(b.slug, 1); } }
        }, [
          el('span', { class: 'bi-home__book-name', html:
            '<span class="bi-home__book-bym">' + escapeHtml(b.bym || b.fr) + '</span>' +
            (b.bym && b.bym !== b.fr ? '<span class="bi-home__book-fr"> (' + escapeHtml(b.fr) + ')</span>' : '')
          }),
          el('span', { class: 'bi-home__book-meta', text: b.chapters + ' chap.' })
        ]);
        grid.appendChild(card);
      });
      if (grid) section.appendChild(grid);

      wrapper.appendChild(section);
    });

    root.appendChild(wrapper);
  }

  function renderReader() {
    var b = state.book;
    var ch = state.chapter;

    root.innerHTML = '';
    var wrapper = el('div', { class: 'bi-reader' });

    // ── Header navigation ──
    var header = el('div', { class: 'bi-reader__header' });

    var breadcrumb = el('nav', { class: 'bi-reader__breadcrumb', 'aria-label': 'Fil d\'ariane' }, [
      el('a', { href: '#', class: 'bi-breadcrumb-link', on: { click: function (e) { e.preventDefault(); navigateHome(); } } }, [
        document.createTextNode('Bible interlin\u00e9aire')
      ]),
      el('span', { class: 'bi-breadcrumb-sep', text: ' \u203a ' }),
      el('span', { class: 'bi-breadcrumb-current', text: bookDisplayName(b) + ' ' + ch })
    ]);
    header.appendChild(breadcrumb);

    var controls = el('div', { class: 'bi-reader__controls' });
    // Book selector
    var bookSel = el('select', {
      class: 'bi-ctrl bi-ctrl--book',
      'aria-label': 'Choisir un livre',
      on: { change: function (e) {
        var slug = e.target.value;
        navigateTo(slug, 1);
      }}
    });
    BOOKS.forEach(function (bk) {
      var opt = el('option', { value: bk.slug, text: bookDisplayName(bk) });
      if (bk.slug === b.slug) opt.selected = true;
      bookSel.appendChild(opt);
    });
    controls.appendChild(bookSel);

    // Chapter selector
    var chapSel = el('select', {
      class: 'bi-ctrl bi-ctrl--chap',
      'aria-label': 'Choisir un chapitre',
      on: { change: function (e) {
        navigateTo(b.slug, parseInt(e.target.value, 10));
      }}
    });
    for (var i = 1; i <= b.chapters; i++) {
      var opt = el('option', { value: String(i), text: 'Chapitre ' + i });
      if (i === ch) opt.selected = true;
      chapSel.appendChild(opt);
    }
    controls.appendChild(chapSel);

    // Verse selector (populated after chapter content loads)
    var verseSel = el('select', {
      class: 'bi-ctrl bi-ctrl--verse',
      id: 'bi-verse-select',
      'aria-label': 'Aller \u00e0 un verset',
      on: { change: function (e) {
        var vNum = e.target.value;
        if (!vNum) return;
        var verseEl = document.querySelector('.bi-verse[data-verse="' + vNum + '"]');
        if (verseEl) {
          verseEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
          // Feedback visuel: flash subtil sur le verset cible
          verseEl.classList.add('bi-verse--flash');
          setTimeout(function () { verseEl.classList.remove('bi-verse--flash'); }, 1500);
        }
        // Reset au placeholder apres scroll pour permettre re-selection du meme verset
        e.target.value = '';
      }}
    });
    verseSel.appendChild(el('option', { value: '', text: '\u2014 Verset \u2014' }));
    controls.appendChild(verseSel);

    // Prev / Next
    var prevBtn = el('button', {
      class: 'bi-ctrl bi-ctrl--nav',
      type: 'button',
      title: 'Chapitre pr\u00e9c\u00e9dent',
      on: { click: function () { goToPrevChapter(); } }
    }, [document.createTextNode('\u2039')]);
    var nextBtn = el('button', {
      class: 'bi-ctrl bi-ctrl--nav',
      type: 'button',
      title: 'Chapitre suivant',
      on: { click: function () { goToNextChapter(); } }
    }, [document.createTextNode('\u203a')]);
    controls.appendChild(prevBtn);
    controls.appendChild(nextBtn);

    header.appendChild(controls);
    wrapper.appendChild(header);

    // ── Chapter content ──
    var body = el('div', { class: 'bi-reader__body', id: 'bi-reader-body' });
    body.appendChild(el('div', { class: 'bi-loading', text: 'Chargement de ' + bookDisplayName(b) + ' ' + ch + '\u2026' }));
    wrapper.appendChild(body);

    // ── Sidebar toggle (mobile) ──
    var sidebarPlaceholder = el('aside', { class: 'bi-sidebar', id: 'bi-sidebar' }, [
      el('div', { class: 'bi-sidebar__placeholder', html: '<strong>Fiche lexicale</strong><br><span>Cliquez sur un mot h\u00e9breu pour afficher sa fiche compl\u00e8te (racine, BDB, occurrences).</span>' })
    ]);
    wrapper.appendChild(sidebarPlaceholder);

    root.appendChild(wrapper);

    // Load data
    Promise.all([
      loadBook(b),
      loadLexicon(),
      loadPosDesc(),
      loadConcordance(),
      loadRootFamilies(),
      loadBymBook(b.bymFile),
      loadStrongConcepts()
    ]).then(function (results) {
      var bookData = results[0];
      state.bookData = bookData;
      var bymChapters = results[5];
      renderChapterContent(bookData, ch, bymChapters);
      // Scroll to verse if provided
      if (state.focusVerse) {
        setTimeout(function () {
          var verseEl = document.querySelector('.bi-verse[data-verse="' + state.focusVerse + '"]');
          if (verseEl) verseEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
          state.focusVerse = null;
        }, 100);
      }
    }).catch(function (err) {
      body.innerHTML = '';
      body.appendChild(el('div', { class: 'bi-error', text: 'Erreur de chargement : ' + (err && err.message || err) }));
    });
  }

  function renderChapterContent(bookData, chapNum, bymChapters) {
    var body = document.getElementById('bi-reader-body');
    if (!body) return;
    body.innerHTML = '';

    var chapterVerses = (bookData.chapters && bookData.chapters[String(chapNum)]) || null;
    if (!chapterVerses) {
      body.appendChild(el('div', { class: 'bi-error', text: 'Chapitre ' + chapNum + ' introuvable pour ' + bookDisplayName(state.book) + '.' }));
      return;
    }

    var bymVerses = (bymChapters && bymChapters[chapNum]) || {};

    // Chapter title
    body.appendChild(el('h2', { class: 'bi-chapter-title', text: bookDisplayName(state.book) + ' \u00b7 Chapitre ' + chapNum }));

    // Iterate verses in numeric order
    var verseNums = Object.keys(chapterVerses).map(Number).sort(function (a,b){ return a-b; });
    verseNums.forEach(function (vNum) {
      var words = chapterVerses[vNum];
      var verseEl = renderVerse(bookData, chapNum, vNum, words, bymVerses[vNum] || '');
      body.appendChild(verseEl);
    });

    // Populate verse selector with available verses for this chapter
    var verseSelEl = document.getElementById('bi-verse-select');
    if (verseSelEl) {
      // Preserve placeholder (index 0), clear the rest
      while (verseSelEl.options.length > 1) verseSelEl.remove(1);
      verseNums.forEach(function (vNum) {
        verseSelEl.appendChild(el('option', { value: String(vNum), text: 'v. ' + vNum }));
      });
    }

    // Chapter nav bottom
    body.appendChild(renderChapterFooter());
  }

  function renderChapterFooter() {
    var b = state.book;
    var ch = state.chapter;
    var footer = el('div', { class: 'bi-chapter-footer' });
    if (ch > 1) {
      footer.appendChild(el('button', {
        class: 'bi-ctrl bi-ctrl--footer',
        type: 'button',
        on: { click: function () { goToPrevChapter(); } }
      }, [document.createTextNode('\u2039 ' + bookDisplayName(b) + ' ' + (ch - 1))]));
    } else {
      footer.appendChild(el('span', { class: 'bi-ctrl bi-ctrl--footer bi-ctrl--disabled', text: '' }));
    }
    if (ch < b.chapters) {
      footer.appendChild(el('button', {
        class: 'bi-ctrl bi-ctrl--footer bi-ctrl--next',
        type: 'button',
        on: { click: function () { goToNextChapter(); } }
      }, [document.createTextNode(bookDisplayName(b) + ' ' + (ch + 1) + ' \u203a')]));
    }
    return footer;
  }

  // ── Verset : card RTL avec grille mot-a-mot + ligne BYM ──
  function renderVerse(bookData, chapNum, vNum, words, bymText) {
    var verseCard = el('article', {
      class: 'bi-verse',
      'data-verse': String(vNum),
      'data-osis': bookData.book + '.' + chapNum + '.' + vNum
    });

    // Verse number label
    verseCard.appendChild(el('div', { class: 'bi-verse__num', text: String(vNum) }));

    // Words grid RTL
    var grid = el('div', { class: 'bi-verse__grid', dir: 'rtl' });
    words.forEach(function (w, idx) {
      grid.appendChild(renderWord(w, idx));
    });
    verseCard.appendChild(grid);

    // BYM translation
    var bymLine = el('div', { class: 'bi-verse__bym' });
    if (bymText) {
      bymLine.appendChild(el('span', { class: 'bi-verse__bym-label', text: 'BYM' }));
      bymLine.appendChild(el('span', { class: 'bi-verse__bym-text', text: bymText }));
      var readerUrl = buildBymReaderUrl(bookData.book, chapNum, vNum);
      if (readerUrl) {
        bymLine.appendChild(el('a', {
          class: 'bi-verse__bym-source',
          href: readerUrl,
          target: '_blank',
          rel: 'noopener',
          title: 'Lire ce verset sur bibledeyehoshouahamashiah.org',
          text: '\u2197'
        }));
      }
    } else {
      bymLine.appendChild(el('span', { class: 'bi-verse__bym-label', text: 'BYM' }));
      bymLine.appendChild(el('span', { class: 'bi-verse__bym-text bi-verse__bym-text--placeholder', text: 'Traduction en cours de chargement\u2026' }));
    }
    verseCard.appendChild(bymLine);

    return verseCard;
  }

  function renderWord(w, idx) {
    var hasStrong = !!w.s;
    // B2: wrapper is always a div now; click handlers are per-morpheme
    var wrapper = el('div', {
      class: 'bi-word',
      'data-strong': w.s || '',
      'data-idx': String(idx)
    });

    // Ligne 1 : H\u00e9breu avec morph\u00e8mes cliquables (design B2)
    var hebWrap = el('div', { class: 'bi-word__heb', dir: 'rtl' });
    var morphemes = parseMorphemes(w.t, w.m);
    if (morphemes.length === 0) {
      hebWrap.appendChild(document.createTextNode(w.t || ''));
    } else {
      morphemes.forEach(function (seg) {
        var spanClass = 'bi-morpheme bi-morpheme--' + seg.role;
        if (seg.isRoot && hasStrong) spanClass += ' bi-morpheme--clickable';
        else if (seg.particle) spanClass += ' bi-morpheme--clickable';
        var attrs = {
          class: spanClass,
          'data-morph': seg.morph,
          'data-role': seg.role
        };
        if (seg.isRoot && hasStrong) attrs['data-strong'] = w.s;
        var span = el('span', attrs, [document.createTextNode(seg.text)]);
        if (seg.isRoot && hasStrong) {
          span.addEventListener('click', function (e) {
            e.preventDefault(); e.stopPropagation();
            openWordSidebar(w);
          });
        } else if (seg.particle) {
          // Capture seg in closure
          (function (capturedSeg) {
            span.addEventListener('click', function (e) {
              e.preventDefault(); e.stopPropagation();
              openMorphemePopup(capturedSeg, span);
            });
          })(seg);
        }
        hebWrap.appendChild(span);
      });
    }
    wrapper.appendChild(hebWrap);

    // Ligne 2 : Translitte\u0301ration globale (B2) \u2014 pre\u0301fixes + racine + suffixes
    var globalXlit = computeGlobalXlit(morphemes, w.x || '');
    if (globalXlit) wrapper.appendChild(el('div', { class: 'bi-word__xlit', text: globalXlit }));
    else wrapper.appendChild(el('div', { class: 'bi-word__xlit bi-word__xlit--empty' }));

    // Ligne 3 : Strong
    if (w.s) wrapper.appendChild(el('div', { class: 'bi-word__strong', text: w.s }));
    else wrapper.appendChild(el('div', { class: 'bi-word__strong bi-word__strong--empty' }));

    // Ligne 4 : Morphologie (court)
    var morphShort = decodeMorphShort(w.m);
    var morphFull = decodeMorph(w.m);
    if (morphShort) {
      wrapper.appendChild(el('div', { class: 'bi-word__morph', title: morphFull, text: morphShort }));
    } else {
      wrapper.appendChild(el('div', { class: 'bi-word__morph bi-word__morph--empty' }));
    }

    // Ligne 5 : Gloss FR
    // Le champ `g` du mot prime (peut etre un override editorial local, ex: elohim minuscule
    // pour contexte faux-dieux). Fallback sur `ig` du lexique si pas de gloss local.
    var gloss = w.g || '';
    if (!gloss && w.s && _lexiconIndex[w.s] && _lexiconIndex[w.s].ig) {
      gloss = _lexiconIndex[w.s].ig;
    }
    wrapper.appendChild(el('div', { class: 'bi-word__gloss', text: gloss }));

    return wrapper;
  }

  function buildBymReaderUrl(osisBook, chap, verse) {
    // BYM reader : ?v1=<ABBR><chap>_<verse> avec abreviation reader specifique
    // Format depuis bible-v2-app.js / hotfix : abbr du type MT10_7 pour Mt 10:7
    var ABBR = {
      Gen:'GE', Exod:'EX', Lev:'LV', Num:'NB', Deut:'DT',
      Josh:'JS', Judg:'JG', Ruth:'RT', '1Sam':'1S', '2Sam':'2S',
      '1Kgs':'1R', '2Kgs':'2R', '1Chr':'1C', '2Chr':'2C',
      Ezra:'ED', Neh:'NE', Esth:'ES', Job:'JB', Ps:'PS',
      Prov:'PR', Eccl:'EC', Song:'CA',
      Isa:'IS', Jer:'JR', Lam:'LM', Ezek:'EZ', Dan:'DA',
      Hos:'OS', Joel:'JL', Amos:'AM', Obad:'AB', Jonah:'JN', Mic:'MI',
      Nah:'NA', Hab:'HA', Zeph:'SO', Hag:'AG', Zech:'ZA', Mal:'ML'
    };
    var a = ABBR[osisBook];
    if (!a) return '';
    return bymReaderBase + '?v1=' + a + chap + '_' + verse;
  }

  // ── B2 : popup grammatical pour un morph\u00e8me non-Strong (pre\u0301fixe / suffixe) ──
  function openMorphemePopup(seg, anchor) {
    // Remove any existing popup
    closeMorphemePopup();
    if (!seg || !seg.particle) return;

    var p = seg.particle;
    var popup = el('div', { class: 'bi-morpheme-popup', id: 'bi-morpheme-popup', role: 'dialog', 'aria-label': 'Explication grammaticale' });

    // Header: the Hebrew letter + role
    var roleLabel = seg.role === 'prefix' ? 'Pr\u00e9fixe' : (seg.role === 'suffix' ? 'Suffixe' : 'Particule');
    popup.appendChild(el('div', { class: 'bi-morpheme-popup__head', html:
      '<span class="bi-morpheme-popup__heb" dir="rtl">' + escapeHtml(seg.text) + '</span>' +
      '<span class="bi-morpheme-popup__role">' + escapeHtml(roleLabel) + '</span>' +
      '<button type="button" class="bi-morpheme-popup__close" aria-label="Fermer">\u00d7</button>'
    }));

    // Title + pronunciation
    popup.appendChild(el('div', { class: 'bi-morpheme-popup__title', text: p.title || '' }));
    if (p.pronounce) {
      popup.appendChild(el('div', { class: 'bi-morpheme-popup__pronounce', text: p.pronounce }));
    }

    // Sense explanation
    if (p.sense) {
      popup.appendChild(el('div', { class: 'bi-morpheme-popup__sense', text: p.sense }));
    }

    // Examples
    if (p.examples && p.examples.length) {
      var exList = el('ul', { class: 'bi-morpheme-popup__examples' });
      p.examples.forEach(function (ex) {
        var li = el('li', { class: 'bi-morpheme-popup__example', html:
          '<span class="bi-morpheme-popup__ex-heb" dir="rtl">' + escapeHtml(ex.heb) + '</span>' +
          '<span class="bi-morpheme-popup__ex-fr">' + escapeHtml(ex.fr) + '</span>'
        });
        exList.appendChild(li);
      });
      popup.appendChild(exList);
    }

    // Morph code footer (for curious readers)
    if (seg.morph) {
      popup.appendChild(el('div', { class: 'bi-morpheme-popup__morph', text: 'Code morphologique : ' + seg.morph }));
    }

    // Position popup next to anchor
    document.body.appendChild(popup);
    positionPopupNear(popup, anchor);

    // Close handlers
    popup.querySelector('.bi-morpheme-popup__close').addEventListener('click', closeMorphemePopup);
    // Close on outside click (deferred to avoid immediate close from the click that opened it)
    setTimeout(function () {
      document.addEventListener('click', _closePopupOnOutside, { once: false });
    }, 10);
    // Close on ESC
    document.addEventListener('keydown', _closePopupOnEsc);
  }

  function _closePopupOnOutside(e) {
    var popup = document.getElementById('bi-morpheme-popup');
    if (!popup) return;
    if (popup.contains(e.target)) return;
    if (e.target.classList && e.target.classList.contains('bi-morpheme')) return;
    closeMorphemePopup();
  }

  function _closePopupOnEsc(e) {
    if (e.key === 'Escape') closeMorphemePopup();
  }

  function closeMorphemePopup() {
    var popup = document.getElementById('bi-morpheme-popup');
    if (popup && popup.parentNode) popup.parentNode.removeChild(popup);
    document.removeEventListener('click', _closePopupOnOutside);
    document.removeEventListener('keydown', _closePopupOnEsc);
  }

  function positionPopupNear(popup, anchor) {
    if (!anchor) return;
    var rect = anchor.getBoundingClientRect();
    var top = rect.bottom + window.scrollY + 8;
    var left = rect.left + window.scrollX + (rect.width / 2);
    popup.style.position = 'absolute';
    popup.style.top = top + 'px';
    popup.style.left = left + 'px';
    popup.style.transform = 'translateX(-50%)';
    popup.style.zIndex = '1050';
    // Clamp to viewport horizontally
    var popRect = popup.getBoundingClientRect();
    if (popRect.left < 8) {
      popup.style.left = '8px';
      popup.style.transform = 'none';
    } else if (popRect.right > window.innerWidth - 8) {
      popup.style.left = (window.innerWidth - popRect.width - 8) + 'px';
      popup.style.transform = 'none';
    }
  }

  // ── Sidebar : fiche lexicale complete du mot clique ──
  function openWordSidebar(word) {
    var sidebar = document.getElementById('bi-sidebar');
    if (!sidebar) return;
    sidebar.innerHTML = '';
    sidebar.classList.add('bi-sidebar--open');
    document.body.classList.add('bi-sidebar-open');

    var closeBtn = el('button', {
      class: 'bi-sidebar__close',
      type: 'button',
      'aria-label': 'Fermer',
      title: 'Fermer la fiche',
      on: { click: function () { closeSidebar(); } }
    }, [document.createTextNode('\u00d7')]);
    sidebar.appendChild(closeBtn);

    if (!word.s) {
      sidebar.appendChild(el('div', { class: 'bi-sidebar__placeholder', html: '<strong>Aucun num\u00e9ro Strong</strong><br><span>Ce mot n\'a pas de r\u00e9f\u00e9rence lexicale.</span>' }));
      return;
    }

    var entry = _lexiconIndex[word.s];
    if (!entry) {
      sidebar.appendChild(el('div', { class: 'bi-sidebar__placeholder', html: '<strong>Strong ' + escapeHtml(word.s) + '</strong><br><span>Entr\u00e9e lexicale non trouv\u00e9e.</span>' }));
      return;
    }

    // Mini header : mot tel qu'affiche dans le texte
    var head = el('div', { class: 'bi-sidebar__head' }, [
      el('div', { class: 'bi-sidebar__head-hebrew', dir: 'rtl', text: word.t || entry.h || '' }),
      el('div', { class: 'bi-sidebar__head-refs', html:
        (word.x ? '<span class="bi-sidebar__head-xlit">' + escapeHtml(word.x) + '</span>' : '') +
        '<span class="bi-sidebar__head-strong">' + escapeHtml(word.s) + '</span>'
      })
    ]);
    sidebar.appendChild(head);

    // Delegate to renderHebrewCard export (bible-v3-hotfix.js)
    if (window.FIGUIER_HEBREW_CARD && typeof window.FIGUIER_HEBREW_CARD.render === 'function') {
      var concRefs = _concordance[word.s] || [];
      var rootData = _rootFamilies[word.s] || null;
      var cardHtml = window.FIGUIER_HEBREW_CARD.render(entry, concRefs, rootData);
      var cardWrapper = el('div', { class: 'bi-sidebar__card', html: cardHtml });
      sidebar.appendChild(cardWrapper);
      // Wire audio button + expand button manually
      wireSidebarCardHandlers(cardWrapper, entry);
    } else {
      // Fallback minimal (si hotfix pas charge)
      sidebar.appendChild(renderFallbackCard(entry, word));
    }

    // Concepts li\u00e9s (Strong \u2192 fiches th\u00e9matiques)
    var conceptBlock = renderConceptsBlock(word.s);
    if (conceptBlock) sidebar.appendChild(conceptBlock);

    // Link to full dictionary fiche
    var slugsFooter = el('div', { class: 'bi-sidebar__footer', html:
      '<a href="/lexique-hebreu-biblique/?strong=' + escapeHtml(word.s) + '" target="_blank" rel="noopener">Ouvrir la fiche compl\u00e8te dans le lexique h\u00e9breu \u2197</a>'
    });
    sidebar.appendChild(slugsFooter);

    // Re-applique les pre\u0301fe\u0301rences h\u00e9breu (translit auto + masquage) sur le DOM re-rendu
    if (window.FIGUIER_HEBREW_UTILS && typeof window.FIGUIER_HEBREW_UTILS.applyHebrewPrefs === 'function') {
      window.FIGUIER_HEBREW_UTILS.applyHebrewPrefs();
    }
  }

  function wireSidebarCardHandlers(cardWrapper, entry) {
    // Expand BDB full definition
    var expandBtn = cardWrapper.querySelector('.fb-hebrew-card__expand');
    var fullDef = cardWrapper.querySelector('.fb-hebrew-card__def--full');
    if (expandBtn && fullDef) {
      expandBtn.addEventListener('click', function () {
        fullDef.hidden = !fullDef.hidden;
        expandBtn.textContent = fullDef.hidden ? 'D\u00e9finition compl\u00e8te BDB \u2192' : 'Masquer la d\u00e9finition compl\u00e8te';
      });
    }
    // NOTE: le bouton audio .fb-hebrew-card__audio est gere par le handler
    // document-level de bible-v3-hotfix.js (evite double-speak / cancel race)
  }

  function renderFallbackCard(entry, word) {
    return el('div', { class: 'bi-sidebar__card bi-sidebar__card--fallback' }, [
      el('div', { class: 'bi-sidebar__fallback-heb', dir: 'rtl', text: entry.h || word.t || '' }),
      el('div', { class: 'bi-sidebar__fallback-xlit', text: entry.x || '' }),
      el('div', { class: 'bi-sidebar__fallback-pos', text: entry.bp || entry.p || '' }),
      el('div', { class: 'bi-sidebar__fallback-def', text: entry.d || '' })
    ]);
  }

  // ── Bloc Concepts li\u00e9s (Strong \u2192 fiches th\u00e9matiques) ──
  // Mapping catégorie \u2192 libell\u00e9 court FR (aligne\u0301 avec CATEGORY_MAP front-end)
  var CONCEPT_CAT_LABELS = {
    'etre_spirituel':    'Dieu',
    'personne':          'Personne',
    'lieu':              'Lieu',
    'lieu_sacre':        'Lieu sacr\u00e9',
    'peuple':            'Peuple',
    'tribu':             'Tribu',
    'objet':             'Objet',
    'animal':            'Animal',
    'plante':            'Plante',
    'aliment':           'Aliment',
    'vetement':          'V\u00eatement',
    'instrument':        'Instrument',
    'mesure':            'Mesure',
    'monnaie':           'Monnaie',
    'doctrine':          'Doctrine',
    'rite':              'Rite',
    'pratique':          'Pratique',
    'fonction':          'Fonction',
    'nature':            'Nature',
    'evenement':         '\u00c9v\u00e9nement',
    'matiere':           'Mati\u00e8re',
    'non_classifie':    ''
  };

  function renderConceptsBlock(strong) {
    if (!strong) return null;
    var list = _strongConcepts[strong];
    if (!list || !list.length) return null;

    // Limite d'affichage pour \u00e9viter la surcharge (sidebar scrollable si >8)
    var MAX_VISIBLE = 12;
    var visible = list.slice(0, MAX_VISIBLE);
    var remaining = list.length - visible.length;

    var block = el('section', {
      class: 'bi-sidebar__concepts',
      'aria-label': 'Concepts bibliques li\u00e9s'
    });

    var title = el('h4', { class: 'bi-sidebar__concepts-title', text: list.length > 1 ? 'Concepts li\u00e9s' : 'Concept li\u00e9' });
    block.appendChild(title);

    var ul = el('ul', { class: 'bi-sidebar__concepts-list' });
    visible.forEach(function (c) {
      var li = el('li', { class: 'bi-sidebar__concept-item' });
      var catLabel = CONCEPT_CAT_LABELS[c.c] || '';
      var href = conceptBaseUrl + encodeURIComponent(c.u || c.slug) + '/';
      var a = el('a', {
        class: 'bi-sidebar__concept-link',
        href: href,
        target: '_blank',
        rel: 'noopener',
        title: 'Ouvrir la fiche concept : ' + (c.l || c.slug)
      });
      a.appendChild(el('span', { class: 'bi-sidebar__concept-label', text: c.l || c.slug }));
      if (catLabel) {
        a.appendChild(el('span', {
          class: 'bi-sidebar__concept-cat',
          'data-cat': c.c,
          text: catLabel
        }));
      }
      li.appendChild(a);
      ul.appendChild(li);
    });
    block.appendChild(ul);

    if (remaining > 0) {
      block.appendChild(el('p', {
        class: 'bi-sidebar__concepts-more',
        text: '+ ' + remaining + ' autre' + (remaining > 1 ? 's' : '') + ' concept' + (remaining > 1 ? 's' : '') + ' li\u00e9' + (remaining > 1 ? 's' : '')
      }));
    }

    return block;
  }

  function closeSidebar() {
    var sidebar = document.getElementById('bi-sidebar');
    if (!sidebar) return;
    sidebar.classList.remove('bi-sidebar--open');
    document.body.classList.remove('bi-sidebar-open');
    sidebar.innerHTML = '<div class="bi-sidebar__placeholder"><strong>Fiche lexicale</strong><br><span>Cliquez sur un mot h\u00e9breu pour afficher sa fiche compl\u00e8te.</span></div>';
  }

  // ── Navigation + URL routing ──
  function navigateTo(slug, chap, verse) {
    var b = BOOK_BY_SLUG[slug];
    if (!b) return;
    state.book = b;
    state.chapter = Math.max(1, Math.min(b.chapters, chap || 1));
    state.focusVerse = verse || null;
    pushUrl();
    renderReader();
  }
  function navigateHome() {
    state.book = null;
    state.chapter = 1;
    pushUrl();
    renderHome();
  }
  function goToPrevChapter() {
    if (!state.book) return;
    if (state.chapter > 1) navigateTo(state.book.slug, state.chapter - 1);
  }
  function goToNextChapter() {
    if (!state.book) return;
    if (state.chapter < state.book.chapters) navigateTo(state.book.slug, state.chapter + 1);
  }
  function pushUrl() {
    var hash = '';
    if (state.book) {
      hash = '#/' + state.book.slug + '/' + state.chapter + (state.focusVerse ? '/' + state.focusVerse : '');
    }
    if (window.location.hash !== hash) {
      try { history.replaceState(null, '', window.location.pathname + window.location.search + hash); }
      catch (_) { window.location.hash = hash; }
    }
  }
  function parseUrl() {
    var hash = (window.location.hash || '').replace(/^#\/?/, '');
    if (!hash) return null;
    var parts = hash.split('/');
    var slug = parts[0];
    var chap = parseInt(parts[1], 10) || 1;
    var verse = parseInt(parts[2], 10) || null;
    if (!BOOK_BY_SLUG[slug]) return null;
    return { slug: slug, chap: chap, verse: verse };
  }

  // ── Keyboard shortcuts ──
  function installKeyboard() {
    document.addEventListener('keydown', function (e) {
      if (e.defaultPrevented || e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
      if (e.key === 'Escape') { closeSidebar(); return; }
      if (!state.book) return;
      if (e.key === 'ArrowLeft') goToPrevChapter();
      else if (e.key === 'ArrowRight') goToNextChapter();
    });
  }

  // ── Init ──
  function init() {
    root.innerHTML = '<div class="bi-loading">Initialisation de la bible interlin\u00e9aire\u2026</div>';

    // Preload lexicon + POS in parallel
    Promise.all([loadLexicon(), loadPosDesc()]).then(function () {
      var parsed = parseUrl();
      if (parsed) {
        state.book = BOOK_BY_SLUG[parsed.slug];
        state.chapter = parsed.chap;
        state.focusVerse = parsed.verse;
        renderReader();
      } else {
        renderHome();
      }
      installKeyboard();
      window.addEventListener('hashchange', function () {
        var p = parseUrl();
        if (!p) { navigateHome(); return; }
        if (!state.book || p.slug !== state.book.slug || p.chap !== state.chapter) {
          state.book = BOOK_BY_SLUG[p.slug];
          state.chapter = p.chap;
          state.focusVerse = p.verse;
          renderReader();
        }
      });
    }).catch(function (err) {
      root.innerHTML = '<div class="bi-error">Erreur d\'initialisation : ' + escapeHtml(err && err.message || String(err)) + '</div>';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
