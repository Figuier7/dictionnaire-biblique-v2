#!/usr/bin/env python3
"""
Re-traduit TOUTES les BDB avec definition_full_fr tronque\u0301e de fac\u0327on subtile.

Crite\u0300res combine\u0301s :
  1. Ratio FR/EN < 0.75 sur texte long (EN > 200 chars)  [~16 cas — de\u0301ja\u0300 corrige\u0301s]
  2. Fin abrupte de la traduction FR (virgule, conjonction seule, mot coupe\u0301) [~1639 cas]

Source : hebrew-lexicon-fr.json (non-compact) — traduit definition_full_fr
Target : re-compile hebrew-lexicon-fr-compact.json (champ `df`)

Usage:
    python scripts/fix_bdb_abrupt_truncations.py --list           # lister les cas a\u0300 traiter
    python scripts/fix_bdb_abrupt_truncations.py --apply          # re-traduire et ecrire
    python scripts/fix_bdb_abrupt_truncations.py --apply --workers 10 --limit 50   # tests
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
NC_PATH = BASE / 'hebrew-lexicon-fr.json'
COMPACT_PATH = BASE / 'uploads' / 'dictionnaires' / 'hebrew' / 'hebrew-lexicon-fr-compact.json'
LOG_DIR = BASE / 'work' / 'audit'
LOG_PATH = LOG_DIR / 'bdb-abrupt-retrans.log'


def log(msg):
    stamp = datetime.now().strftime('%H:%M:%S')
    line = f'[{stamp}] {msg}'
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {msg}\n')


def ends_abruptly(text):
    """True si le texte se termine abruptement (virgule, conjonction seule, mot incomplet)."""
    if not text:
        return False
    t = text.rstrip()
    if not t:
        return False
    last = t[-1]
    # Ponctuation finale normale
    if last in '.!?)"\u00bb\u201d\u2019\u2026\u2014':
        return False
    # Finit par virgule / point-virgule / deux-points / tiret
    if last in ',;:\u2014-':
        return True
    # Finit par conjonction ou preposition isolee
    last_word = t.split()[-1].lower().strip('.,;:')
    if last_word in {'et', 'ou', 'de', 'du', 'des', 'le', 'la', 'les', 'avec',
                     'dans', 'sur', 'pour', 'par', 'mais', 'comme', 'si', 'que',
                     'a\u0300', 'au', 'aux', 'en', 'se', 'ce', 'il', 'elle',
                     'e\u0302tre', 'faire', 'avoir'}:
        return True
    # Si l'EN finit par point et le FR pas → suspect
    if '.' in t and last not in '.!?':
        return True
    return False


def needs_retranslation(entry):
    """Determine si l'entry a besoin d'une re-traduction."""
    en_full = entry.get('definition_full', '') or ''
    fr_full = entry.get('definition_full_fr', '') or ''
    if len(en_full) < 100:
        return False, ''  # trop court pour evaluer
    if not fr_full:
        return True, 'fr_empty'
    ratio = len(fr_full) / len(en_full)
    if len(en_full) > 200 and ratio < 0.45:
        return True, f'ratio_high_trunc ({ratio:.2f})'
    if len(en_full) > 300 and ratio < 0.65:
        return True, f'ratio_med_trunc ({ratio:.2f})'
    if ends_abruptly(fr_full):
        return True, 'abrupt_ending'
    return False, ''


def translate_one(entry, api_key, max_retries=3):
    en = entry['definition_full']
    prompt = f"""Tu traduis une entre\u0301e de lexique biblique BDB (Brown-Driver-Briggs) de l'anglais vers le franc\u0327ais.
Conserve le sens technique/scholarly. Ne tronque pas. Garde toutes les nuances par stem (Qal, Niphal, Piel, Hiphil, etc.).
Traduis fide\u0300lement, sans re\u0301sumer. La traduction doit se terminer proprement par un point ou ponctuation finale.

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
            return {'strong': entry['strong'], 'old_len': len(entry.get('definition_full_fr', '') or ''),
                    'new': translated, 'new_len': len(translated), 'error': None}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')
            if e.code == 429 or e.code >= 500:
                time.sleep(2 ** attempt)
                continue
            return {'strong': entry['strong'], 'new': None, 'error': f'{e.code}: {err_body[:200]}'}
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {'strong': entry['strong'], 'new': None, 'error': str(e)[:200]}
    return {'strong': entry['strong'], 'new': None, 'error': 'max_retries'}


