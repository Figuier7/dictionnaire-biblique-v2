#!/usr/bin/env python3
"""
Audit global des troncatures BDB dans hebrew-lexicon-fr.json (non-compact).

Plusieurs crite\u0300res de de\u0301tection :
  1. Ratio FR/EN anormalement bas sur champs longs
  2. Troncature silencieuse (phrase finit par ',', ';', ':', mot incomplet)
  3. Champs secondaires tronque\u0301s : usage_fr, bdb_defs_fr, bdb_senses.text
  4. definition_short_fr vs EN (textes plus courts)
  5. Pre\u0301sence d'ellipses "..." ou "etc." en fin de texte traduit

Usage:
    python scripts/audit_bdb_truncations_full.py
    python scripts/audit_bdb_truncations_full.py --csv work/audit/bdb-truncations.csv
"""
import argparse
import csv
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
NC_PATH = BASE / 'hebrew-lexicon-fr.json'


def ends_abruptly(text):
    """True si le texte se termine de fac\u0327on suspecte (virgule, deux-points, conjonction sans fin)."""
    if not text:
        return False
    t = text.rstrip()
    if not t:
        return False
    last = t[-1]
    # Ponctuation finale normale
    if last in '.!?)"\u00bb\u201d\u2019\u2026\u2014':
        return False
    # Finit par virgule / point-virgule / deux-points / tiret seul
    if last in ',;:\u2014-':
        return True
    # Finit par une conjonction/pre\u0301position isole\u0301e
    last_word = t.split()[-1].lower().strip('.,;:')
    if last_word in {'et', 'ou', 'de', 'du', 'des', 'le', 'la', 'les', 'avec',
                     'dans', 'sur', 'pour', 'par', 'mais', 'comme', 'si', 'que'}:
        return True
    # Finit sans point alors qu'il y a des points dans le texte (cohe\u0301rence ponctuation)
    if '.' in t and last not in '.!?':
        return True
    return False


def ratio(fr, en):
    if not en:
        return None
    if not fr:
        return 0.0
    return len(fr) / len(en)


def analyze(nc):
    """Produit une liste de findings pour chaque entre\u0301e suspecte."""
    findings = []
    stats = Counter()

    for e in nc:
        s = e.get('strong', '?')
        h = e.get('hebrew', '')
        hits = []  # liste de (severity, field, detail)

        # === 1. definition_full_fr vs definition_full (EN) ===
        en_full = e.get('definition_full', '') or ''
        fr_full = e.get('definition_full_fr', '') or ''
        r = ratio(fr_full, en_full)
        if r is not None and len(en_full) >= 200:
            if r < 0.45:
                hits.append(('HIGH', 'def_full', f'EN={len(en_full)} FR={len(fr_full)} ratio={r:.2f}'))
                stats['def_full_high'] += 1
            elif r < 0.65:
                hits.append(('MED', 'def_full', f'EN={len(en_full)} FR={len(fr_full)} ratio={r:.2f}'))
                stats['def_full_med'] += 1

        # === 2. Fin abrupte definition_full_fr ===
        if fr_full and len(fr_full) >= 100 and ends_abruptly(fr_full):
            hits.append(('MED', 'def_full_abrupt', f'fin: \"...{fr_full[-40:]}\"'))
            stats['def_full_abrupt'] += 1

        # === 3. usage_fr vs usage ===
        en_usage = e.get('usage', '') or ''
        fr_usage = e.get('usage_fr', '') or ''
        r2 = ratio(fr_usage, en_usage)
        if r2 is not None and len(en_usage) >= 300:
            if r2 < 0.55:
                hits.append(('MED', 'usage', f'EN={len(en_usage)} FR={len(fr_usage)} ratio={r2:.2f}'))
                stats['usage_low'] += 1

        # === 4. bdb_senses.text FR vs EN (dans les stems) ===
        for sense in e.get('bdb_senses', []) or []:
            st = sense.get('stem', '?')
            en_txt = sense.get('text', '') or ''
            fr_txt = sense.get('text_fr', '') or ''
            if len(en_txt) >= 150:
                r3 = ratio(fr_txt, en_txt)
                if r3 is None or r3 < 0.4:
                    hits.append(('LOW', f'sense_{st}', f'EN={len(en_txt)} FR={len(fr_txt) if fr_txt else 0}'))
                    stats['sense_txt_low'] += 1

        # === 5. definition_short_fr sans EN \u00e9quivalent ===
        en_short = e.get('definition_short', '') or ''
        fr_short = e.get('definition_short_fr', '') or ''
        r4 = ratio(fr_short, en_short)
        if r4 is not None and len(en_short) >= 80:
            if r4 < 0.55:
                hits.append(('LOW', 'def_short', f'EN={len(en_short)} FR={len(fr_short)} ratio={r4:.2f}'))
                stats['def_short_low'] += 1

        # === 6. Ellipses / "etc." abusifs en fin de FR mais pas EN ===
        if fr_full and ('\u2026' in fr_full[-10:] or fr_full.rstrip().endswith('etc.')):
            if not ('\u2026' in en_full[-10:] or en_full.rstrip().endswith('etc.')):
                hits.append(('LOW', 'def_full_ellipsis', f'ellipse FR non pre\u0301sente en EN'))
                stats['ellipsis_asymmetric'] += 1

        if hits:
            findings.append({
                'strong': s,
                'hebrew': h,
                'en_full_len': len(en_full),
                'fr_full_len': len(fr_full),
                'hits': hits,
            })

    return findings, stats


def format_console(findings, stats, max_rows=200):
    print('=== BDB Troncation audit — full ===')
    print()
    print(f'Total entries with at least one finding: {len(findings)}')
    print()
    print('=== Counters ===')
    for k, v in sorted(stats.items(), key=lambda x: -x[1]):
        print(f'  {k:<25}: {v}')
    print()

    # Severity order
    sev_rank = {'HIGH': 0, 'MED': 1, 'LOW': 2}
    findings_sorted = sorted(findings, key=lambda f: (
        min(sev_rank[h[0]] for h in f['hits']),
        -max(int(re.search(r'EN=(\d+)', h[2]).group(1)) if 'EN=' in h[2] else 0 for h in f['hits'])
    ))

    print(f'=== Top {min(max_rows, len(findings_sorted))} findings ===')
    print(f'{"Strong":<7} {"Heb":<10} {"Severity":<10} {"Field":<20} {"Detail"}')
    for f in findings_sorted[:max_rows]:
        for sev, field, detail in f['hits']:
            print(f'{f["strong"]:<7} {f["hebrew"]:<10} {sev:<10} {field:<20} {detail}')


def export_csv(findings, csv_path):
    os.makedirs(os.path.dirname(csv_path) or '.', exist_ok=True)
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['strong', 'hebrew', 'severity', 'field', 'detail', 'en_full_len', 'fr_full_len'])
        for finding in findings:
            for sev, field, detail in finding['hits']:
                w.writerow([finding['strong'], finding['hebrew'], sev, field, detail,
                           finding['en_full_len'], finding['fr_full_len']])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', help='Export findings to CSV file')
    ap.add_argument('--max-rows', type=int, default=200, help='Max rows to display in console')
    args = ap.parse_args()

    print(f'Loading {NC_PATH}...')
    with io.open(NC_PATH, 'r', encoding='utf-8-sig') as f:
        nc = json.load(f)
    print(f'  {len(nc)} entries')
    print()

    findings, stats = analyze(nc)
    format_console(findings, stats, max_rows=args.max_rows)

    if args.csv:
        export_csv(findings, args.csv)
        print(f'\nCSV exported: {args.csv}')


if __name__ == '__main__':
    main()
