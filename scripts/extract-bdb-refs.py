#!/usr/bin/env python3
"""Extract biblical references from BrownDriverBriggs.xml and add to compact lexicon."""
import xml.etree.ElementTree as ET
import json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BDB_PATH = os.path.join(BASE, 'HebrewLexicon-master', 'BrownDriverBriggs.xml')
LEXICON_PATH = os.path.join(BASE, 'hebrew-lexicon-fr-compact.json')

NS = {'ns': 'http://openscriptures.github.com/morphhb/namespace'}
MAX_REFS = 10  # max refs per entry to keep file size manageable


def extract_bdb_refs():
    """Extract <ref r="..."> from BDB entries, grouped by BDB entry ID."""
    print(f'Parsing {BDB_PATH}...')
    tree = ET.parse(BDB_PATH)
    root = tree.getroot()

    entries = root.findall('.//ns:entry', NS)
    bdb_refs = {}  # bdb_id -> [ref_strings]

    for entry in entries:
        eid = entry.get('id', '')
        if not eid:
            continue
        refs = entry.findall('.//ns:ref', NS)
        if not refs:
            continue
        ref_list = []
        seen = set()
        for ref in refs:
            r = ref.get('r', '')
            if r and r not in seen:
                seen.add(r)
                ref_list.append(r)
        if ref_list:
            bdb_refs[eid] = ref_list[:MAX_REFS]

    print(f'  {len(bdb_refs)} BDB entries with refs')
    total_refs = sum(len(v) for v in bdb_refs.values())
    print(f'  {total_refs} total refs (capped at {MAX_REFS}/entry)')
    return bdb_refs


def enrich_lexicon(bdb_refs):
    """Add refs field to compact lexicon entries via BDB ID mapping."""
    print(f'\nEnriching {LEXICON_PATH}...')
    with open(LEXICON_PATH, 'r', encoding='utf-8') as f:
        lexicon = json.load(f)

    before = sum(1 for e in lexicon if 'refs' in e)
    added = 0

    for entry in lexicon:
        bdb_id = entry.get('b', '')
        if not bdb_id:
            continue
        refs = bdb_refs.get(bdb_id)
        if refs:
            entry['refs'] = refs
            added += 1

    after = sum(1 for e in lexicon if 'refs' in e)
    print(f'  Before: {before} entries with refs')
    print(f'  Added: {added} entries')
    print(f'  After: {after} entries with refs ({after}/{len(lexicon)} = {after/len(lexicon)*100:.1f}%)')

    # Save
    with open(LEXICON_PATH, 'w', encoding='utf-8') as f:
        json.dump(lexicon, f, ensure_ascii=False, separators=(',', ':'))

    size_mb = os.path.getsize(LEXICON_PATH) / 1024 / 1024
    print(f'  File size: {size_mb:.1f} MB')

    # Show samples
    print(f'\n=== Samples ===')
    for entry in lexicon:
        if entry.get('refs') and len(entry['refs']) >= 2:
            print(f'  {entry["s"]} ({entry.get("h","")}) {entry.get("g",[""])[0] if entry.get("g") else ""}: {entry["refs"][:5]}')
            added -= 1
            if added < 2840:
                break

    return lexicon


def main():
    print('=== Chantier 3B: BDB Biblical References ===\n')
    bdb_refs = extract_bdb_refs()
    lexicon = enrich_lexicon(bdb_refs)
    print(f'\n=== Done ===')


if __name__ == '__main__':
    main()
