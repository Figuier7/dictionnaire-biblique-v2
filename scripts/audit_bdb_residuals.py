#!/usr/bin/env python3
"""
Audit des re\u0301sidus anglais + abbre\u0301viations tronque\u0301es dans le lexique h\u00e9breu FR.

Cible 2 proble\u0300mes :
  A) Mots anglais re\u0301siduels dans `bd`, `g`, `d`, `df`, `se[].d`, `se[].c[].d`
     Ex : bd=['Destruction', 'Ruin', \"'Abaddo\u0302n\"] — \"Ruin\" non traduit
  B) Abbre\u0301viations de noms propres non expanse\u0301es : \"D.\" pour \"David\" etc.
     Ex : \"la vie de Jonathan e\u0301tait lie\u0301e a\u0300 la vie de D.\"

Sortie : work/audit/bdb-residuals.csv + resume\u0301 console
"""
import argparse
import csv
import io
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
LEX_PATH = BASE / 'uploads' / 'dictionnaires' / 'hebrew' / 'hebrew-lexicon-fr-compact.json'
OUT_CSV = BASE / 'work' / 'audit' / 'bdb-residuals.csv'

# Mots anglais fre\u0301quents qui sont souvent de\u0301laisse\u0301s par les traductions (re\u0301sidus)
# Liste construite pour e\u0302tre conservatrice : mots sans \u00e9quivalent FR proche qui pourraient
# causer des faux positifs (evite "and", "or", "the", "of" qui collident avec FR)
ENGLISH_RESIDUAL_WORDS = {
    'Ruin', 'Heaven', 'Heavens', 'earth', 'Earth', 'son', 'Son', 'sons', 'Sons',
    'father', 'Father', 'fathers', 'Fathers', 'mother', 'Mother',
    'child', 'Child', 'children', 'Children', 'house', 'House', 'city', 'City',
    'land', 'Land', 'way', 'Way', 'place', 'Place', 'eye', 'Eye', 'eyes',
    'hand', 'Hand', 'head', 'Head', 'king', 'King', 'people', 'People',
    'life', 'Life', 'death', 'Death', 'word', 'Word', 'words', 'Words',
    'day', 'Day', 'days', 'Days', 'night', 'Night',
    'water', 'Water', 'waters', 'Waters', 'light', 'Light', 'darkness', 'Darkness',
    'fire', 'Fire', 'mountain', 'Mountain', 'river', 'River',
    'good', 'Good', 'evil', 'Evil', 'great', 'Great', 'small', 'Small',
    'holy', 'Holy', 'righteous', 'Righteous', 'blessed', 'Blessed',
    'priest', 'Priest', 'prophet', 'Prophet', 'servant', 'Servant',
    'heart', 'Heart', 'soul', 'Soul', 'spirit', 'Spirit', 'flesh', 'Flesh',
    'make', 'come', 'speak', 'take', 'give', 'go', 'see', 'hear', 'know',
    'break', 'bring', 'build', 'call', 'cry', 'fall', 'hold',
    'open', 'close', 'leave', 'lead', 'lie', 'live', 'meet', 'put',
    'run', 'say', 'send', 'set', 'show', 'sit', 'stand', 'turn',
    # Mots speciaux souvent rate\u0301s
    'lovingkindness', 'steadfast', 'covenant', 'righteousness',
}

# Abbre\u0301viations susceptibles d'e\u0302tre des troncatures de noms propres
# (une seule lettre majuscule suivie de point, entoure\u0301e de contexte biblique)
# On les flagge si dans un contexte sugge\u0301rant un nom propre
SUSPECT_SHORT_ABBREV_RE = re.compile(r'\b([A-Z])\.(?=\s|[,;:\)\]]|$)')
# Contexte biblique : "la vie de X.", "pour X.", "selon X.", "apre\u0300s X."
NAME_CONTEXT_RE = re.compile(
    r'(?:de\s+|par\s+|\u00e0\s+|chez\s+|pour\s+|selon\s+|apre\u0300s\s+|avec\s+|avant\s+|'
    r'fils\s+de\s+|fille\s+de\s+|r\u00e8gne\s+de\s+|e\u0301poque\s+de\s+)([A-Z])\.(?=\s|[,;:\)\]]|$)',
    re.U,
)


def read_json_with_bom(path):
    with open(path, 'rb') as f:
        raw = f.read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    if bom:
        raw = raw[3:]
    return json.loads(raw.decode('utf-8')), bom


def _collect_text_values(obj, field_path=''):
    """Yield (field_path, str_value) for all string values recursively."""
    if isinstance(obj, str):
        yield (field_path, obj)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from _collect_text_values(item, field_path + f'[{i}]')
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _collect_text_values(v, field_path + '.' + k if field_path else k)


