#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nettoyage des résidus 'base' / 'ref' en fin de BDB `df` + ponctuation de fin.

Cause : le pipeline de traduction BDB initial a extrait le texte XML sans
exclure les balises <status p="..." type="base"/> ou <status type="ref"/>.
Le type attr (valeur "base" ou "ref") s'est retrouvé textuellement concaténé
en fin de chaque df traduit.

Impact : ~7 151 entrées sur 8 669 (82 %) avec df terminant par 'base' ou 'ref'.

Ce script :
1. Détecte les suffixes indésirables : ' base', ' base.', ' ref', ' ref.',
   ' structure', ' note' (termes de métadonnées BDB).
2. Les retire proprement en préservant la ponctuation sémantique.
3. Ajoute un point final si la phrase termine sans ponctuation.

Usage :
  python scripts/clean_bdb_residues.py --dry-run
  python scripts/clean_bdb_residues.py --apply
"""

import argparse
import json
import re
import sys
from pathlib import Path
from collections import Counter


ROOT = Path(__file__).resolve().parent.parent
LEX_PATH = ROOT / 'uploads' / 'dictionnaires' / 'hebrew' / 'hebrew-lexicon-fr-compact.json'

# Suffixes parasites issus des balises <status type="..."/>
RESIDUE_SUFFIXES = [
    'base', 'ref', 'structure', 'note',
    'supplied', 'doubtful', 'corrupt', 'emendation',
]
# Pattern : (espace facultatif) + mot + (ponctuation finale facultative)
RESIDUE_RE = re.compile(
    r'\s+(?:' + '|'.join(RESIDUE_SUFFIXES) + r')\s*[.!?,;]?\s*$',
    re.IGNORECASE,
)

def clean_df(df):
    """Retourne (new_df, changed_bool)."""
    if not df:
        return df, False
    original = df
    new = df.rstrip()
    # Retire tous les suffixes parasites consécutifs (ex : 'base ref')
    while True:
        m = RESIDUE_RE.search(new)
        if not m:
            break
        new = new[:m.start()].rstrip()
    # Si le texte perd tout son contenu (cas extrême), on garde l'original
    if not new.strip():
        return original, False
    # Ajout ponctuation finale si absente et si différent de l'original
    if new != original.rstrip():
        # si dernier char n'est pas ponctuation, ajouter point
        if new and new[-1] not in '.!?…;)':
            new = new + '.'
        return new, True
    return original, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    if not args.dry_run and not args.apply:
        ap.error('Specify --dry-run or --apply')

    with open(LEX_PATH, 'r', encoding='utf-8-sig') as f:
        lex = json.load(f)

    changed_count = 0
    residue_hits = Counter()
    samples = []

    for e in lex:
        df = e.get('df') or ''
        if not df:
            continue
        new_df, changed = clean_df(df)
        if changed:
            changed_count += 1
            # detect which residue
            m = RESIDUE_RE.search(df)
            if m:
                residue_hits[m.group(0).strip().rstrip('.!?,;')] += 1
            if len(samples) < 8:
                samples.append({
                    's': e['s'],
                    'before': df[-80:],
                    'after': new_df[-80:],
                })
            if args.apply:
                e['df'] = new_df

    print(f'Total df entries with residue removed : {changed_count:,}')
    print(f'Residue type frequency :')
    for k, n in residue_hits.most_common():
        print(f'  {k!r}: {n:,}')
    print()
    print('Samples (before → after, last 80 chars):')
    for s in samples:
        print(f'  {s["s"]}:')
        print(f'    before: ...{s["before"]!r}')
        print(f'    after : ...{s["after"]!r}')

    if args.apply:
        with open(LEX_PATH, 'w', encoding='utf-8') as f:
            json.dump(lex, f, ensure_ascii=False, separators=(', ', ': '))
        print()
        print(f'Lexicon saved : {LEX_PATH}')
    else:
        print()
        print('(dry-run: no files written)')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    main()
