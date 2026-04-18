#!/usr/bin/env python3
"""
Normalisation des abréviations bibliques vers le standard Ostervald.

Lit la table de mapping depuis work/audit/ostervald-abbrev-mapping.json
et applique les remplacements dans toutes les définitions ISBE.

Pattern strict : \bFORME(?:\.)\s+\d — word boundary + optionnel point + chiffre
pour éviter les faux positifs (Am, Lu, Le, La, etc.)

Modes : dry-run (default) ou --apply
"""
import json
import sys
import re
import argparse
import glob
from pathlib import Path
from datetime import datetime
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
ISBE_DIR = ROOT / "uploads" / "dictionnaires" / "isbe"
AUDIT_DIR = ROOT / "work" / "audit"
MAP_JSON = AUDIT_DIR / "ostervald-abbrev-mapping.json"
LOG_JSON = AUDIT_DIR / "ostervald-normalization-log.json"


def build_replacement_rules(mapping):
    """Build regex-based replacement rules from the mapping JSON.
    Returns list of (compiled_regex, replacement_string, source_form)."""
    rules = []

    # 1. Main replacements (wrong form → Ostervald)
    for wrong, correct in mapping.get('replacements', {}).items():
        # Pattern: \bFORME\.?\s+(?=\d) — word boundary, optional dot, space, followed by digit
        # Use lookahead for digit so we don't consume it
        escaped = re.escape(wrong.rstrip('.'))
        pattern = r'\b' + escaped + r'\.?\s+(?=\d)'
        replacement = correct + ' '
        rules.append((re.compile(pattern), replacement, wrong, correct))

    # 2. Missing dots (correct form but needs dot)
    for nodot, withdot in mapping.get('points_manquants', {}).items():
        if nodot.startswith('_'):
            continue
        escaped = re.escape(nodot)
        # Match form WITHOUT dot followed by space+digit, replace with dotted form
        pattern = r'\b' + escaped + r'\s+(?=\d)'
        replacement = withdot + ' '
        rules.append((re.compile(pattern), replacement, nodot, withdot))

    # Sort by length of source form (longest first to avoid partial matches)
    rules.sort(key=lambda r: -len(r[2]))

    return rules


def apply_rules(text, rules):
    """Apply all replacement rules to a text. Returns (new_text, changes_list)."""
    changes = []
    result = text

    for regex, replacement, src, tgt in rules:
        # Find all matches first (for logging)
        matches = list(regex.finditer(result))
        if matches:
            new_result = regex.sub(replacement, result)
            if new_result != result:
                changes.append({
                    'from': src,
                    'to': tgt,
                    'count': len(matches),
                })
                result = new_result

    return result, changes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'Mode: {mode}')

    with open(MAP_JSON, encoding='utf-8') as f:
        mapping = json.load(f)

    rules = build_replacement_rules(mapping)
    print(f'Replacement rules: {len(rules)}')

    total_entries_changed = 0
    total_replacements = 0
    chunks_modified = 0
    change_stats = Counter()
    samples = []

    for fp in sorted(ISBE_DIR.glob('isbe-?.json')):
        with open(fp, encoding='utf-8-sig') as f:
            entries = json.load(f)
        local_changes = 0

        for e in entries:
            defn = e.get('definition', '')
            if not defn:
                continue

            new_defn, changes = apply_rules(defn, rules)

            if changes:
                total_entries_changed += 1
                local_changes += 1
                for ch in changes:
                    change_stats[f"{ch['from']} → {ch['to']}"] += ch['count']
                    total_replacements += ch['count']
                    if len(samples) < 20:
                        # Get a context sample
                        samples.append({
                            'entry_id': e['id'],
                            'mot': e.get('mot', '')[:25],
                            'from': ch['from'],
                            'to': ch['to'],
                        })

                if args.apply:
                    e['definition'] = new_defn
                    e['definition_length'] = len(new_defn)

        if local_changes > 0:
            chunks_modified += 1
            if args.apply:
                payload = json.dumps(entries, ensure_ascii=False, separators=(', ', ': '))
                with open(fp, 'w', encoding='utf-8-sig') as f:
                    f.write(payload)

    print(f'\nEntries changed: {total_entries_changed}')
    print(f'Total replacements: {total_replacements}')
    print(f'Chunks modified: {chunks_modified}')
    print()
    print('=== Top 30 replacements ===')
    for rule, count in change_stats.most_common(30):
        print(f'  {rule:30s} {count:>5}x')
    print()
    print('=== Samples ===')
    for s in samples[:15]:
        print(f"  {s['entry_id']} {s['mot']:25s} {s['from']} → {s['to']}")

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_JSON, 'w', encoding='utf-8') as f:
        json.dump({
            'mode': mode,
            'timestamp': datetime.now().isoformat(),
            'rules_count': len(rules),
            'entries_changed': total_entries_changed,
            'total_replacements': total_replacements,
            'chunks_modified': chunks_modified,
            'top_changes': dict(change_stats.most_common(50)),
            'samples': samples,
        }, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
