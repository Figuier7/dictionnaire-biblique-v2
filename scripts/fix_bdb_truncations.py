#!/usr/bin/env python3
"""
Re-traduit les BDB definition_full_fr qui ont e\u0301te\u0301 tronque\u0301es.
Crite\u0300re : EN > 500 chars ET ratio FR/EN < 0.75

Source : hebrew-lexicon-fr.json (non-compact)
Target : meme fichier + re-compile hebrew-lexicon-fr-compact.json (champ df)

Usage:
    python scripts/fix_bdb_truncations.py --list              # lister les cas
    python scripts/fix_bdb_truncations.py --apply             # re-traduit et ecrit
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
NC_PATH = BASE / 'hebrew-lexicon-fr.json'
COMPACT_PATH = BASE / 'uploads' / 'dictionnaires' / 'hebrew' / 'hebrew-lexicon-fr-compact.json'


def identify_truncations(nc):
    truncated = []
    for e in nc:
        en = e.get('definition_full', '') or ''
        fr = e.get('definition_full_fr', '') or ''
        if len(en) > 500 and len(fr) > 0:
            ratio = len(fr) / len(en)
            if ratio < 0.75:
                truncated.append(e)
    return truncated


def translate_one(entry, api_key, max_retries=3):
    en = entry['definition_full']
    prompt = f"""Tu traduis une entre\u0301e de lexique biblique BDB (Brown-Driver-Briggs) de l'anglais vers le franc\u0327ais.
Conserve le sens technique/scholarly. Ne tronque pas. Garde toutes les nuances par stem (Qal, Niphal, Piel, Hiphil, etc.).
Traduis fide\u0300lement, sans re\u0301sumer.

Texte a\u0300 traduire :
---
{en}
---

Re\u0301ponds uniquement avec la traduction franc\u0327aise, sans pre\u0301ambule."""

    body = {
        'model': 'gpt-4o-mini',
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.1,
    }
    data = json.dumps(body).encode('utf-8')

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                'https://api.openai.com/v1/chat/completions',
                data=data, method='POST',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                response = json.loads(resp.read())
            translated = response['choices'][0]['message']['content'].strip()
            return {'strong': entry['strong'], 'old': entry['definition_full_fr'], 'new': translated, 'error': None}
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {'strong': entry['strong'], 'old': entry.get('definition_full_fr',''), 'new': None, 'error': str(e)}


def list_only():
    with io.open(NC_PATH, 'r', encoding='utf-8-sig') as f:
        nc = json.load(f)
    truncated = identify_truncations(nc)
    print(f'Total troncatures : {len(truncated)}')
    print()
    print(f'{"Strong":<8} {"Hebrew":<12} {"EN len":<8} {"FR len":<8} {"ratio":<6}')
    for e in sorted(truncated, key=lambda x: -len(x.get('definition_full', ''))):
        print(f'{e["strong"]:<8} {e.get("hebrew",""):<12} {len(e["definition_full"]):<8} {len(e["definition_full_fr"]):<8} {len(e["definition_full_fr"])/len(e["definition_full"]):.2f}')


def apply_fixes():
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print('ERROR: OPENAI_API_KEY not set', file=sys.stderr); return 1

    # Load non-compact
    with io.open(NC_PATH, 'r', encoding='utf-8-sig') as f:
        nc = json.load(f)

    truncated = identify_truncations(nc)
    print(f'Traductions a\u0300 refaire : {len(truncated)}')

    # Translate in parallel
    results = []
    with ThreadPoolExecutor(max_workers=5) as exe:
        futs = {exe.submit(translate_one, e, api_key): e for e in truncated}
        for fut in as_completed(futs):
            r = fut.result()
            if r['error']:
                print(f'  FAIL {r["strong"]}: {r["error"][:100]}')
            else:
                print(f'  OK {r["strong"]}: {len(r["old"])} -> {len(r["new"])} chars')
            results.append(r)

    # Apply to non-compact
    idx_nc = {e['strong']: e for e in nc}
    for r in results:
        if r['new']:
            e = idx_nc.get(r['strong'])
            if e:
                e['definition_full_fr'] = r['new']

    # Write back non-compact
    with open(NC_PATH, 'wb') as f:
        raw = json.dumps(nc, ensure_ascii=False, indent=2).encode('utf-8')
        f.write(raw)
    print(f'\nNon-compact sauv\u00e9 ({os.path.getsize(NC_PATH):,} bytes)')

    # Re-compile compact : update `df` field for truncated entries
    with io.open(COMPACT_PATH, 'rb') as f:
        raw = f.read()
    has_bom = raw.startswith(b'\xef\xbb\xbf')
    if has_bom:
        raw = raw[3:]
    compact = json.loads(raw.decode('utf-8'))
    idx_c = {e.get('s'): e for e in compact}
    count_updated = 0
    for r in results:
        if r['new']:
            e = idx_c.get(r['strong'])
            if e:
                old = e.get('df', '')
                e['df'] = r['new']
                count_updated += 1

    # Write compact back (preserve BOM + format)
    with open(COMPACT_PATH, 'rb') as f:
        orig = f.read()
    sample = orig[:500].decode('utf-8', errors='replace')
    # Compact uses (',', ':') no space separator
    payload = json.dumps(compact, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if has_bom:
        payload = b'\xef\xbb\xbf' + payload
    with open(COMPACT_PATH, 'wb') as f:
        f.write(payload)
    print(f'Compact sauve\u0301 ({os.path.getsize(COMPACT_PATH):,} bytes, {count_updated} entre\u0301es mises a\u0300 jour)')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    if args.list:
        list_only()
    elif args.apply:
        return apply_fixes()
    else:
        list_only()
        print('\n(dry-run: use --apply to translate and write)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
