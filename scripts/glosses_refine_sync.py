#!/usr/bin/env python3
"""
Mode sync (non-batch) du refinement des glosses.

Bypass complet de la Batch API d'OpenAI (qui est saturee).
Utilise /v1/chat/completions avec ThreadPoolExecutor pour paralleliser.

Rate limit par defaut : 10 workers concurrents, ~1 req/sec/worker.
Avec gpt-4o-mini : ~3500 req/min de limite, on est largement dessous.

Output format : identique au batch output (un JSON par ligne avec custom_id +
response.body), pour etre compatible avec glosses_refine_apply.py.

Usage:
    python scripts/glosses_refine_sync.py              # defaut 10 workers
    python scripts/glosses_refine_sync.py --workers 20 # plus agressif
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'work/glosses'
LOG_FILE = OUT_DIR / 'sync.log'
INPUT_JSONL = OUT_DIR / 'batch_input.jsonl'
OUTPUT_JSONL = OUT_DIR / 'batch_output_merged.jsonl'


def log(msg):
    stamp = datetime.now().strftime('%H:%M:%S')
    line = f'[{stamp}] {msg}'
    print(line, flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {msg}\n')


def process_request(req_spec, api_key, max_retries=3):
    """Process one request in sync mode.

    req_spec: dict with keys custom_id, method, url, body
    Returns: dict with custom_id and response (or error)
    """
    custom_id = req_spec.get('custom_id')
    body = req_spec.get('body', {})

    data = json.dumps(body).encode('utf-8')
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                'https://api.openai.com/v1/chat/completions',
                data=data,
                method='POST',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                response_body = json.loads(resp.read())
            return {
                'id': f'resp-{custom_id}',
                'custom_id': custom_id,
                'response': {
                    'status_code': 200,
                    'request_id': resp.headers.get('x-request-id', ''),
                    'body': response_body,
                },
                'error': None,
            }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')
            # Retry on 429 (rate limit) or 5xx
            if e.code == 429 or e.code >= 500:
                backoff = 2 ** attempt
                time.sleep(backoff)
                continue
            return {
                'id': f'resp-{custom_id}',
                'custom_id': custom_id,
                'response': None,
                'error': {'code': str(e.code), 'message': err_body[:500]},
            }
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {
                'id': f'resp-{custom_id}',
                'custom_id': custom_id,
                'response': None,
                'error': {'code': 'exception', 'message': str(e)[:500]},
            }
    return {
        'id': f'resp-{custom_id}',
        'custom_id': custom_id,
        'response': None,
        'error': {'code': 'max_retries', 'message': 'All retries exhausted'},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=10)
    args = parser.parse_args()

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print('ERROR: OPENAI_API_KEY not set', file=sys.stderr)
        return 1

    if not INPUT_JSONL.exists():
        print(f'ERROR: {INPUT_JSONL} not found', file=sys.stderr)
        return 1

    # Load all requests
    requests = []
    with open(INPUT_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                requests.append(json.loads(line))

    total = len(requests)
    log(f'=== SYNC MODE START: {total} requests, {args.workers} workers ===')

    # Detect already-processed requests (to resume)
    done_ids = set()
    if OUTPUT_JSONL.exists():
        with open(OUTPUT_JSONL, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get('error') is None:
                        done_ids.add(entry.get('custom_id'))
                except json.JSONDecodeError:
                    pass
    if done_ids:
        log(f'Resume: {len(done_ids)} requests already completed, skipping')

    todo = [r for r in requests if r.get('custom_id') not in done_ids]
    log(f'To process: {len(todo)} requests')

    if not todo:
        log('Nothing to do, exiting')
        return 0

    t_start = time.time()
    completed = 0
    failed = 0
    lock_open = open(OUTPUT_JSONL, 'a', encoding='utf-8', buffering=1)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_request, r, api_key): r for r in todo}
        for fut in as_completed(futures):
            result = fut.result()
            lock_open.write(json.dumps(result, ensure_ascii=False) + '\n')
            if result['error'] is None:
                completed += 1
            else:
                failed += 1
                log(f'FAIL {result["custom_id"]}: {result["error"]["code"]} - {result["error"]["message"][:150]}')
            # Progress every 10
            if (completed + failed) % 10 == 0:
                elapsed = time.time() - t_start
                rate = (completed + failed) / elapsed if elapsed > 0 else 0
                eta = (len(todo) - completed - failed) / rate if rate > 0 else 0
                log(f'progress {completed + failed}/{len(todo)} ok={completed} fail={failed} rate={rate:.1f}/s ETA={eta:.0f}s')

    lock_open.close()
    elapsed = time.time() - t_start
    log(f'=== DONE in {elapsed:.0f}s : {completed} ok, {failed} failed ===')
    log(f'Output: {OUTPUT_JSONL}')
    return 0 if failed == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
