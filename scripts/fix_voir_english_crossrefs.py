#!/usr/bin/env python3
"""
Phase 4B : pre-traite les renvois 'Voir [MAJUSCULES]' dans les chunks ISBE.

Strategie Option B (Hybride):
  1. Pour chaque 'Voir XYZ' :
     - Si XYZ existe dans le mapping résolu -> remplacer par le label_fr canonique
       (qui est deja en bonne casse: "Aleph", "Sacrifice", ...)
     - Sinon si XYZ est dans le MANUAL_EN_TO_FR -> utiliser la traduction manuelle
     - Sinon si XYZ est detecte comme sigle (PEF, HDB, NT, ...) -> garder tel quel
     - Sinon -> appliquer Smart TitleCase (stopwords FR lowercase)

Usage:
  python scripts/fix_voir_english_crossrefs.py              # dry-run (preview)
  python scripts/fix_voir_english_crossrefs.py --apply      # ecrit les chunks
  python scripts/fix_voir_english_crossrefs.py --sample 50  # show sample substitutions
"""
import argparse
import io
import json
import re
import sys
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

ROOT       = Path(__file__).resolve().parent.parent
DICT_DIR   = ROOT / 'uploads' / 'dictionnaires'
ISBE_DIR   = DICT_DIR / 'isbe'
AUDIT_DIR  = ROOT / 'work' / 'audit'
MAP_PATH   = AUDIT_DIR / 'voir-crossref-map.json'
LOG_PATH   = AUDIT_DIR / 'voir-fix-changes.json'

# Pattern 'Voir X' où X est UPPERCASE
# - commence par majuscule (ASCII A-Z ou accents majuscules A0-DD)
# - continue avec majuscules, chiffres, espaces, tirets, apostrophes, virgules, point-virgules
# - s'arrête avant un signe de ponctuation de fin ou fin de chaîne
VOIR_PATTERN = re.compile(
    r"Voir\s+([A-Z\u00c0-\u00dd][A-Z\u00c0-\u00dd0-9\s\-',]{1,60}?)(?=[\.,;:\)\]]|$)",
    re.U,
)

# Traductions manuelles pour les cas non resolus frequents
MANUAL_EN_TO_FR = {
    # Anglais -> Francais
    'APOCALYPTIC LITERATURE':              'Littérature apocalyptique',
    'APOCRYPHAL GOSPELS':                  'Évangiles apocryphes',
    'APOCRYPHAL ACTS':                     'Actes apocryphes',
    'WANDERINGS OF ISRAEL':                "Errances d'Israël",
    'ARMOR':                               'Armure',
    'ARMOUR':                              'Armure',
    'OLIVE TREE':                          'Olivier',
    'ENGLISH VERSIONS':                    'Versions anglaises',
    'SLAVERY':                             'Esclavage',
    'ANTELOPE':                            'Antilope',
    'ASTROLOGY':                           'Astrologie',
    'CALENDAR':                            'Calendrier',
    'LINEN':                               'Lin (tissu)',
    'FLAX':                                'Lin (plante)',
    'ANCIENT':                             'Ancien',
    'ANCIENT LITERATURE':                  'Littérature ancienne',

    # Variantes FR sans accent ou en UPPER non indexees
    'LITTERATURE APOCALYPTIQUE':           'Littérature apocalyptique',
    'LITT\u00c9RATURE APOCALYPTIQUE':      'Littérature apocalyptique',
    'ASMONEENS':                           'Asmonéens',
    'BLASPHEMIE':                          'Blasphémie',
    'CRETE':                               'Crète',
    'EPITRES PASTORALES':                  'Épîtres pastorales',
    'ETOILE DES MAGI':                     'Étoile des Mages',
    'REVELATION DE JEAN':                  'Révélation de Jean',

    # Expressions composees FR non indexees
    'POIDS ET MESURES':                    'Poids et mesures',
    'NAVIRES ET BATEAUX':                  'Navires et bateaux',
    "ERRANCES D'ISRAEL":                   "Errances d'Israël",
    "ERRANCES D'ISRA\u00cbL":              "Errances d'Israël",
    'TABLE DES NATIONS':                   'Table des nations',
    'ESCHATOLOGIE DU NOUVEAU TESTAMENT':   'Eschatologie du Nouveau Testament',
    "ESCHATOLOGIE DE L'ANCIEN TESTAMENT":  "Eschatologie de l'Ancien Testament",
    'EMPIRE ROMAIN ET CHRISTIANISME':      'Empire romain et christianisme',
    'BABYLONIE ET ASSYRIE':                'Babylonie et Assyrie',
    'LANGUE DU NOUVEAU TESTAMENT':         'Langue du Nouveau Testament',
    'TEXTE ET MANUSCRITS DU NOUVEAU TESTAMENT': 'Texte et manuscrits du Nouveau Testament',
    'PR\u00caTRES ET L\u00c9VITES':        'Prêtres et Lévites',
    'PRETRES ET LEVITES':                  'Prêtres et Lévites',
    'PRESSE \u00c0 VIN':                   'Presse à vin',
    'PRESSE A VIN':                        'Presse à vin',
    'LANGUES DE LA BIBLE':                 'Langues de la Bible',
}

