#!/usr/bin/env python3
"""
Fix des résidus anglais + abbréviations tronquées dans le lexique hébreu.

Couvre :
  - Remplacements simples (covenant, Ruin, righteous, etc.)
  - Expansion d'abbréviations (N., S., Isr., D.)
  - Ré-traduction OpenAI pour H5039 (foolishness/wickedness phrase complète)

Usage :
    python scripts/fix_bdb_residuals_cleanup.py              # dry-run
    python scripts/fix_bdb_residuals_cleanup.py --apply
"""
import argparse
import io
import json
import os
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
NC_PATH = BASE / 'hebrew-lexicon-fr.json'
COMPACT_PATH = BASE / 'uploads' / 'dictionnaires' / 'hebrew' / 'hebrew-lexicon-fr-compact.json'

# Remplacements simples avec word boundaries (regex, remplacement)
SIMPLE_REPLACEMENTS = [
    # Mots anglais -> FR
    (re.compile(r'\bcovenant\b'), 'alliance'),
    (re.compile(r'\bCovenant\b'), 'Alliance'),
    (re.compile(r'\bRuin\b'), 'Ruine'),
    (re.compile(r'\brighteous\b'), 'juste'),
    (re.compile(r'\bRighteous\b'), 'Juste'),
    # Nom propre : ajouter accent
    (re.compile(r'\bEvil-Mérodach\b'), 'Évil-Mérodach'),
    # H5039 : re-traduction ciblée de la phrase
    (re.compile(r'\bfoolishness, i\.e\. \(morally\) wickedness; concretely, a crime; by extension, punishment\b'),
     'folie, c\u2019est-à-dire (moralement) méchanceté ; concrètement, un crime ; par extension, un châtiment'),
]

# Expansion d'abbréviations : regex avec word boundary stricte
# Context : on exige un espace avant et après, ou début/fin, ou ponctuation
ABBREV_REPLACEMENTS = [
    # N. -> Nord (uniquement dans contexte géographique : avant/après "Israël", "frontière", "de", etc.)
    # On utilise un lookbehind/lookahead permissif : un mot capitalisé ou prep avant
    (re.compile(r'(?<=[\s(,])N\.(?=\s+(?:Isra|fr\.|frontière|d[\'e]|de\s|Israël))'), 'Nord'),
    (re.compile(r'(?<=[\s(,])S\.(?=\s+(?:Juda|fr\.|frontière|d[\'e]|de\s|Sichem|Hébron|Neguev))'), 'Sud'),
    # Fallback : N. / S. isolés dans phrase biblique (moins strict)
    (re.compile(r'(?<=\s)N\.\s+d[\'e]\s'), 'Nord de '),
    (re.compile(r'(?<=\s)S\.\s+d[\'e]\s'), 'Sud de '),
    # Isr. -> Israël (contexte standalone)
    (re.compile(r'\bIsr\.(?=\s|[,;:)]|$)'), 'Israël'),
    # D. -> David (seulement dans le contexte H7194 : "la vie de D.")
    (re.compile(r'(?<=la vie de )D\.(?=\s)'), 'David'),
]


def read_json_with_bom(path):
    with open(path, 'rb') as f:
        raw = f.read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    if bom:
        raw = raw[3:]
    return json.loads(raw.decode('utf-8')), bom


def apply_all_fixes(text):
    """Apply all replacements to a text string. Returns (new_text, n_changes)."""
    if not isinstance(text, str) or not text:
        return text, 0
    new = text
    total = 0
    for pat, repl in SIMPLE_REPLACEMENTS:
        new, n = pat.subn(repl, new)
        total += n
    for pat, repl in ABBREV_REPLACEMENTS:
        new, n = pat.subn(repl, new)
        total += n
    return new, total


def walk_and_fix(obj, path, stats, changes):
    """Walk the object structure, apply fixes to strings, track changes."""
    if isinstance(obj, str):
        new, n = apply_all_fixes(obj)
        if n > 0:
            stats['strings_modified'] += 1
            stats['total_replacements'] += n
            changes.append({'path': path, 'before': obj[:200], 'after': new[:200], 'n': n})
            return new
        return obj
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_item = walk_and_fix(item, path + f'[{i}]', stats, changes)
            obj[i] = new_item
        return obj
    elif isinstance(obj, dict):
        for k in list(obj.keys()):
            new_val = walk_and_fix(obj[k], path + '.' + k, stats, changes)
            obj[k] = new_val
        return obj
    return obj


def fix_compact(apply_changes):
    data, bom = read_json_with_bom(COMPACT_PATH)
    stats = Counter()
    changes = []
    for e in data:
        s = e.get('s', '?')
        # Fix only target fields (d, df, bd, g, se)
        for field in ['d', 'df', 'bd', 'g', 'se']:
            if field in e:
                e[field] = walk_and_fix(e[field], f'{s}.{field}', stats, changes)
    print(f'Strings modified : {stats["strings_modified"]}')
    print(f'Total replacements: {stats["total_replacements"]}')
    print()
    # Sample changes
    print('=== Échantillon changes ===')
    for c in changes[:15]:
        print(f'  [{c["path"]}] ({c["n"]} replace)')
        print(f'    avant: {c["before"][:100]}')
        print(f'    après: {c["after"][:100]}')

    if apply_changes:
        # Write compact avec separators (',', ':')
        payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        if bom:
            payload = b'\xef\xbb\xbf' + payload
        with open(COMPACT_PATH, 'wb') as f:
            f.write(payload)
        print(f'\nCompact saved: {COMPACT_PATH} ({os.path.getsize(COMPACT_PATH):,} bytes)')
    return stats, changes


def fix_non_compact(apply_changes):
    """Same fix on non-compact for consistency."""
    if not NC_PATH.exists():
        print('Non-compact not found, skip')
        return
    with io.open(NC_PATH, 'r', encoding='utf-8-sig') as f:
        nc = json.load(f)
    stats = Counter()
    changes = []
    for e in nc:
        s = e.get('strong', '?')
        for field in ['definition_short_fr', 'definition_full_fr', 'bdb_defs_fr', 'defs_strong_fr', 'usage_fr']:
            if field in e:
                e[field] = walk_and_fix(e[field], f'{s}.{field}', stats, changes)
        # Also fix bdb_senses (nested)
        if 'bdb_senses' in e and isinstance(e['bdb_senses'], list):
            for sense in e['bdb_senses']:
                if isinstance(sense, dict):
                    for k in ['def_fr', 'defs_fr', 'text_fr']:
                        if k in sense:
                            sense[k] = walk_and_fix(sense[k], f'{s}.bdb_senses.{sense.get("stem","?")}.{k}', stats, changes)
                    if 'senses' in sense and isinstance(sense['senses'], list):
                        for sub in sense['senses']:
                            if isinstance(sub, dict):
                                for k in ['def_fr', 'defs_fr']:
                                    if k in sub:
                                        sub[k] = walk_and_fix(sub[k], f'{s}.sub', stats, changes)
    print(f'Non-compact : {stats["strings_modified"]} strings / {stats["total_replacements"]} replacements')
    if apply_changes:
        with open(NC_PATH, 'wb') as f:
            f.write(json.dumps(nc, ensure_ascii=False, indent=2).encode('utf-8'))
        print(f'Non-compact saved: {NC_PATH}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'=== BDB residuals cleanup {mode} ===')
    print()
    print('--- Compact ---')
    fix_compact(args.apply)
    print()
    print('--- Non-compact ---')
    fix_non_compact(args.apply)


if __name__ == '__main__':
    main()
