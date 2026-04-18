#!/usr/bin/env python3
"""
Audit final : résidus anglais + abbréviations dans tous les champs texte du lexique.
Version 2 : patterns précis, pas de faux positifs sur "son" (possessif FR).

Output : console + work/audit/bdb-residuals-v2.csv
"""
import csv
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
LEX_PATH = BASE / 'uploads' / 'dictionnaires' / 'hebrew' / 'hebrew-lexicon-fr-compact.json'
OUT_CSV = BASE / 'work' / 'audit' / 'bdb-residuals-v2.csv'

# Patterns pour VRAIS résidus anglais (pas d'ambiguïté avec le français)
ENGLISH_PATTERNS = {
    'son_of': re.compile(r'\bson of\b', re.I),
    'daughter_of': re.compile(r'\bdaughter of\b', re.I),
    'God': re.compile(r'\bGod\b'),
    'Lord': re.compile(r'\bLord\b'),
    'Ruin': re.compile(r'\bRuin\b'),
    'Heaven': re.compile(r'\bHeaven\b'),
    'Evil': re.compile(r'\bEvil\b'),
    'covenant': re.compile(r'\bcovenant\b'),
    'lovingkindness': re.compile(r'\blovingkindness\b'),
    'steadfast': re.compile(r'\bsteadfast love\b'),
    'righteousness': re.compile(r'\brighteousness\b'),
    'wickedness': re.compile(r'\bwickedness\b'),
    'foolishness': re.compile(r'\bfoolishness\b'),
    'righteous': re.compile(r'\brighteous\b'),
    'mighty': re.compile(r'\bmighty\b'),
    'wisdom': re.compile(r'\bwisdom\b'),
    'earth': re.compile(r'\bearth\b'),
    'heaven': re.compile(r'\bheaven\b'),
    'holy': re.compile(r'\bholy\b'),
    'priest': re.compile(r'\bpriest\b'),
    'prophet': re.compile(r'\bprophet\b'),
    'servant': re.compile(r'\bservant\b'),
    'temple': re.compile(r'\btemple\b'),
    'sanctuary': re.compile(r'\bsanctuary\b'),
    'sacrifice_en': re.compile(r'\bsacrifice\b'),  # peut être FR aussi mais contextuel
    # Mots anglais qui sont rarement FR
    'blessing_en': re.compile(r'\bblessing\b'),
    'peace_en': re.compile(r'\bpeace\b'),
    'truth_en': re.compile(r'\btruth\b'),
    'love_en': re.compile(r'\blove\b'),
    'mercy_en': re.compile(r'\bmercy\b'),
    'wrath_en': re.compile(r'\bwrath\b'),
    'judgment_en': re.compile(r'\bjudgment\b'),
}

# Abbréviations à expanser
ABBREV_PATTERNS = {
    'D.': re.compile(r'(?<=\s)D\.(?=\s)'),
    'N.': re.compile(r'(?<=\s)N\.(?=\s)'),
    'S.': re.compile(r'(?<=\s)S\.(?=\s)'),
    'M.': re.compile(r'(?<=\s)M\.(?=\s)'),
    'Isr.': re.compile(r'\bIsr\.(?=\s|[,;:)]|$)'),
    'Jer.': re.compile(r'\bJer\.(?=\s|[,;:)]|$)'),
}


def read_json_with_bom(path):
    with open(path, 'rb') as f:
        raw = f.read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    if bom:
        raw = raw[3:]
    return json.loads(raw.decode('utf-8')), bom


def main():
    print(f'Loading {LEX_PATH}...')
    lex, _ = read_json_with_bom(LEX_PATH)
    print(f'  {len(lex)} entries')
    print()

    english_hits = Counter()
    abbrev_hits = Counter()
    findings = []

    def scan_text(s, h, field, text):
        for name, pat in ENGLISH_PATTERNS.items():
            matches = pat.findall(text)
            if matches:
                english_hits[name] += len(matches)
                findings.append({
                    's': s, 'h': h, 'field': field, 'type': 'english',
                    'pattern': name, 'count': len(matches), 'sample': text[:250]
                })
        for name, pat in ABBREV_PATTERNS.items():
            matches = pat.findall(text)
            if matches:
                abbrev_hits[name] += len(matches)
                findings.append({
                    's': s, 'h': h, 'field': field, 'type': 'abbrev',
                    'pattern': name, 'count': len(matches), 'sample': text[:250]
                })

    for e in lex:
        s = e.get('s', '?')
        h = e.get('h', '')
        for field in ['d', 'df']:
            val = e.get(field, '')
            if isinstance(val, str) and val:
                scan_text(s, h, field, val)
        for field in ['bd', 'g']:
            val = e.get(field, [])
            if isinstance(val, list):
                for i, item in enumerate(val):
                    if isinstance(item, str):
                        scan_text(s, h, f'{field}[{i}]', item)
        for sense in e.get('se', []) or []:
            if not isinstance(sense, dict): continue
            st = sense.get('st', '?')
            d_val = sense.get('d', '')
            if isinstance(d_val, str) and d_val:
                scan_text(s, h, f'se[{st}].d', d_val)
            for sub in sense.get('c', []) or []:
                if not isinstance(sub, dict): continue
                sub_d = sub.get('d', '')
                if isinstance(sub_d, str) and sub_d:
                    scan_text(s, h, f'se[{st}].c[{sub.get("n","?")}].d', sub_d)

    print('=== Patterns anglais (vrais résidus) ===')
    for k, v in english_hits.most_common():
        print(f'  {k:<20}: {v}')
    print()
    print('=== Patterns abbréviations ===')
    for k, v in abbrev_hits.most_common():
        print(f'  {k:<20}: {v}')
    print()
    print(f'Total findings: {len(findings)}')
    print(f'Unique entries affected: {len(set((f["s"], f["field"]) for f in findings))}')
    print()

    # Échantillons par pattern
    by_pattern = {}
    for f in findings:
        by_pattern.setdefault(f['pattern'], []).append(f)
    print('=== Échantillons ===')
    for pat, hits in sorted(by_pattern.items(), key=lambda x: -len(x[1])):
        print(f'\n--- {pat} ({len(hits)} hits) ---')
        for h in hits[:3]:
            print(f'  {h["s"]} {h["h"]} [{h["field"]}]: {h["sample"][:150]}')

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['strong', 'hebrew', 'field', 'type', 'pattern', 'count', 'sample'])
        for finding in findings:
            w.writerow([finding['s'], finding['h'], finding['field'], finding['type'],
                       finding['pattern'], finding['count'], finding['sample']])
    print(f'\nCSV: {OUT_CSV}')


if __name__ == '__main__':
    main()
