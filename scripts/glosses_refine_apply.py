#!/usr/bin/env python3
"""
Affinage glosses interlineaires - Telechargement + application des resultats.

Prerequis :
    batch completed (verify avec scripts/glosses_refine_submit.py --status)
    export OPENAI_API_KEY="sk-..."

Usage :
    python scripts/glosses_refine_apply.py             # download + dry run
    python scripts/glosses_refine_apply.py --commit    # applique vraiment

Effets :
    - Telecharge batch_output.jsonl dans work/glosses/
    - Parse les glosses retournes, sanitize
    - Ajoute champ 'ig' (interlinear gloss) dans hebrew-lexicon-fr-compact.json
    - Re-patche les 39 JSON interlinear avec nouveau champ 'g'
    - Rapport dans work/glosses/refine_report.json

Backup :
    hebrew-lexicon-fr-compact.json.bak-pre-ig
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'work/glosses'
BATCH_META = OUT_DIR / 'batch_meta.json'
BATCH_OUTPUT = OUT_DIR / 'batch_output.jsonl'
REPORT_FILE = OUT_DIR / 'refine_report.json'

LEX_PATH = BASE / 'uploads/dictionnaires/hebrew/hebrew-lexicon-fr-compact.json'
INTERLIN_DIR = BASE / 'uploads/dictionnaires/interlinear'


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


def sanitize_gloss(g):
    """Clean gloss : strip, lowercase proper-casing."""
    if not g: return ''
    g = str(g).strip()
    # Retire guillemets
    g = g.strip('"\'`')
    # Retire points finaux
    g = g.rstrip('.;,:')
    # Retire doubles espaces
    while '  ' in g: g = g.replace('  ', ' ')
    return g.strip()


def parse_and_apply(commit=False):
    import re as _re

    new_glosses = {}
    errors = []
    n_processed = 0
    n_chunks = 0

    def clean_json_content(s):
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
                errors.append(f'{chunk_id}: status={response.get("status_code","?")}')
                continue

            body = response.get('body') or {}
            choices = body.get('choices') or []
            if not choices:
                errors.append(f'{chunk_id}: no choices')
                continue
            content = (choices[0].get('message') or {}).get('content', '').strip()
            content = clean_json_content(content)
            try:
                arr = json.loads(content)
            except Exception:
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
                s = item.get('s', '') or item.get('strong', '')
                g = sanitize_gloss(item.get('g', '') or item.get('gloss', ''))
                if s and g:
                    new_glosses[s] = g

    print(f'Chunks processed  : {n_chunks}')
    print(f'Entries parsed    : {n_processed}')
    print(f'Valid glosses     : {len(new_glosses)}')
    print(f'Errors            : {len(errors)}')

    # Load current lexicon pour comparer
    with open(LEX_PATH, encoding='utf-8') as f:
        lex = json.load(f)
    current_by_s = {e['s']: e for e in lex}

    same_count = 0
    changed_count = 0
    missing_count = 0
    sample_changes = []
    for s, new_g in new_glosses.items():
        e = current_by_s.get(s)
        if not e:
            missing_count += 1
            continue
        old_g = (e.get('g') or [''])[0] if isinstance(e.get('g'), list) else ''
        if old_g == new_g:
            same_count += 1
        else:
            changed_count += 1
            if len(sample_changes) < 40:
                sample_changes.append({'s': s, 'x': e.get('x',''), 'old': old_g, 'new': new_g})

    print(f'\n=== Impact ===')
    print(f'Same as before   : {same_count}')
    print(f'Changed          : {changed_count}')
    print(f'Missing in lex   : {missing_count}')

    print(f'\nSample changes (20) :')
    for c in sample_changes[:20]:
        print(f'  {c["s"]:7s} {c["x"][:18]:18s}  "{c["old"]}" -> "{c["new"]}"')

    report = {
        'n_processed': n_processed,
        'valid': len(new_glosses),
        'same': same_count,
        'changed': changed_count,
        'missing': missing_count,
        'errors': len(errors),
        'sample_changes': sample_changes,
    }
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'\nReport saved to {REPORT_FILE}')

    if not commit:
        print('\n--- DRY RUN (no files written). Add --commit to apply. ---')
        return

    # Backup lexicon
    bak = LEX_PATH.with_suffix(LEX_PATH.suffix + '.bak-pre-ig')
    if not bak.exists():
        bak.write_bytes(LEX_PATH.read_bytes())
        print(f'Backup: {bak}')

    # Add 'ig' field to each entry
    n_updated_lex = 0
    for e in lex:
        s = e.get('s', '')
        if s in new_glosses:
            e['ig'] = new_glosses[s]
            n_updated_lex += 1
    with open(LEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(lex, f, ensure_ascii=False, separators=(',', ':'))
    print(f'Updated {n_updated_lex} entries in {LEX_PATH.name} (field "ig")')

    # Re-patch 39 interlinear JSON files (overwrite 'g' field)
    print('\nRe-patching 39 interlinear JSON files...')
    n_words_updated = 0
    for f_path in sorted(INTERLIN_DIR.glob('*.json')):
        with open(f_path, encoding='utf-8') as f:
            data = json.load(f)
        file_updates = 0
        for chap_num, verses in data.get('chapters', {}).items():
            for v_num, words in verses.items():
                for w in words:
                    s = w.get('s', '')
                    if s in new_glosses:
                        new_g = new_glosses[s]
                        if w.get('g') != new_g:
                            w['g'] = new_g
                            file_updates += 1
        if file_updates:
            with open(f_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
            n_words_updated += file_updates
        print(f'  {f_path.name:20s} : {file_updates:>6} words updated')
    print(f'\nTotal words updated across 39 books: {n_words_updated}')

    print('\n[OK] Glosses applied.')
    print('Next steps :')
    print('  1. Upload hebrew-lexicon-fr-compact.json to server')
    print('  2. Upload uploads/dictionnaires/interlinear/*.json to server')
    print('  3. Purge LiteSpeed cache + touch filemtime')


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
