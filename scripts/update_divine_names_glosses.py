#!/usr/bin/env python3
"""
Met a\u0300 jour les glosses des noms divins (H410, H430, H3050) dans :
  - hebrew-lexicon-fr-compact.json  (champ `ig`)
  - tous les fichiers interlinear/*.json (champ `g` des mots concerne\u0301s)

Regles:
  H410  \u2192 'El'     (par de\u0301faut)
  H3050 \u2192 'Yah'    (par de\u0301faut)
  H430  \u2192 'Elohi\u0302m' (vrai Dieu / juges) OU 'elohi\u0302m' (faux dieux)
           Detection faux dieu: H430 est dans un verset qui contient aussi H312 (autres)

Usage:
    python scripts/update_divine_names_glosses.py             # dry-run
    python scripts/update_divine_names_glosses.py --apply     # ecrit
"""
import argparse
import glob
import io
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
LEX_PATH = BASE / 'uploads' / 'dictionnaires' / 'hebrew' / 'hebrew-lexicon-fr-compact.json'
INTERLIN_DIR = BASE / 'uploads' / 'dictionnaires' / 'interlinear'

# Strong -> gloss par defaut
STRONG_GLOSS = {
    'H410': 'El',
    'H3050': 'Yah',
    'H430': 'Elohi\u0302m',  # default; overridden to lowercase for false-gods contexts
}

H430_FALSE_GOD_GLOSS = 'elohi\u0302m'


def read_json_with_bom(path):
    with open(path, 'rb') as f:
        raw = f.read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    if bom:
        raw = raw[3:]
    return json.loads(raw.decode('utf-8')), bom


def write_json_preserve_bom(path, data, bom, compact=False):
    if compact:
        payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    else:
        payload = json.dumps(data, ensure_ascii=False, indent=2)
    body = payload.encode('utf-8')
    if bom:
        body = b'\xef\xbb\xbf' + body
    with open(path, 'wb') as f:
        f.write(body)


def detect_lexicon_format(data):
    """Is the lexicon a list or dict? Compact vs indented?"""
    if isinstance(data, list):
        return 'list'
    return 'dict'


def update_lexicon(apply_changes):
    data, bom = read_json_with_bom(LEX_PATH)
    fmt = detect_lexicon_format(data)
    entries = data if fmt == 'list' else list(data.values())
    updates = 0
    for e in entries:
        s = e.get('s')
        if s in STRONG_GLOSS:
            old = e.get('ig')
            new = STRONG_GLOSS[s]
            if old != new:
                e['ig'] = new
                print(f'  [lexicon] {s}: ig {old!r} -> {new!r}')
                updates += 1
    if apply_changes and updates:
        # Detect if original file was compact (one line)
        with open(LEX_PATH, 'rb') as f:
            head = f.read(500)
        compact = b'\n' not in head[:500]
        write_json_preserve_bom(LEX_PATH, data, bom, compact=compact)
    return updates


def is_false_god_context(words, idx, window=2):
    """Retourne True si le mot H430 a l'index `idx` a un voisin H312 (autres)
    dans une fenetre de +/- `window` mots (adjacence proche = 'autres elohim')."""
    lo = max(0, idx - window)
    hi = min(len(words), idx + window + 1)
    for j in range(lo, hi):
        if j == idx:
            continue
        if words[j].get('s') == 'H312':
            return True
    return False


def update_interlinear(apply_changes):
    total_updates = 0
    total_h430_elohim = 0
    total_h430_elohim_lower = 0
    total_h410 = 0
    total_h3050 = 0

    for fp in sorted(INTERLIN_DIR.glob('*.json')):
        data, bom = read_json_with_bom(fp)
        file_updates = 0

        for chap, verses in (data.get('chapters') or {}).items():
            for vnum, words in verses.items():
                for i, w in enumerate(words):
                    s = w.get('s')
                    if s not in STRONG_GLOSS:
                        continue
                    if s == 'H430':
                        # Raffinement : H312 doit etre dans une fenetre proche (+/- 2 mots)
                        # pour qualifier "autres elohim" vs "son Elohim" co-existant dans un meme verset
                        if is_false_god_context(words, i, window=2):
                            new_gloss = H430_FALSE_GOD_GLOSS
                            total_h430_elohim_lower += 1
                        else:
                            new_gloss = STRONG_GLOSS['H430']
                            total_h430_elohim += 1
                    else:
                        new_gloss = STRONG_GLOSS[s]
                        if s == 'H410':
                            total_h410 += 1
                        elif s == 'H3050':
                            total_h3050 += 1

                    if w.get('g') != new_gloss:
                        w['g'] = new_gloss
                        file_updates += 1

        if apply_changes and file_updates:
            # Interlinear files use separators=(', ', ': ') — or maybe compact?
            with open(fp, 'rb') as f:
                head = f.read(500)
            # Check if head has ' : ' or '": "' style
            compact = (b'": "' in head and b'", "' in head)
            payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')) if compact else json.dumps(data, ensure_ascii=False, separators=(', ', ': '))
            body = payload.encode('utf-8')
            if bom:
                body = b'\xef\xbb\xbf' + body
            with open(fp, 'wb') as f:
                f.write(body)
        if file_updates:
            print(f'  [{fp.name}] {file_updates} mots mis a jour')
        total_updates += file_updates

    print()
    print('=== Stats interlinear ===')
    print(f'  H410  -> El      : {total_h410}')
    print(f'  H3050 -> Yah     : {total_h3050}')
    print(f'  H430  -> Elohim  : {total_h430_elohim}')
    print(f'  H430  -> elohim  : {total_h430_elohim_lower}')
    print(f'  TOTAL updates    : {total_updates}')
    return total_updates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'=== Update divine names glosses {mode} ===')
    print()
    print('--- Lexicon ---')
    update_lexicon(args.apply)
    print()
    print('--- Interlinear ---')
    update_interlinear(args.apply)


if __name__ == '__main__':
    main()
