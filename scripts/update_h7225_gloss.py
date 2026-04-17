#!/usr/bin/env python3
"""
Met a\u0300 jour la gloss de H7225 (re\u0302'shi\u0302yth) :
- Par de\u0301faut : 'commencement'
- Pre\u0301mices (contexte rituel/agricole/premier-ne\u0301) : liste PREMICES
- Le meilleur / chef (sens figuratif) : liste MEILLEUR

Aussi met a\u0300 jour l'`ig` du lexique compact : 'pre\u0301mices' -> 'commencement'.

Usage:
    python scripts/update_h7225_gloss.py            # dry-run
    python scripts/update_h7225_gloss.py --apply
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

DEFAULT_GLOSS = 'commencement'
PREMICES_GLOSS = 'pre\u0301mices'  # pr\u00e9mices
MEILLEUR_GLOSS = 'le meilleur'

# Re\u0301fe\u0301rences utilisant le fichier interlinear (code chapitre:verset)
# Format : 'NN-BookFile': set de 'chap:verse'
PREMICES = {
    '01-Gen':   {'49:3'},
    '02-Exod':  {'23:19', '34:26'},
    '03-Lev':   {'2:12', '23:10'},
    '04-Num':   {'15:20', '15:21', '18:12'},
    '05-Deut':  {'18:4', '21:17', '26:2', '26:10'},
    '09-1Sam':  {'2:29', '15:21'},
    '14-2Chr':  {'31:5'},
    '16-Neh':   {'10:38', '12:44'},
    '19-Ps':    {'78:51', '105:36'},
    '20-Prov':  {'3:9'},
    '24-Jer':   {'2:3'},
    '26-Ezek':  {'20:40', '44:30', '48:14'},
    '28-Hos':   {'9:10'},
}

MEILLEUR = {
    '04-Num':   {'24:20'},
    '05-Deut':  {'33:21'},
    '18-Job':   {'40:19'},
    '24-Jer':   {'49:35'},
    '27-Dan':   {'11:41'},
    '30-Amos':  {'6:1', '6:6'},
}


def read_json_with_bom(path):
    with open(path, 'rb') as f:
        raw = f.read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    if bom:
        raw = raw[3:]
    return json.loads(raw.decode('utf-8')), bom


def write_json_preserve_bom(path, data, bom, compact=True, sep_with_space=True):
    if compact and sep_with_space:
        payload = json.dumps(data, ensure_ascii=False, separators=(', ', ': '))
    elif compact:
        payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    else:
        payload = json.dumps(data, ensure_ascii=False, indent=2)
    body = payload.encode('utf-8')
    if bom:
        body = b'\xef\xbb\xbf' + body
    with open(path, 'wb') as f:
        f.write(body)


def update_lexicon(apply_changes):
    data, bom = read_json_with_bom(LEX_PATH)
    entries = data if isinstance(data, list) else list(data.values())
    for e in entries:
        if e.get('s') == 'H7225':
            old = e.get('ig')
            if old != DEFAULT_GLOSS:
                e['ig'] = DEFAULT_GLOSS
                print(f'  [lexicon] H7225 ig: {old!r} -> {DEFAULT_GLOSS!r}')
            break
    if apply_changes:
        # compact no-space separators (format original hebrew-lexicon)
        write_json_preserve_bom(LEX_PATH, data, bom, compact=True, sep_with_space=False)


def classify(book_file, chap, verse):
    key = f'{chap}:{verse}'
    if book_file in PREMICES and key in PREMICES[book_file]:
        return PREMICES_GLOSS
    if book_file in MEILLEUR and key in MEILLEUR[book_file]:
        return MEILLEUR_GLOSS
    return DEFAULT_GLOSS


def update_interlinear(apply_changes):
    stats = {DEFAULT_GLOSS: 0, PREMICES_GLOSS: 0, MEILLEUR_GLOSS: 0}
    total = 0
    files_changed = 0

    for fp in sorted(INTERLIN_DIR.glob('*.json')):
        book_file = fp.stem  # "01-Gen"
        data, bom = read_json_with_bom(fp)
        file_changes = 0

        for chap, verses in (data.get('chapters') or {}).items():
            for vnum, words in verses.items():
                for w in words:
                    if w.get('s') == 'H7225':
                        new_gloss = classify(book_file, chap, vnum)
                        stats[new_gloss] += 1
                        total += 1
                        if w.get('g') != new_gloss:
                            w['g'] = new_gloss
                            file_changes += 1

        if apply_changes and file_changes:
            # Interlinear format: compact with separator ', ' and ': '
            write_json_preserve_bom(fp, data, bom, compact=True, sep_with_space=True)
            print(f'  [{fp.name}] {file_changes} updates')
            files_changed += 1
        elif file_changes and not apply_changes:
            print(f'  [{fp.name}] {file_changes} updates (dry-run)')

    print()
    print('=== Stats H7225 ===')
    print(f'  commencement : {stats[DEFAULT_GLOSS]}')
    print(f'  pre\u0301mices     : {stats[PREMICES_GLOSS]}')
    print(f'  le meilleur  : {stats[MEILLEUR_GLOSS]}')
    print(f'  TOTAL        : {total}')
    print(f'  files changed: {files_changed}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'=== H7225 gloss update {mode} ===')
    print()
    print('--- Lexicon ---')
    update_lexicon(args.apply)
    print()
    print('--- Interlinear ---')
    update_interlinear(args.apply)


if __name__ == '__main__':
    main()