def find_english_residuals(text):
    """Returns list of english-looking residual words found in text."""
    hits = []
    words = re.findall(r'\b[A-Za-z]+\b', text)
    for w in words:
        if w in ENGLISH_RESIDUAL_WORDS:
            hits.append(w)
    return hits


def find_suspect_abbrev(text):
    """Returns list of suspect single-letter abbreviations in biblical context."""
    return [m.group(1) for m in NAME_CONTEXT_RE.finditer(text)]


def audit(lex):
    findings = []
    stats = Counter()
    english_word_counter = Counter()

    for e in lex:
        s = e.get('s', '?')
        h = e.get('h', '')

        # Scan les champs de texte cle\u0301s
        for field in ['d', 'df']:
            val = e.get(field, '')
            if not isinstance(val, str) or not val:
                continue
            eng = find_english_residuals(val)
            if eng:
                stats[f'{field}_english'] += 1
                for w in eng:
                    english_word_counter[w] += 1
                findings.append({
                    's': s, 'h': h, 'field': field,
                    'issue': 'english_residual',
                    'detail': ', '.join(sorted(set(eng))),
                    'sample': val[:200],
                })
            abb = find_suspect_abbrev(val)
            if abb:
                stats[f'{field}_abbrev'] += 1
                findings.append({
                    's': s, 'h': h, 'field': field,
                    'issue': 'abbrev_context',
                    'detail': ', '.join(sorted(set(abb))),
                    'sample': val[:200],
                })

        # Scan les listes `bd` et `g`
        for field in ['bd', 'g']:
            val = e.get(field, [])
            if not isinstance(val, list):
                continue
            eng = []
            for item in val:
                if isinstance(item, str):
                    e_hits = find_english_residuals(item)
                    eng.extend(e_hits)
            if eng:
                stats[f'{field}_english'] += 1
                for w in eng:
                    english_word_counter[w] += 1
                findings.append({
                    's': s, 'h': h, 'field': field,
                    'issue': 'english_residual',
                    'detail': ', '.join(sorted(set(eng))),
                    'sample': str(val)[:200],
                })

        # Scan les sens structures
        for sense in e.get('se', []) or []:
            if not isinstance(sense, dict):
                continue
            st = sense.get('st', '?')
            for field_inner in ['d']:
                val = sense.get(field_inner, '')
                if not isinstance(val, str) or not val:
                    continue
                eng = find_english_residuals(val)
                if eng:
                    stats[f'se_{st}_english'] += 1
                    findings.append({
                        's': s, 'h': h, 'field': f'se[{st}].{field_inner}',
                        'issue': 'english_residual',
                        'detail': ', '.join(sorted(set(eng))),
                        'sample': val[:200],
                    })
            for sub in sense.get('c', []) or []:
                if not isinstance(sub, dict):
                    continue
                sub_d = sub.get('d', '')
                if not isinstance(sub_d, str) or not sub_d:
                    continue
                eng = find_english_residuals(sub_d)
                if eng:
                    stats[f'se_c_english'] += 1
                    findings.append({
                        's': s, 'h': h, 'field': f'se[{st}].c.{sub.get("n","?")}.d',
                        'issue': 'english_residual',
                        'detail': ', '.join(sorted(set(eng))),
                        'sample': sub_d[:200],
                    })

    return findings, stats, english_word_counter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', action='store_true', help='Export CSV')
    ap.add_argument('--max', type=int, default=40, help='Max rows in console')
    args = ap.parse_args()

    print(f'Loading {LEX_PATH}...')
    lex, bom = read_json_with_bom(LEX_PATH)
    print(f'  {len(lex)} entries')
    print()

    findings, stats, english_words = audit(lex)

    print('=== Findings stats ===')
    for k, v in sorted(stats.items(), key=lambda x: -x[1]):
        print(f'  {k:<30}: {v}')
    print()
    print(f'Total findings: {len(findings)}')
    print(f'Unique entries affected: {len(set(f["s"] for f in findings))}')
    print()
    print('=== Top 20 english residual words ===')
    for w, n in english_words.most_common(20):
        print(f'  {w:<20}: {n}')
    print()
    print(f'=== Sample (max {args.max}) ===')
    for f in findings[:args.max]:
        print(f'  {f["s"]:<7} {f["h"]:<10} field={f["field"]:<25} issue={f["issue"]:<18} detail=[{f["detail"][:60]}]')

    if args.csv:
        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT_CSV, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['strong', 'hebrew', 'field', 'issue', 'detail', 'sample'])
            for finding in findings:
                w.writerow([finding['s'], finding['h'], finding['field'],
                           finding['issue'], finding['detail'], finding['sample']])
        print(f'\nCSV exported: {OUT_CSV}')


if __name__ == '__main__':
    main()