def list_targets():
    with io.open(NC_PATH, 'r', encoding='utf-8-sig') as f:
        nc = json.load(f)
    targets = []
    reasons_count = {}
    for e in nc:
        need, reason = needs_retranslation(e)
        if need:
            targets.append(e)
            reasons_count[reason.split(' ')[0]] = reasons_count.get(reason.split(' ')[0], 0) + 1
    return nc, targets, reasons_count


def apply_fixes(workers=10, limit=None):
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        log('ERROR: OPENAI_API_KEY not set')
        return 1

    log('Loading non-compact lexicon...')
    nc, targets, reasons = list_targets()
    log(f'Targets to re-translate: {len(targets)}')
    log(f'Reasons: {reasons}')

    if limit:
        targets = targets[:limit]
        log(f'Limited to {limit} for test')

    idx_nc = {e['strong']: e for e in nc}
    completed = 0
    failed = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=workers) as exe:
        futs = {exe.submit(translate_one, e, api_key): e for e in targets}
        for fut in as_completed(futs):
            r = fut.result()
            if r['error']:
                failed += 1
                log(f'  FAIL {r["strong"]}: {r["error"][:100]}')
            else:
                completed += 1
                target = idx_nc.get(r['strong'])
                if target:
                    target['definition_full_fr'] = r['new']
                if (completed + failed) % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = (completed + failed) / elapsed if elapsed else 0
                    eta = (len(targets) - completed - failed) / rate if rate else 0
                    log(f'Progress {completed+failed}/{len(targets)} ok={completed} fail={failed} rate={rate:.1f}/s ETA={eta:.0f}s')

    # Sauvegarde non-compact
    log(f'Saving non-compact ({len(nc)} entries)...')
    with open(NC_PATH, 'wb') as f:
        f.write(json.dumps(nc, ensure_ascii=False, indent=2).encode('utf-8'))
    log(f'  {NC_PATH} saved ({os.path.getsize(NC_PATH):,} bytes)')

    # Rebuild compact : synchroniser le champ `df`
    log('Updating compact lexicon (df field)...')
    with open(COMPACT_PATH, 'rb') as f:
        raw = f.read()
    has_bom = raw.startswith(b'\xef\xbb\xbf')
    if has_bom:
        raw = raw[3:]
    compact = json.loads(raw.decode('utf-8'))
    idx_c = {e.get('s'): e for e in compact}
    count_updated = 0
    for e in compact:
        s = e.get('s')
        target_nc = idx_nc.get(s)
        if target_nc:
            new_df = target_nc.get('definition_full_fr', '')
            if new_df and e.get('df') != new_df:
                e['df'] = new_df
                count_updated += 1

    payload = json.dumps(compact, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if has_bom:
        payload = b'\xef\xbb\xbf' + payload
    with open(COMPACT_PATH, 'wb') as f:
        f.write(payload)
    log(f'Compact updated: {count_updated} entries, size {os.path.getsize(COMPACT_PATH):,} bytes')
    log(f'=== DONE: {completed} re-translated, {failed} failed, compact size updated ===')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true', help='List targets without applying')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--workers', type=int, default=10)
    ap.add_argument('--limit', type=int, default=None, help='Limit number of entries (for test)')
    args = ap.parse_args()

    if args.list:
        nc, targets, reasons = list_targets()
        log(f'Total entries to re-translate: {len(targets)}')
        log(f'Breakdown by reason: {reasons}')
    elif args.apply:
        return apply_fixes(workers=args.workers, limit=args.limit)
    else:
        nc, targets, reasons = list_targets()
        log(f'(dry-run) Total entries to re-translate: {len(targets)}')
        log(f'Breakdown: {reasons}')
        log('Use --apply to proceed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
