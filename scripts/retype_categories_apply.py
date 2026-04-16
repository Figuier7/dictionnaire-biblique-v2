#!/usr/bin/env python3
"""
PHASE D - Telecharge batch output + applique les nouvelles categories.

Prerequis :
    batch completed (verify avec scripts/retype_categories_submit.py --status)
    export OPENAI_API_KEY="sk-..."

Usage :
    python scripts/retype_categories_apply.py             # download + apply (dry run)
    python scripts/retype_categories_apply.py --commit    # applique vraiment

Effets :
    - Telecharge batch_output.jsonl dans work/retype/
    - Parse les categories retournees, valide contre la taxonomie
    - Met a jour concept-meta.json (champ 'c')
    - Met a jour concepts.json (champ 'category')
    - Rapport complet dans work/retype/retype_report.json

Backups :
    concept-meta.json.bak-pre-retype
    concepts.json.bak-pre-retype
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'work/retype'
BATCH_META = OUT_DIR / 'batch_meta.json'
BATCH_OUTPUT = OUT_DIR / 'batch_output.jsonl'
TAXONOMY_FILE = OUT_DIR / 'taxonomy.json'
REPORT_FILE = OUT_DIR / 'retype_report.json'

META_PATH = BASE / 'uploads/dictionnaires/concept-meta.json'
CONCEPTS_PATH = BASE / 'uploads/dictionnaires/concepts.json'


def get_client():
    try:
        from openai import OpenAI
    except ImportError:
        print('pip install openai', file=sys.stderr); sys.exit(1)
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        print('OPENAI_API_KEY missing', file=sys.stderr); sys.exit(1)
    return OpenAI(api_key=key)


def download():
    if BATCH_OUTPUT.exists():
        print(f'{BATCH_OUTPUT} already exists; skipping download')
        return
    client = get_client()
    with open(BATCH_META, encoding='utf-8') as f:
        meta = json.load(f)
    batch = client.batches.retrieve(meta['batch_id'])
    if batch.status != 'completed':
        print(f'ERROR: batch status = {batch.status}, need "completed"', file=sys.stderr)
        sys.exit(1)
    if not batch.output_file_id:
        print('ERROR: no output_file_id', file=sys.stderr)
        sys.exit(1)
    print(f'Downloading output file {batch.output_file_id}...')
    content = client.files.content(batch.output_file_id)
    BATCH_OUTPUT.write_bytes(content.read())
    print(f'Saved to {BATCH_OUTPUT} ({BATCH_OUTPUT.stat().st_size / 1024:.1f} KB)')


def parse_and_apply(commit=False):
    with open(TAXONOMY_FILE, encoding='utf-8') as f:
        taxonomy = set(json.load(f)['taxonomy'])

    with open(META_PATH, encoding='utf-8') as f:
        meta = json.load(f)
    with open(CONCEPTS_PATH, encoding='utf-8') as f:
        concepts = json.load(f)

    # Parse batch output (format : JSON array par chunk)
    import re as _re
    new_cats = {}
    errors = []
    invalid_categories = []
    n_processed = 0
    n_chunks = 0

    def clean_json_content(s):
        """Enleve d'eventuels markdown code fences."""
        s = s.strip()
        if s.startswith('```'):
            s = _re.sub(r'^```(?:json)?\s*\n?', '', s)
            s = _re.sub(r'\n?```\s*$', '', s)
        return s.strip()

    with open(BATCH_OUTPUT, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            n_chunks += 1
            try:
                record = json.loads(line)
            except Exception as e:
                errors.append(f'parse error outer: {e}')
                continue

            chunk_id = record.get('custom_id', '')
            response = record.get('response') or {}
            if not response or response.get('status_code') != 200:
                errors.append(f'{chunk_id}: status={response.get("status_code","?")} err={record.get("error")}')
                continue

            body = response.get('body') or {}
            choices = body.get('choices') or []
            if not choices:
                errors.append(f'{chunk_id}: no choices')
                continue
            content = (choices[0].get('message') or {}).get('content', '').strip()
            content = clean_json_content(content)
            # Parse JSON array
            try:
                arr = json.loads(content)
            except Exception:
                # Essayer d'extraire [ ... ]
                m = _re.search(r'\[\s*\{.*\}\s*\]', content, _re.DOTALL)
                if m:
                    try: arr = json.loads(m.group(0))
                    except: arr = None
                else:
                    arr = None
            if not isinstance(arr, list):
                errors.append(f'{chunk_id}: not a JSON array (content[:150]={content[:150]!r})')
                continue

            for item in arr:
                n_processed += 1
                if not isinstance(item, dict): continue
                cid = item.get('cid', '') or item.get('concept_id', '')
                cat = (item.get('cat') or item.get('category') or '').strip().lower()
                cat = cat.replace(' ', '_').replace('-', '_').rstrip('.')
                if cid and cat:
                    if cat in taxonomy:
                        new_cats[cid] = cat
                    else:
                        invalid_categories.append({'cid': cid, 'raw': cat, 'chunk': chunk_id})

    print(f'Chunks processed  : {n_chunks}')
    print(f'Concepts parsed   : {n_processed}')
    print(f'Valid categories  : {len(new_cats)}')
    print(f'Invalid responses : {len(invalid_categories)}')
    print(f'Parse errors      : {len(errors)}')

    # Compute diff stats
    diff_stats = Counter()
    same_count = 0
    changes_by_direction = Counter()
    for cid, new_cat in new_cats.items():
        m = meta.get(cid, {})
        old_cat = m.get('c', '')
        if old_cat == new_cat:
            same_count += 1
        else:
            diff_stats[new_cat] += 1
            changes_by_direction[f'{old_cat} -> {new_cat}'] += 1

    print(f'\n=== Impact ===')
    print(f'Unchanged         : {same_count}')
    print(f'Changed           : {len(new_cats) - same_count}')
    print(f'\nTop 15 directions de changement :')
    for direction, count in changes_by_direction.most_common(15):
        print(f'  {direction:40s} : {count}')

    print(f'\nNouvelles categories (top 15) :')
    new_dist = Counter(new_cats.values())
    for cat, count in new_dist.most_common():
        old = sum(1 for v in meta.values() if v.get('c') == cat)
        print(f'  {cat:32s} : {count:>5} (avant: {old})')

    # Sample invalid
    if invalid_categories:
        print(f'\n=== {len(invalid_categories)} reponses invalides (10 premieres) ===')
        for inv in invalid_categories[:10]:
            print(f'  {inv["cid"]:25s} : raw={inv["raw"]!r}')

    report = {
        'n_processed': n_processed,
        'valid': len(new_cats),
        'invalid': len(invalid_categories),
        'errors': len(errors),
        'unchanged': same_count,
        'changed': len(new_cats) - same_count,
        'new_distribution': dict(new_dist),
        'top_directions': dict(changes_by_direction.most_common(30)),
        'invalid_samples': invalid_categories[:50],
    }
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'\nReport saved to {REPORT_FILE}')

    if not commit:
        print('\n--- DRY RUN (no files written). Add --commit to apply. ---')
        return

    # Backup + apply
    for path in (META_PATH, CONCEPTS_PATH):
        bak = path.with_suffix(path.suffix + '.bak-pre-retype')
        if not bak.exists():
            bak.write_bytes(path.read_bytes())
            print(f'Backup: {bak}')

    # Update concept-meta.json
    n_updated_meta = 0
    for cid, new_cat in new_cats.items():
        if cid in meta and meta[cid].get('c') != new_cat:
            meta[cid]['c'] = new_cat
            n_updated_meta += 1
    with open(META_PATH, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, separators=(',',':'))
    print(f'Updated {n_updated_meta} entries in {META_PATH.name}')

    # Update concepts.json (list)
    n_updated_concepts = 0
    for c in concepts:
        cid = c.get('concept_id') or c.get('slug') or c.get('id')
        if cid and cid in new_cats and c.get('category') != new_cats[cid]:
            c['category'] = new_cats[cid]
            n_updated_concepts += 1
    with open(CONCEPTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(concepts, f, ensure_ascii=False, separators=(',',':'))
    print(f'Updated {n_updated_concepts} entries in {CONCEPTS_PATH.name}')

    print('\n[OK] Categories applied to JSON files.')
    print('Next steps :')
    print('  1. Regenerate browse-index.json : python scripts/sync_browse_index.py')
    print('  2. Re-audit hebrew mappings     : python scripts/reaudit_hebrew_mappings.py')
    print('  3. Upload to server + purge cache')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--commit', action='store_true', help='Apply changes (otherwise dry run)')
    p.add_argument('--skip-download', action='store_true', help='Assume batch_output.jsonl already local')
    args = p.parse_args()

    if not args.skip_download:
        download()

    parse_and_apply(commit=args.commit)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
