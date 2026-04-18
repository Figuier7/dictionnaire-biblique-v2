#!/usr/bin/env python3
"""
Enrich Hebrew lexicon with root data from LexicalIndex.xml.

Resolves etymological roots via parent-child inheritance:
- etym type="main" root="xxx" → direct root
- etym type="sub" parent_id → inherit root from parent (recursive)

Outputs:
- hebrew-lexicon-fr-compact.json (enriched with 'r' field)
- strong-root-families-enriched.json (merged families for arbre view)
"""

import xml.etree.ElementTree as ET
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LI_PATH = os.path.join(BASE, 'HebrewLexicon-master', 'LexicalIndex.xml')
LEXICON_PATH = os.path.join(BASE, 'hebrew-lexicon-fr-compact.json')
FAMILIES_PATH = os.path.join(BASE, 'uploads', 'dictionnaires', 'strong-root-families.json')
OUT_LEXICON = LEXICON_PATH  # overwrite in place
OUT_FAMILIES = os.path.join(BASE, 'uploads', 'dictionnaires', 'strong-root-families-enriched.json')

NS = {'ns': 'http://openscriptures.github.com/morphhb/namespace'}


def parse_lexical_index():
    """Parse LexicalIndex.xml into a map of id -> entry data."""
    print(f'Parsing {LI_PATH}...')
    tree = ET.parse(LI_PATH)
    root = tree.getroot()
    entries = root.findall('.//ns:entry', NS)

    id_map = {}
    for e in entries:
        eid = e.get('id')
        etym = e.find('ns:etym', NS)
        xref = e.find('ns:xref', NS)

        strong = None
        if xref is not None and xref.get('strong'):
            strong = 'H' + xref.get('strong')

        etym_type = ''
        etym_root = ''
        parent_id = ''
        if etym is not None:
            etym_type = etym.get('type', '')
            etym_root = etym.get('root', '')
            if etym_type == 'sub' and etym.text:
                parent_id = etym.text.strip()

        id_map[eid] = {
            'strong': strong,
            'etym_type': etym_type,
            'etym_root': etym_root,
            'parent_id': parent_id,
        }

    print(f'  {len(id_map)} LI entries parsed')
    print(f'  {sum(1 for d in id_map.values() if d["strong"])} with Strong numbers')
    print(f'  {sum(1 for d in id_map.values() if d["etym_root"])} with direct root')
    print(f'  {sum(1 for d in id_map.values() if d["etym_type"] == "sub")} sub entries')
    return id_map


def resolve_roots(id_map):
    """Resolve root for every entry via parent-child inheritance."""
    cache = {}

    def _resolve(eid, visited=None):
        if eid in cache:
            return cache[eid]
        if visited is None:
            visited = set()
        if eid in visited:
            return ''
        visited.add(eid)

        entry = id_map.get(eid)
        if not entry:
            return ''
        if entry['etym_root']:
            cache[eid] = entry['etym_root']
            return entry['etym_root']
        if entry['parent_id']:
            result = _resolve(entry['parent_id'], visited)
            cache[eid] = result
            return result
        cache[eid] = ''
        return ''

    # Build strong -> root map
    strong_to_root = {}
    for eid, d in id_map.items():
        if not d['strong']:
            continue
        root = _resolve(eid)
        if root:
            strong_to_root[d['strong']] = root

    print(f'  {len(strong_to_root)} Strong IDs with resolved root')
    return strong_to_root


def enrich_lexicon(strong_to_root):
    """Add/update 'r' field in the compact lexicon JSON."""
    print(f'\nEnriching {LEXICON_PATH}...')
    with open(LEXICON_PATH, 'r', encoding='utf-8') as f:
        lexicon = json.load(f)

    before = sum(1 for e in lexicon if 'r' in e)
    added = 0
    kept = 0

    for entry in lexicon:
        s = entry.get('s', '')
        if s in strong_to_root:
            if 'r' not in entry:
                entry['r'] = strong_to_root[s]
                added += 1
            else:
                kept += 1  # already has root, keep it

    after = sum(1 for e in lexicon if 'r' in e)
    print(f'  Before: {before} entries with root')
    print(f'  Added: {added} new roots')
    print(f'  Kept: {kept} existing roots unchanged')
    print(f'  After: {after} entries with root ({after}/{len(lexicon)} = {after/len(lexicon)*100:.1f}%)')

    with open(OUT_LEXICON, 'w', encoding='utf-8') as f:
        json.dump(lexicon, f, ensure_ascii=False, separators=(',', ':'))
    print(f'  Written: {OUT_LEXICON}')

    return lexicon


def rebuild_families(lexicon, strong_to_root):
    """Rebuild strong-root-families.json by merging existing + new LI data."""
    print(f'\nRebuilding root families...')

    # Load existing families
    with open(FAMILIES_PATH, 'r', encoding='utf-8') as f:
        existing = json.load(f)
    print(f'  Existing: {len(existing)} Strong IDs')

    # Build lexicon lookup: strong -> { h, g, p }
    lex_map = {}
    for e in lexicon:
        s = e.get('s', '')
        lex_map[s] = {
            'h': e.get('h', ''),
            'g': e.get('g', [''])[0] if isinstance(e.get('g'), list) and e.get('g') else '',
            'p': e.get('p', ''),
        }

    # Merge: start with existing, add missing from LI
    merged = dict(existing)
    new_entries = 0
    for strong, root in strong_to_root.items():
        if strong not in merged:
            merged[strong] = {'r': root, 'f': []}
            new_entries += 1
        elif 'r' not in merged[strong] or not merged[strong]['r']:
            merged[strong]['r'] = root

    # Rebuild sibling lists for ALL entries
    # Group all Strong IDs by root
    root_groups = {}
    for strong, data in merged.items():
        r = data.get('r', '')
        if not r:
            continue
        if r not in root_groups:
            root_groups[r] = []
        root_groups[r].append(strong)

    # For each Strong ID, build the 'f' array (siblings = same root, excluding self)
    for strong, data in merged.items():
        r = data.get('r', '')
        if not r or r not in root_groups:
            continue
        siblings = []
        for sib_strong in root_groups[r]:
            if sib_strong == strong:
                continue
            info = lex_map.get(sib_strong, {})
            siblings.append({
                's': sib_strong,
                'h': info.get('h', ''),
                'g': info.get('g', ''),
                'p': info.get('p', ''),
            })
        data['f'] = siblings

    unique_roots = set(d.get('r', '') for d in merged.values() if d.get('r'))
    print(f'  New entries added: {new_entries}')
    print(f'  Total: {len(merged)} Strong IDs, {len(unique_roots)} unique roots')

    with open(OUT_FAMILIES, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, separators=(',', ':'))
    size_mb = os.path.getsize(OUT_FAMILIES) / 1024 / 1024
    print(f'  Written: {OUT_FAMILIES} ({size_mb:.1f} MB)')

    return merged


def main():
    print('=== Chantier 3D: Root Enrichment from LexicalIndex ===\n')

    id_map = parse_lexical_index()
    strong_to_root = resolve_roots(id_map)
    lexicon = enrich_lexicon(strong_to_root)
    families = rebuild_families(lexicon, strong_to_root)

    print('\n=== Done ===')
    print(f'Lexicon: {sum(1 for e in lexicon if "r" in e)}/{len(lexicon)} entries with root')
    print(f'Families: {len(families)} Strong IDs')


if __name__ == '__main__':
    main()
