#!/usr/bin/env python3
"""
Construit un index unifié Strong → concepts pour la sidebar interlinéaire.

Fusionne :
  - concept-strong-map.json          (slug → [H...])  — noms propres majoritaires
  - concept-french-strong-map.json   (slug → [{s,h,x,g,pn}, ...])  — noms communs
  - concept-meta.json                (pour enrichir avec label + catégorie + url)
  - concept-url-slugs.json           (pour URL finalisée)

Sortie : uploads/dictionnaires/strong-to-concepts-index.json
Schéma :
  {
    "H1234": [
      {"slug": "alliance", "l": "Alliance", "c": "concept", "u": "alliance"},
      ...
    ]
  }

Usage :
  python scripts/build_strong_concepts_index.py
"""
import json
import os
import sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
IN_DIR = BASE / 'uploads' / 'dictionnaires'
OUT = IN_DIR / 'strong-to-concepts-index.json'


def read_json(path):
    with open(path, 'rb') as f:
        raw = f.read()
    if raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]
    return json.loads(raw.decode('utf-8'))


def main():
    meta = read_json(IN_DIR / 'concept-meta.json')
    url_map = read_json(IN_DIR / 'concept-url-slugs.json')
    strong_map = read_json(IN_DIR / 'concept-strong-map.json')
    fr_map = read_json(IN_DIR / 'concept-french-strong-map.json')

    # Index inversé : Strong → set(slug)
    reverse = defaultdict(set)

    for slug, strongs in strong_map.items():
        if isinstance(strongs, list):
            for s in strongs:
                if isinstance(s, str) and s.startswith('H'):
                    reverse[s].add(slug)

    for slug, entries in fr_map.items():
        if isinstance(entries, list):
            for e in entries:
                if isinstance(e, dict):
                    s = e.get('s')
                    if isinstance(s, str) and s.startswith('H'):
                        reverse[s].add(slug)

    # Enrichir chaque slug avec label + catégorie + url
    def enrich(slug):
        m = meta.get(slug) or {}
        label = m.get('l') or m.get('s') or slug
        cat = m.get('c') or ''
        url = url_map.get(slug) or m.get('u') or slug
        return {'slug': slug, 'l': label, 'c': cat, 'u': url}

    out = {}
    for strong, slugs in reverse.items():
        # Ordre : par longueur label asc (concepts simples d'abord) puis alpha
        enriched = [enrich(s) for s in sorted(slugs)]
        # Filtrer : retirer ceux dont le label est vide
        enriched = [e for e in enriched if e['l']]
        out[strong] = enriched

    # Stats
    total_strongs = len(out)
    total_pairs = sum(len(v) for v in out.values())
    mono = sum(1 for v in out.values() if len(v) == 1)
    multi = total_strongs - mono

    print(f'Strong indexés : {total_strongs}')
    print(f'  monovalents : {mono}')
    print(f'  multivalents : {multi}')
    print(f'Paires Strong↔concept : {total_pairs}')

    # Sanity
    print()
    print('=== Sanity checks ===')
    for s in ['H1285', 'H430', 'H3068', 'H7307', 'H2617', 'H120', 'H4941', 'H3414']:
        v = out.get(s)
        if v:
            labels = [f'{c["l"]} ({c["c"]})' for c in v[:5]]
            print(f'  {s}: {labels}')
        else:
            print(f'  {s}: (aucun concept)')

    # Écriture compacte
    payload = json.dumps(out, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    with open(OUT, 'wb') as f:
        f.write(payload)
    print()
    print(f'Fichier : {OUT}')
    print(f'Taille : {os.path.getsize(OUT):,} bytes ({os.path.getsize(OUT)/1024:.1f} KB)')


if __name__ == '__main__':
    main()
