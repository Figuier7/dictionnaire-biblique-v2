#!/usr/bin/env python3
"""
Corrections simples de glosses `ig` (lexique) + `g` (interlinear) pour Strong cle\u0301s.
Aucune distinction contextuelle : un seul gloss par de\u0301faut par Strong.

Usage:
    python scripts/update_core_glosses_batch.py          # dry-run
    python scripts/update_core_glosses_batch.py --apply
"""
import argparse
import glob
import io
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
LEX_PATH = BASE / 'uploads' / 'dictionnaires' / 'hebrew' / 'hebrew-lexicon-fr-compact.json'
INTERLIN_DIR = BASE / 'uploads' / 'dictionnaires' / 'interlinear'

# Strong -> nouvelle gloss par de\u0301faut
CORRECTIONS = {
    'H5769':  'e\u0301ternite\u0301',  # éternité  (was 'caché')
    'H3519':  'gloire',               # was 'poids'
    'H5315':  'a\u0302me',            # âme  (was 'vitalité')
    'H1285':  'alliance',             # was 'pacte'
    'H1004':  'maison',               # was 'une maison'
    'H7563':  'me\u0301chant',        # méchant  (was 'mauvais')
    'H8451':  'Torah',                # was 'précepte'
}


def read_json_with_bom(path):
    with open(path, 'rb') as f:
        raw = f.read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    if bom:
        raw = raw[3:]
    return json.loads(raw.decode('utf-8')), bom


def write_json_preserve_bom(path, data, bom, separators=(',', ':')):
    payload = json.dumps(data, ensure_ascii=False, separators=separators)
    body = payload.encode('utf-8')
    if bom:
        body = b'\xef\xbb\xbf' + body
    with open(path, 'wb') as f:
        f.write(body)


def update_lexicon(apply_changes):
    data, bom = read_json_with_bom(LEX_PATH)
    entries = data if isinstance(data, list) else list(data.values())
    updates = 0
    for e in entries:
        s = e.get('s')
        if s in CORRECTIONS:
            old = e.get('ig')
            new = CORRECTIONS[s]
            if old != new:
                e['ig'] = new
                updates += 1
                print(f'  [lexicon] {s}: ig {old!r} -> {new!r}')
    if apply_changes and updates:
        # Compact format (no space after separator) — same as original
        write_json_preserve_bom(LEX_PATH, data, bom, separators=(',', ':'))
    return updates


def update_interlinear(apply_changes):
    from collections import Counter
    stats = Counter()
    total = 0

    for fp in sorted(INTERLIN_DIR.glob('*.json')):
        data, bom = read_json_with_bom(fp)
        file_changes = 0

        for chap, verses in (data.get('chapters') or {}).items():
            for vnum, words in verses.items():
                for w in words:
                    s = w.get('s')
                    if s not in CORRECTIONS:
                        continue
                    new_gloss = CORRECTIONS[s]
                    stats[s] += 1
                    total += 1
                    if w.get('g') != new_gloss:
                        w['g'] = new_gloss
                        file_changes += 1

        if apply_changes and file_changes:
            # Interlinear format: separators=(', ', ': ')
            write_json_preserve_bom(fp, data, bom, separators=(', ', ': '))
            print(f'  [{fp.name}] {file_changes} updates')
        elif file_changes:
            print(f'  [{fp.name}] {file_changes} updates (dry-run)')

    print()
    print('=== Stats per Strong ===')
    for s in CORRECTIONS:
        print(f'  {s} ({CORRECTIONS[s]:<12s}): {stats.get(s, 0)} occurrences')
    print(f'  TOTAL : {total}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'=== Core glosses batch {mode} ===')
    print()
    print('--- Lexicon ---')
    update_lexicon(args.apply)
    print()
    print('--- Interlinear ---')
    update_interlinear(args.apply)


if __name__ == '__main__':
    main()