# Sigles connus preserves tels quels
KNOWN_SIGLES = {'PEF', 'HDB', 'LTJM', 'NT', 'AT', 'LXX', 'MT', 'RAT', 'RSV', 'KJV', 'NIV', 'ASV',
                'ISBE', 'BDB', 'TWOT'}

# Tokens sacres ou conventionnels preserves en UPPERCASE meme dans TitleCase
# (tetragrammes, noms divins translitteres)
SACRED_UPPER = {'YHWH', 'JHVH', 'YHVH', 'JHWH'}

# Mots vides FR (passent en minuscule dans TitleCase, sauf 1er mot)
FR_STOPWORDS = {
    'et', 'ou', 'de', 'du', 'des', 'le', 'la', 'les', 'un', 'une',
    'à', 'au', 'aux', 'en', 'sur', 'dans', 'par', 'pour', 'avec',
    'sans', 'sous', 'entre',
}


def smart_titlecase(text):
    """TitleCase francais: premier mot capitalise, stopwords en minuscules,
    autres mots capitalises.

    Ex: 'POIDS ET MESURES' -> 'Poids et mesures'
        'NAVIRES ET BATEAUX' -> 'Navires et bateaux'
    """
    if not text:
        return text
    text = text.strip()
    # Split en preservant les separateurs (espaces, tirets, apostrophes)
    parts = re.split(r"(\s+|[\-'])", text)
    out = []
    first_word = True
    for part in parts:
        if not part:
            continue
        if part.isspace() or part in ('-', "'"):
            out.append(part)
            continue
        upper = part.upper()
        lower = part.lower()
        if upper in SACRED_UPPER:
            # Preserver les tetragrammes en UPPERCASE
            out.append(upper)
            first_word = False
        elif first_word:
            out.append(lower.capitalize())
            first_word = False
        elif lower in FR_STOPWORDS:
            out.append(lower)
        else:
            out.append(lower.capitalize())
    return ''.join(out)


def is_sigle(text):
    """Detecte les sigles."""
    t = text.strip()
    if t in KNOWN_SIGLES:
        return True
    if not t.isupper():
        return False
    # Pas d'espace et <=4 chars = probable sigle
    if ' ' not in t and len(t) <= 4:
        return True
    return False


def resolve_target(raw_target, resolved_map):
    """Retourne (new_form, reason) pour un target 'ALEPH' capture."""
    key = raw_target.upper().strip()
    # Priority 1: dictionnaire manuel (pour override les mauvaises resolutions)
    if key in MANUAL_EN_TO_FR:
        return MANUAL_EN_TO_FR[key], 'manual'
    # Priority 2: mapping resolu (label_fr canonique, deja bien casse)
    if key in resolved_map:
        return resolved_map[key]['label_fr'], 'resolved'
    # Priority 3: sigle preserve
    if is_sigle(raw_target):
        return raw_target, 'sigle'
    # Priority 4: Smart TitleCase
    return smart_titlecase(raw_target), 'titlecase'


def load_resolved_map():
    with open(MAP_PATH, encoding='utf-8') as f:
        data = json.load(f)
    return data['resolved']


def read_json_preserve_bom(path):
    with open(path, 'rb') as f:
        raw = f.read()
    has_bom = raw.startswith(b'\xef\xbb\xbf')
    if has_bom:
        raw = raw[3:]
    data = json.loads(raw.decode('utf-8'))
    return data, has_bom


def write_json_preserve_bom(path, data, has_bom):
    """Ecrit en preservant la convention ISBE : separators=(', ', ': ')."""
    payload = json.dumps(data, ensure_ascii=False, separators=(', ', ': '))
    body = payload.encode('utf-8')
    if has_bom:
        body = b'\xef\xbb\xbf' + body
    with open(path, 'wb') as f:
        f.write(body)


