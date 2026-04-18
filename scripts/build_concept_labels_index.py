#!/usr/bin/env python3
"""
Construit un sous-index léger des labels de concepts pour l'interlinéaire.

Source : uploads/dictionnaires/concept-meta.json (3 MB, 9873 concepts)
Sortie : uploads/dictionnaires/concept-labels.json (~300 KB)

Schéma :
  { slug: {l: label, c: category, u: url_slug} }

Usage :
  python scripts/build_concept_labels_index.py
"""
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
IN_META = BASE / 'uploads' / 'dictionnaires' / 'concept-meta.json'
IN_URL = BASE / 'uploads' / 'dictionnaires' / 'concept-url-slugs.json'
IN_STRONG_MAP = BASE / 'uploads' / 'dictionnaires' / 'concept-strong-map.json'
OUT = BASE / 'uploads' / 'dictionnaires' / 'concept-labels.json'


def read_json(path):
    with open(path, 'rb') as f:
        raw = f.read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    if bom:
        raw = raw[3:]
    return json.loads(raw.decode('utf-8')), bom


def main():
    meta, _ = read_json(IN_META)
    url_map, _ = read_json(IN_URL)
    strong_map, _ = read_json(IN_STRONG_MAP)

    # On ne conserve que les concepts qui ont au moins un Strong mappé
    slugs_with_strong = set(strong_map.keys())

    out = {}
    for slug, m in meta.items():
        if slug not in slugs_with_strong:
            continue
        label = m.get('l') or m.get('s') or slug
        cat = m.get('c') or ''
        url = url_map.get(slug) or m.get('u') or slug
        out[slug] = {'l': label, 'c': cat, 'u': url}

    # Écriture compacte (pas de BOM, séparateurs compacts)
    payload = json.dumps(out, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    with open(OUT, 'wb') as f:
        f.write(payload)

    print(f'Concepts indexés : {len(out)}')
    print(f'Fichier : {OUT}')
    print(f'Taille : {os.path.getsize(OUT):,} bytes ({os.path.getsize(OUT)/1024:.1f} KB)')

    # Sanity : quelques exemples
    for k in ['paulos', 'yirmeyah', 'alliance', 'byssus', 'lin']:
        if k in out:
            print(f'  {k:<15} -> {out[k]}')


if __name__ == '__main__':
    main()
