"""
Phase 2 du chantier Lin/Byssus/Renvois.

Corrections:
  1. concepts.json         : byssus.category objets_et_vetements -> matiere
  2. concept-meta.json     : byssus.c         objets_et_vetements -> matiere
  3. isbe/isbe-B.json      : isbe-001706.definition 'Voir LIN (tissu).' -> 'Voir Lin (tissu).'

Preserve l'encodage BOM/no-BOM de chaque fichier.
Usage:
  python scripts/fix_phase2_byssus.py          # dry-run
  python scripts/fix_phase2_byssus.py --apply  # ecrit
"""
import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONCEPTS_PATH    = os.path.join(ROOT, 'uploads', 'dictionnaires', 'concepts.json')
CONCEPT_META     = os.path.join(ROOT, 'uploads', 'dictionnaires', 'concept-meta.json')
ISBE_B_PATH      = os.path.join(ROOT, 'uploads', 'dictionnaires', 'isbe', 'isbe-B.json')


def read_json_preserve_bom(path):
    with open(path, 'rb') as f:
        raw = f.read()
    has_bom = raw.startswith(b'\xef\xbb\xbf')
    if has_bom:
        raw = raw[3:]
    data = json.loads(raw.decode('utf-8'))
    return data, has_bom


def write_json_preserve_bom(path, data, has_bom, separators=(',', ':')):
    """Write compact JSON (no newlines/indent), preserving BOM state and
    the file-specific separator convention."""
    payload = json.dumps(data, ensure_ascii=False, separators=separators)
    body = payload.encode('utf-8')
    if has_bom:
        body = b'\xef\xbb\xbf' + body
    with open(path, 'wb') as f:
        f.write(body)


def fix_concepts(apply_changes):
    data, has_bom = read_json_preserve_bom(CONCEPTS_PATH)
    if not isinstance(data, list):
        raise RuntimeError('concepts.json expected list')
    target = None
    for c in data:
        if c.get('concept_id') == 'byssus':
            target = c
            break
    if target is None:
        raise RuntimeError("concept 'byssus' not found in concepts.json")
    before = target.get('category')
    if before == 'matiere':
        print(f'  [concepts.json] byssus.category already "matiere" - skip')
        return False
    target['category'] = 'matiere'
    print(f'  [concepts.json] byssus.category: {before!r} -> "matiere"')
    if apply_changes:
        # concepts.json : compact, separators=(',',':')
        write_json_preserve_bom(CONCEPTS_PATH, data, has_bom, separators=(',', ':'))
    return True


def fix_concept_meta(apply_changes):
    data, has_bom = read_json_preserve_bom(CONCEPT_META)
    if not isinstance(data, dict):
        raise RuntimeError('concept-meta.json expected dict')
    if 'byssus' not in data:
        raise RuntimeError("'byssus' missing from concept-meta.json")
    before = data['byssus'].get('c')
    if before == 'matiere':
        print(f'  [concept-meta.json] byssus.c already "matiere" - skip')
        return False
    data['byssus']['c'] = 'matiere'
    print(f'  [concept-meta.json] byssus.c: {before!r} -> "matiere"')
    if apply_changes:
        # concept-meta.json : compact, separators=(',',':')
        write_json_preserve_bom(CONCEPT_META, data, has_bom, separators=(',', ':'))
    return True


def fix_isbe_byssus(apply_changes):
    data, has_bom = read_json_preserve_bom(ISBE_B_PATH)
    items = data if isinstance(data, list) else data.get('entries', data)
    target = None
    if isinstance(items, list):
        for e in items:
            if (e.get('entry_id') or e.get('id')) == 'isbe-001706':
                target = e
                break
    elif isinstance(items, dict):
        target = items.get('isbe-001706')
    if target is None:
        raise RuntimeError("isbe-001706 not found in isbe-B.json")
    before = target.get('definition', '')
    fixed = before.replace('Voir LIN (tissu).', 'Voir Lin (tissu).')
    if fixed == before:
        print(f'  [isbe-B.json] isbe-001706.definition unchanged - skip (current: {before!r})')
        return False
    target['definition'] = fixed
    print(f'  [isbe-B.json] isbe-001706.definition: {before!r} -> {fixed!r}')
    if apply_changes:
        # isbe-B.json : compact with space after colon AND after comma
        # separators=(', ', ': ') matches original format
        write_json_preserve_bom(ISBE_B_PATH, data, has_bom, separators=(', ', ': '))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='write changes to disk')
    args = ap.parse_args()

    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'=== Phase 2 (Byssus corrections) {mode} ===')
    changed = 0
    if fix_concepts(args.apply):       changed += 1
    if fix_concept_meta(args.apply):   changed += 1
    if fix_isbe_byssus(args.apply):    changed += 1
    print()
    print(f'{changed} file(s) would be modified' if not args.apply else f'{changed} file(s) written')


if __name__ == '__main__':
    main()
