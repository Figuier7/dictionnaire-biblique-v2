#!/usr/bin/env python3
"""
Soumet le batch glosses en 3 chunks sequentiels, en respectant la limite
d'enqueued tokens OpenAI (90K pour gpt-4o, ~1.5M pour gpt-4o-mini mais peut varier).

Strategie:
  1. Split batch_input.jsonl en N chunks (par defaut 3)
  2. Pour chaque chunk:
     a. Upload le fichier
     b. Submit le batch
     c. Poll jusqu'a status terminal (completed / failed / cancelled / expired)
     d. Log progression dans work/glosses/sequential.log
  3. Si tous completed: fusionner les output files en un seul result
  4. Si un fail: stopper et logguer

Usage:
    python scripts/glosses_refine_sequential.py                 # defaut 3 chunks
    python scripts/glosses_refine_sequential.py --chunks 4      # 4 chunks
    python scripts/glosses_refine_sequential.py --interval 180  # poll 3min (defaut 300s)
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'work/glosses'
LOG_FILE = OUT_DIR / 'sequential.log'
INPUT_JSONL = OUT_DIR / 'batch_input.jsonl'
STATE_FILE = OUT_DIR / 'sequential_state.json'
TERMINAL = {'completed', 'failed', 'cancelled', 'expired'}


def log(msg):
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{stamp}] {msg}'
    print(line, flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def api_request(method, path, api_key, body=None, multipart=None):
    """Helper for OpenAI API requests."""
    url = f'https://api.openai.com/v1{path}'
    headers = {'Authorization': f'Bearer {api_key}'}
    if multipart:
        boundary, payload = multipart
        headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
        data = payload
    elif body is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(body).encode('utf-8')
    else:
        data = None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def upload_file(jsonl_path, api_key):
    with open(jsonl_path, 'rb') as f:
        file_bytes = f.read()
    boundary = '----SEQBOUNDARY'
    body = b''
    body += f'--{boundary}\r\n'.encode()
    body += b'Content-Disposition: form-data; name="purpose"\r\n\r\n'
    body += b'batch\r\n'
    body += f'--{boundary}\r\n'.encode()
    body += f'Content-Disposition: form-data; name="file"; filename="{jsonl_path.name}"\r\n'.encode()
    body += b'Content-Type: application/jsonl\r\n\r\n'
    body += file_bytes + b'\r\n'
    body += f'--{boundary}--\r\n'.encode()
    return api_request('POST', '/files', api_key, multipart=(boundary, body))


def create_batch(file_id, api_key, metadata_name):
    return api_request('POST', '/batches', api_key, body={
        'input_file_id': file_id,
        'endpoint': '/v1/chat/completions',
        'completion_window': '24h',
        'metadata': {'name': metadata_name, 'source': 'hebrew-lexicon'},
    })


def get_batch(batch_id, api_key):
    return api_request('GET', f'/batches/{batch_id}', api_key)


def download_file(file_id, api_key):
    url = f'https://api.openai.com/v1/files/{file_id}/content'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {api_key}'})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode('utf-8')


def split_jsonl(input_path, n_chunks, out_dir):
    """Split input jsonl into n_chunks roughly equal sized files."""
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = [line for line in f if line.strip()]
    total = len(lines)
    per_chunk = (total + n_chunks - 1) // n_chunks
    chunks = []
    for i in range(n_chunks):
        slice_lines = lines[i * per_chunk : (i + 1) * per_chunk]
        if not slice_lines:
            continue
        out_path = out_dir / f'batch_input_part{i+1:02d}.jsonl'
        with open(out_path, 'w', encoding='utf-8') as f:
            for l in slice_lines:
                f.write(l if l.endswith('\n') else l + '\n')
        chunks.append({'index': i + 1, 'path': out_path, 'n_requests': len(slice_lines)})
    return chunks


def run_chunk(chunk, api_key, poll_interval):
    """Run a single chunk: upload, submit, poll until terminal, return result."""
    log(f'[chunk {chunk["index"]}] uploading {chunk["path"].name} ({chunk["n_requests"]} requests)')
    file_data = upload_file(chunk['path'], api_key)
    file_id = file_data['id']
    log(f'[chunk {chunk["index"]}] file uploaded: {file_id} ({file_data["bytes"]} bytes)')

    batch_data = create_batch(file_id, api_key, f'glosses_refine_part{chunk["index"]}')
    batch_id = batch_data['id']
    log(f'[chunk {chunk["index"]}] batch created: {batch_id} status={batch_data["status"]}')

    # Poll until terminal
    while True:
        time.sleep(poll_interval)
        try:
            data = get_batch(batch_id, api_key)
        except Exception as e:
            log(f'[chunk {chunk["index"]}] poll error: {e}')
            continue
        status = data['status']
        counts = data.get('request_counts', {})
        log(f'[chunk {chunk["index"]}] status={status} completed={counts.get("completed", 0)}/{counts.get("total", 0)} failed={counts.get("failed", 0)}')
        if status in TERMINAL:
            return data


def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chunks', type=int, default=3)
    parser.add_argument('--interval', type=int, default=300)
    parser.add_argument('--initial-wait', type=int, default=15,
                        help='initial wait after batch creation before first poll (seconds)')
    args = parser.parse_args()

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print('ERROR: OPENAI_API_KEY not set', file=sys.stderr)
        return 1

    if not INPUT_JSONL.exists():
        print(f'ERROR: {INPUT_JSONL} not found', file=sys.stderr)
        return 1

    log(f'=== Sequential batch start: {args.chunks} chunks, interval={args.interval}s ===')
    chunks = split_jsonl(INPUT_JSONL, args.chunks, OUT_DIR)
    log(f'Split into {len(chunks)} files: ' + ', '.join(f'{c["path"].name}({c["n_requests"]})' for c in chunks))

    results = []
    state = {'chunks': []}
    merged_output_path = OUT_DIR / 'batch_output_merged.jsonl'
    # reset merged file
    open(merged_output_path, 'w').close()

    for chunk in chunks:
        result = run_chunk(chunk, api_key, args.interval)
        entry = {
            'chunk': chunk['index'],
            'batch_id': result['id'],
            'status': result['status'],
            'output_file_id': result.get('output_file_id'),
            'error_file_id': result.get('error_file_id'),
            'request_counts': result.get('request_counts'),
        }
        results.append(result)
        state['chunks'].append(entry)
        save_state(state)

        if result['status'] != 'completed':
            log(f'[chunk {chunk["index"]}] NOT COMPLETED (status={result["status"]}), stopping sequence')
            errors = result.get('errors')
            if errors:
                log(f'[chunk {chunk["index"]}] errors: {json.dumps(errors, ensure_ascii=False)[:500]}')
            state['final_status'] = 'stopped_on_failure'
            save_state(state)
            return 2

        # Download output and append to merged file
        output_content = download_file(result['output_file_id'], api_key)
        with open(merged_output_path, 'a', encoding='utf-8') as f:
            f.write(output_content)
            if not output_content.endswith('\n'):
                f.write('\n')
        log(f'[chunk {chunk["index"]}] output appended to {merged_output_path.name}')

    state['final_status'] = 'all_completed'
    state['merged_output'] = str(merged_output_path)
    save_state(state)
    log(f'=== ALL {len(chunks)} CHUNKS COMPLETED ===')
    log(f'Merged output: {merged_output_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