def transform_in_voir_clause(clause, resolved_map, entry_id, samples, sample_budget, stats, changes_log, fname):
    """Parcourt une clause 'Voir ...' complete et transforme tous les tokens UPPERCASE
    rencontres (y compris apres ',' ou ';').

    Une clause est de la forme: 'Voir X', 'Voir X ; Y', 'Voir X, Y, Z', 'Voir aussi X ; Y', etc.
    """
    # Pattern qui trouve les sequences UPPERCASE les plus longues possibles
    # (incluant espaces/tirets/apostrophes internes pour preserver les expressions
    # composees comme "VERGE D'AARON" ou "POIDS ET MESURES").
    # Une sequence commence apres un separateur (debut, espace, ',', ';', '(') ET
    # le premier char est UPPERCASE. Elle continue greedy tant qu'on a des chars
    # UPPERCASE/espace/tiret/apostrophe, et s'arrete au premier char qui casse
    # (minuscule, chiffre apres espace non-UPPER, ponctuation, ou fin).
    token_pattern = re.compile(
        r"(?<=[\s,;(])"                                                          # precede d'un separateur
        r"(?P<tok>[A-Z\u00c0-\u00dd](?:[A-Z\u00c0-\u00dd0-9]|[\s\-']+(?=[A-Z\u00c0-\u00dd]))*[A-Z\u00c0-\u00dd0-9]?)"
        r"(?=[\s\.,;:\)\]]|$)",                                                  # suivi de sep ou fin
        re.U,
    )

    def replacer(m):
        raw_target = m.group('tok').strip().rstrip(",;.:)")
        if len(raw_target) < 2:
            return m.group(0)
        if not raw_target.isupper():
            # Contains mixed case (already processed or not UPPER) — skip
            return m.group(0)
        new_form, reason = resolve_target(raw_target, resolved_map)
        if new_form == raw_target:
            stats['no_change'] += 1
            return m.group(0)
        stats[reason] += 1
        changes_log.append({
            'file': fname,
            'entry_id': entry_id,
            'before': raw_target,
            'after': new_form,
            'reason': reason,
        })
        if len(samples) < sample_budget:
            samples.append({
                'entry_id': entry_id,
                'before': raw_target,
                'after': new_form,
                'reason': reason,
            })
        # Lookbehind n'est pas consomme, donc juste remplacer le token
        return new_form

    return token_pattern.sub(replacer, clause)


# Pattern pour une clause 'Voir ...' complete, jusqu'au '.', '\n' ou fin de chaine
VOIR_CLAUSE_PATTERN = re.compile(
    r"Voir(?:\s+aussi)?(?:\s+l'article)?\s+[^.\n]{1,300}",
    re.U,
)


def process_file(fp, resolved_map, apply_changes, samples, sample_budget, stats, changes_log):
    data, has_bom = read_json_preserve_bom(fp)
    file_changed = False
    file_changes = 0

    for entry in data:
        defn = entry.get('definition', '') or ''
        if not isinstance(defn, str) or 'Voir' not in defn:
            continue

        def clause_replacer(mc):
            nonlocal file_changed, file_changes
            clause = mc.group(0)
            new_clause = transform_in_voir_clause(
                clause, resolved_map, entry.get('id'),
                samples, sample_budget, stats, changes_log, fp.name
            )
            if new_clause != clause:
                file_changed = True
                file_changes += 1
            return new_clause

        new_defn = VOIR_CLAUSE_PATTERN.sub(clause_replacer, defn)

        if new_defn != defn:
            entry['definition'] = new_defn
            entry['definition_length'] = len(new_defn)

    if apply_changes and file_changed:
        write_json_preserve_bom(fp, data, has_bom)

    return file_changed, file_changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='write changes to ISBE chunks')
    ap.add_argument('--sample', type=int, default=30, help='sample size to display')
    args = ap.parse_args()

    if not MAP_PATH.exists():
        print('ERROR: mapping not found. Run build_voir_crossref_map.py first.')
        return 1

    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'=== Phase 4B (Voir crossref fix) {mode} ===')
    print()

    resolved_map = load_resolved_map()
    print(f'Resolved map loaded: {len(resolved_map)} entries')
    print(f'Manual EN->FR dict : {len(MANUAL_EN_TO_FR)} entries')
    print()

    stats = Counter()
    samples = []
    changes_log = []

    for fp in sorted(ISBE_DIR.glob('isbe-?.json')):
        changed, n = process_file(fp, resolved_map, args.apply, samples, args.sample, stats, changes_log)
        if changed:
            tag = 'write' if args.apply else 'dry'
            print(f'  [{tag}] {fp.name}: {n} changes')

    print()
    print('=== Stats by reason ===')
    for k in ['resolved', 'manual', 'sigle', 'titlecase', 'no_change']:
        print(f'  {k:>10} : {stats.get(k, 0)}')
    total_fix = sum(stats[k] for k in ('resolved', 'manual', 'titlecase') if k in stats)
    print(f'  {"TOTAL_FIX":>10} : {total_fix}')

    print()
    print(f'=== Sample of {len(samples)} substitutions ===')
    # Group samples by reason for readability
    by_reason = {}
    for s in samples:
        by_reason.setdefault(s['reason'], []).append(s)
    for reason in ['resolved', 'manual', 'titlecase', 'sigle']:
        lst = by_reason.get(reason, [])
        if not lst:
            continue
        print(f'\n  -- {reason} ({len(lst)}) --')
        for s in lst[:10]:
            print(f'    {s["before"]!r:<55} -> {s["after"]!r:<55}  [{s["entry_id"]}]')

    if args.apply:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, 'w', encoding='utf-8') as f:
            json.dump({'stats': dict(stats), 'changes': changes_log}, f, ensure_ascii=False, indent=2)
        print(f'\nFull log: {LOG_PATH} ({len(changes_log)} changes)')
    else:
        print('\n(dry-run: no files written. Pass --apply to persist.)')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
