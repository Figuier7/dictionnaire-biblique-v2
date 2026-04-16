#!/usr/bin/env python3
"""
Audit complet de la conformité BYM éditoriale dans les 3 dictionnaires.

Règles BYM (AGENTS_COMMON.md + editorial-terminology.json) :
- "Dieu" (majuscule) → "Elohîm" — INTERDIT dans les définitions
- "l'Éternel" → "YHWH" — INTERDIT
- "Jésus" standalone → "Yéhoshoua" — INTERDIT
- "Christ" → "Mashiah" ou "le Mashiah" — INTERDIT
- "Seigneur" quand = YHWH → "YHWH" — INTERDIT
- "le Seigneur" quand = Jésus → "le Seigneur" OK (ou Yéhoshoua selon contexte)

Patterns AUTORISÉS (convention de parenthèse explicative) :
- "Elohîm (Dieu)" — OK, c'est la convention AGENTS
- "Yéhoshoua (Jésus)" ou "Yehoshoua (Jésus)" — OK
- "YHWH (l'Éternel)" — OK
- "Mashiah (Christ)" — OK

Ce script scanne les 3 dictionnaires et classe chaque occurrence.
"""
import json
import sys
import re
import glob
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
DICT_DIR = ROOT / "uploads" / "dictionnaires"
AUDIT_DIR = ROOT / "work" / "audit"
OUT_JSON = AUDIT_DIR / "bym-editorial-audit.json"


def scan_definitions(entries_iter):
    """Scan definitions from an iterator of (entry_id, mot, definition) tuples."""
    results = {
        'dieu_in_pattern': 0,      # Elohîm (Dieu) — OK
        'dieu_standalone': 0,       # "Dieu" sans Elohîm — à corriger
        'dieu_samples': [],
        'jesus_in_pattern': 0,      # Yéhoshoua (Jésus) — OK
        'jesus_standalone': 0,      # "Jésus" sans Yéhoshoua — à corriger
        'jesus_samples': [],
        'christ_in_pattern': 0,     # Mashiah (Christ) — OK
        'christ_standalone': 0,     # "Christ" sans Mashiah — à corriger
        'christ_samples': [],
        'eternel': 0,               # "l'Éternel" — à corriger
        'eternel_samples': [],
        'seigneur_for_yhwh': 0,     # "le Seigneur" quand = YHWH
    }

    for entry_id, mot, defn in entries_iter:
        if not defn:
            continue

        # === DIEU ===
        # Count pattern "Elohîm (Dieu)" — OK
        results['dieu_in_pattern'] += len(re.findall(r'Eloh[iî]m\s*\(Dieu\)', defn))
        # Count standalone "Dieu" NOT in pattern
        # Must be: capital D, word boundary, NOT preceded by "(", NOT in "Elohîm (Dieu)"
        for m in re.finditer(r'\bDieu\b', defn):
            # Check if inside pattern
            before = defn[max(0, m.start()-20):m.start()]
            if 'Eloh' in before and '(' in before:
                continue  # Part of "Elohîm (Dieu)" pattern
            results['dieu_standalone'] += 1
            if len(results['dieu_samples']) < 30:
                ctx = defn[max(0, m.start()-30):m.end()+30].replace('\n', ' ')
                results['dieu_samples'].append({
                    'entry_id': entry_id, 'mot': mot[:25], 'context': ctx
                })

        # === JÉSUS ===
        results['jesus_in_pattern'] += len(re.findall(
            r'Y[eé]hoshoua\s*\(J[eé]sus[^)]*\)', defn))
        for m in re.finditer(r'\bJ[eé]sus\b', defn):
            before = defn[max(0, m.start()-25):m.start()]
            if 'hoshoua' in before and '(' in before:
                continue
            results['jesus_standalone'] += 1
            if len(results['jesus_samples']) < 30:
                ctx = defn[max(0, m.start()-30):m.end()+30].replace('\n', ' ')
                results['jesus_samples'].append({
                    'entry_id': entry_id, 'mot': mot[:25], 'context': ctx
                })

        # === CHRIST ===
        results['christ_in_pattern'] += len(re.findall(
            r'Mashiah\s*\(Christ\)', defn))
        for m in re.finditer(r'\bChrist\b', defn):
            before = defn[max(0, m.start()-20):m.start()]
            if 'Mashiah' in before and '(' in before:
                continue
            # Exclude "Jésus-Christ" compounds and "Antichrist"
            if 'Anti' in defn[max(0, m.start()-5):m.start()]:
                continue
            results['christ_standalone'] += 1
            if len(results['christ_samples']) < 20:
                ctx = defn[max(0, m.start()-30):m.end()+30].replace('\n', ' ')
                results['christ_samples'].append({
                    'entry_id': entry_id, 'mot': mot[:25], 'context': ctx
                })

        # === L'ÉTERNEL ===
        eternel_matches = re.findall(r"l['\u2019][EÉ]ternel", defn)
        if eternel_matches:
            results['eternel'] += len(eternel_matches)
            if len(results['eternel_samples']) < 10:
                results['eternel_samples'].append({
                    'entry_id': entry_id, 'mot': mot[:25],
                    'count': len(eternel_matches),
                })

    return results


def iter_isbe():
    for fp in sorted((DICT_DIR / 'isbe').glob('isbe-?.json')):
        with open(fp, encoding='utf-8-sig') as f:
            for e in json.load(f):
                yield e['id'], e.get('mot', ''), e.get('definition', '')


def iter_easton():
    fp = DICT_DIR / 'easton' / 'easton.entries.json'
    with open(fp, encoding='utf-8-sig') as f:
        for e in json.load(f):
            yield e['id'], e.get('mot', ''), e.get('definition', '')


def iter_smith():
    fp = DICT_DIR / 'smith' / 'smith.entries.json'
    with open(fp, encoding='utf-8') as f:
        for e in json.load(f):
            yield e['id'], e.get('mot', ''), e.get('definition', '')


def main():
    all_results = {}
    for name, iterator in [('isbe', iter_isbe), ('easton', iter_easton), ('smith', iter_smith)]:
        print(f'Scanning {name}...')
        all_results[name] = scan_definitions(iterator())
        r = all_results[name]
        print(f'  Dieu pattern (OK): {r["dieu_in_pattern"]}')
        print(f'  Dieu standalone:   {r["dieu_standalone"]}')
        print(f'  Jésus pattern (OK):{r["jesus_in_pattern"]}')
        print(f'  Jésus standalone:  {r["jesus_standalone"]}')
        print(f'  Christ pattern (OK):{r["christ_in_pattern"]}')
        print(f'  Christ standalone: {r["christ_standalone"]}')
        print(f'  l\'Éternel:         {r["eternel"]}')
        print()

    # Totals
    print('=== TOTAUX ===')
    for key in ['dieu_standalone', 'jesus_standalone', 'christ_standalone', 'eternel']:
        total = sum(all_results[d][key] for d in all_results)
        print(f'  {key}: {total}')

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f'\nOutput: {OUT_JSON}')


if __name__ == '__main__':
    main()
