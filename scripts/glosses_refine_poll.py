#!/usr/bin/env python3
"""
Polling periodique du batch OpenAI en arriere-plan.

Interroge le statut toutes les 5 minutes et log dans work/glosses/poll.log.
S'arrete automatiquement quand status est completed / failed / cancelled / expired.

Usage :
    py scripts/glosses_refine_poll.py                 # boucle jusqu'a fin
    py scripts/glosses_refine_poll.py --interval 180  # polling 3 min

Le log est ecrit en append : tail work/glosses/poll.log pour suivre.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'work/glosses'
BATCH_META = OUT_DIR / 'batch_meta.json'
LOG_FILE = OUT_DIR / 'poll.log'
TERMINAL = {'completed', 'failed', 'cancelled', 'expired'}


def log(msg):
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{stamp}] {msg}'
    print(line, flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', type=int, default=300, help='Intervalle en secondes (defaut 300)')
    args = parser.parse_args()

    try:
        from openai import OpenAI
    except ImportError:
        print('pip install openai', file=sys.stderr); sys.exit(1)
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        print('OPENAI_API_KEY missing', file=sys.stderr); sys.exit(1)
    client = OpenAI(api_key=key)

    if not BATCH_META.exists():
        print(f'ERROR: {BATCH_META} missing', file=sys.stderr); sys.exit(1)
    with open(BATCH_META, encoding='utf-8') as f:
        meta = json.load(f)
    batch_id = meta['batch_id']

    log(f'Start polling batch {batch_id} every {args.interval}s')

    last_status = None
    last_completed = -1
    try:
        while True:
            try:
                batch = client.batches.retrieve(batch_id)
            except Exception as e:
                log(f'ERROR retrieving batch: {e}')
                time.sleep(args.interval)
                continue

            status = batch.status
            done = getattr(batch.request_counts, 'completed', 0) or 0
            total = getattr(batch.request_counts, 'total', 0) or 0
            failed = getattr(batch.request_counts, 'failed', 0) or 0

            if status != last_status or done != last_completed:
                msg = f'status={status} progress={done}/{total}'
                if failed:
                    msg += f' failed={failed}'
                log(msg)
                last_status = status
                last_completed = done

                meta['status'] = status
                if batch.output_file_id:
                    meta['output_file_id'] = batch.output_file_id
                if batch.error_file_id:
                    meta['error_file_id'] = batch.error_file_id
                with open(BATCH_META, 'w', encoding='utf-8') as f:
                    json.dump(meta, f, indent=2)

            if status in TERMINAL:
                log(f'BATCH TERMINAL: {status}')
                if status == 'completed':
                    log(f'output_file_id = {batch.output_file_id}')
                    log('Ready to apply: py scripts/glosses_refine_apply.py --commit')
                break

            time.sleep(args.interval)
    except KeyboardInterrupt:
        log('Polling interrupted by user')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
