#!/usr/bin/env python3
"""
PHASE C - Soumet le batch de re-typage categories sur OpenAI.

Prerequis :
    export OPENAI_API_KEY="sk-..."
    pip install openai
    scripts/retype_categories_prepare.py deja execute

Usage :
    python scripts/retype_categories_submit.py

Output :
    work/retype/batch_meta.json  (contient file_id, batch_id, status)

Ensuite :
    - Attendre completion (qques heures typiquement)
    - Check status : python scripts/retype_categories_submit.py --status
    - Telecharger : python scripts/retype_categories_apply.py
"""
import argparse
import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'work/retype'
BATCH_INPUT = OUT_DIR / 'batch_input.jsonl'
BATCH_META = OUT_DIR / 'batch_meta.json'


def get_client():
    try:
        from openai import OpenAI
    except ImportError:
        print('ERROR: openai package not installed. Run: pip install openai', file=sys.stderr)
        sys.exit(1)
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print('ERROR: OPENAI_API_KEY env variable not set', file=sys.stderr)
        sys.exit(1)
    return OpenAI(api_key=api_key)


def submit(client):
    if not BATCH_INPUT.exists():
        print(f'ERROR: {BATCH_INPUT} missing. Run retype_categories_prepare.py first.', file=sys.stderr)
        sys.exit(1)
    size_mb = BATCH_INPUT.stat().st_size / (1024 * 1024)
    print(f'Uploading {BATCH_INPUT.name} ({size_mb:.1f} MB)...')
    with open(BATCH_INPUT, 'rb') as f:
        file_obj = client.files.create(file=f, purpose='batch')
    print(f'  file_id: {file_obj.id}')

    print('Creating batch job...')
    batch = client.batches.create(
        input_file_id=file_obj.id,
        endpoint='/v1/chat/completions',
        completion_window='24h',
        metadata={
            'project': 'figuier-concept-retype',
            'purpose': 'classify 9873 biblical concepts into 20-category taxonomy',
        }
    )
    print(f'  batch_id: {batch.id}')
    print(f'  status: {batch.status}')
    print(f'  request_counts: total={batch.request_counts.total}')

    meta = {
        'file_id': file_obj.id,
        'batch_id': batch.id,
        'status': batch.status,
        'created_at': batch.created_at,
        'request_total': batch.request_counts.total,
    }
    with open(BATCH_META, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)
    print(f'\nBatch metadata saved to {BATCH_META}')
    print('\nCheck status later with: python scripts/retype_categories_submit.py --status')


def status(client):
    if not BATCH_META.exists():
        print('ERROR: batch_meta.json missing. Submit first.', file=sys.stderr)
        sys.exit(1)
    with open(BATCH_META, encoding='utf-8') as f:
        meta = json.load(f)
    batch = client.batches.retrieve(meta['batch_id'])
    print(f"Batch ID     : {batch.id}")
    print(f"Status       : {batch.status}")
    print(f"Progress     : {batch.request_counts.completed}/{batch.request_counts.total}")
    if batch.request_counts.failed:
        print(f"Failed       : {batch.request_counts.failed}")
    if batch.output_file_id:
        print(f"Output ready : {batch.output_file_id}")
    if batch.error_file_id:
        print(f"Errors file  : {batch.error_file_id}")
    # Update meta
    meta['status'] = batch.status
    if batch.output_file_id:
        meta['output_file_id'] = batch.output_file_id
    if batch.error_file_id:
        meta['error_file_id'] = batch.error_file_id
    with open(BATCH_META, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)


def cancel(client):
    with open(BATCH_META, encoding='utf-8') as f:
        meta = json.load(f)
    batch = client.batches.cancel(meta['batch_id'])
    print(f'Batch {batch.id} status: {batch.status}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--status', action='store_true', help='Check batch status')
    p.add_argument('--cancel', action='store_true', help='Cancel the batch')
    args = p.parse_args()
    client = get_client()
    if args.status:
        status(client)
    elif args.cancel:
        cancel(client)
    else:
        submit(client)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
