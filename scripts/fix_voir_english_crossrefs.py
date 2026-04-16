#!/usr/bin/env python3
"""
Phase 4B : Remplace les renvois "Voir ENGLISH_TARGET" par "Voir FRENCH_LABEL"
dans les définitions ISBE.

Utilise le mapping de voir-crossref-map.json produit par Phase 4A.

Modes : dry-run (default) ou --apply
"""
import json
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
ISBE_DIR = ROOT / "uploads" / "dictionnaires" / "isbe"
AUDIT_DIR = ROOT / "work" / "audit"
MAP_JSON = AUDIT_DIR / "voir-crossref-map.json"
LOG_JSON = AUDIT_DIR / "voir-crossrefs-fix-log.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'Mode: {mode}')

    with open(MAP_JSON, encoding='utf-8') as f:
        mapping = json.load(f)
    resolved = mapping['resolved']
    print(f'Resolved mappings: {len(resolved)}')

    # Build replacement dict: UPPERCASE_TARGET → label_fr
    replacements = {}
    for key, info in resolved.items():
        original = info['original']
        label_fr = info['label_fr']
        # Only replace if the French label is actually different
        if original.upper() != label_fr.upper():
            replacements[original] = label_fr

    print(f'Replacements where EN != FR: {len(replacements)}')

    # Pattern to find "Voir TARGET" in definitions
    # TARGET = uppercase sequence after "Voir "
    voir_re = re.compile(
        r'(Voir\s+)([A-ZÀ-Ý][A-ZÀ-Ý\s\-\',]+?)(\s*[.;,:\)\]]|$)'
    )

    total_replacements = 0
    chunks_modified = 0
    log_samples = []

    for fp in sorted(ISBE_DIR.glob('isbe-?.json')):
        with open(fp, encoding='utf-8-sig') as f:
            entries = json.load(f)
        local_changes = 0

        for e in entries:
            defn = e.get('definition', '')
            if 'Voir ' not in defn:
                continue

            new_defn = defn
            for match in voir_re.finditer(defn):
                prefix = match.group(1)  # "Voir "
                target = match.group(2).strip()
                suffix = match.group(3)

                if target in replacements:
                    fr_label = replacements[target]
                    old_text = prefix + target + suffix
                    new_text = prefix + fr_label.upper() + suffix
                    new_defn = new_defn.replace(old_text, new_text, 1)

                    if len(log_samples) < 20:
                        log_samples.append({
                            'entry_id': e['id'],
                            'mot': e.get('mot', ''),
                            'old': target,
                            'new': fr_label.upper(),
                        })

            if new_defn != defn:
                local_changes += 1
                total_replacements += 1
                if args.apply:
                    e['definition'] = new_defn
                    e['definition_length'] = len(new_defn)

        if local_changes > 0:
            chunks_modified += 1
            if args.apply:
                payload = json.dumps(entries, ensure_ascii=False, separators=(', ', ': '))
                with open(fp, 'w', encoding='utf-8-sig') as f:
                    f.write(payload)

    print(f'\nEntries modified: {total_replacements}')
    print(f'Chunks modified: {chunks_modified}')
    print()
    print('=== Samples ===')
    for s in log_samples[:15]:
        print(f'  {s["entry_id"]} {s["mot"][:25]:25s} Voir {s["old"]} → Voir {s["new"]}')

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_JSON, 'w', encoding='utf-8') as f:
        json.dump({
            'mode': mode,
            'timestamp': datetime.now().isoformat(),
            'total_replacements': total_replacements,
            'chunks_modified': chunks_modified,
            'samples': log_samples,
        }, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
