#!/usr/bin/env python3
"""
Strip English phonetic transliterations from ISBE definitions.

Pattern: entries starting with pronunciation like "dark'-li :", "ab'-a-kuk (",
"sak'-ri-fis, sak'-ri-fiz :" — these are English pronunciation guides useless
in the French translation.

Strategy:
- Match the phonetic prefix (lowercase with apostrophes/hyphens)
- Remove it, keeping the rest of the definition starting from ( : ; or the
  actual content
- Clean up leading ": " or "; " if the definition starts with that after removal
- Do NOT remove content that looks like Hebrew/Greek transliteration (has
  special chars or is inside parentheses)

Modes: dry-run (default) or --apply
"""
import json
import sys
import re
import argparse
import glob
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
ISBE_DIR = ROOT / "uploads" / "dictionnaires" / "isbe"
AUDIT_DIR = ROOT / "work" / "audit"
BACKUP_DIR = ROOT / "work" / "backups"
LOG_JSON = AUDIT_DIR / "isbe-strip-phonetics-log.json"

# Pattern: starts with phonetic block, then delimiter
# Phonetic block = lowercase letters with ' and - inside, optionally comma-separated variants
PHONETIC_RE = re.compile(
    r"^([a-z][a-z'\u2019\-]+(?:\s*,\s*[a-z'\u2019\-]+)*)\s*"
    r"([:;(\[])"
)


def strip_phonetic(definition):
    """Remove leading English phonetic transliteration from a definition.
    Returns (cleaned_def, removed_part) or (None, None) if no match."""
    defn = definition.strip()
    if not defn:
        return None, None

    m = PHONETIC_RE.match(defn)
    if not m:
        return None, None

    phonetic_part = m.group(1).strip()

    # Verify it's actually phonetic (must have ' or - inside, not just a plain word)
    if "'" not in phonetic_part and '\u2019' not in phonetic_part and '-' not in phonetic_part:
        return None, None

    # Get the rest after the phonetic block
    rest = defn[m.start(2):]

    # Clean up leading ": " or "; " if the delimiter was : or ;
    rest = re.sub(r'^[:;]\s*', '', rest).strip()

    # If rest starts with ( it's fine — that's the etymology
    # If rest is empty or too short, skip (safety)
    if len(rest) < 10:
        return None, None

    return rest, phonetic_part


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'Mode: {mode}')

    if args.apply and not (BACKUP_DIR.exists() and list(BACKUP_DIR.glob('dictionnaires-*.zip'))):
        print("ERREUR: backup manquant")
        sys.exit(1)

    total_entries = 0
    total_stripped = 0
    chunks_modified = {}
    log_entries = []

    for fp in sorted(ISBE_DIR.glob('isbe-?.json')):
        with open(fp, encoding='utf-8-sig') as f:
            entries = json.load(f)

        chunk_name = fp.name
        local_stripped = 0

        for e in entries:
            total_entries += 1
            defn = e.get('definition', '')
            cleaned, removed = strip_phonetic(defn)
            if cleaned is not None:
                total_stripped += 1
                local_stripped += 1
                if len(log_entries) < 30:
                    log_entries.append({
                        'entry_id': e['id'],
                        'mot': e.get('mot', ''),
                        'removed': removed,
                        'def_before_50': defn[:50],
                        'def_after_50': cleaned[:50],
                    })
                if args.apply:
                    e['definition'] = cleaned
                    e['definition_length'] = len(cleaned)

        if local_stripped > 0:
            chunks_modified[chunk_name] = local_stripped
            if args.apply:
                payload = json.dumps(entries, ensure_ascii=False, separators=(', ', ': '))
                with open(fp, 'w', encoding='utf-8-sig') as f:
                    f.write(payload)

    print(f'\nTotal entries scanned : {total_entries}')
    print(f'Phonetics stripped    : {total_stripped}')
    print(f'Chunks modified       : {len(chunks_modified)}')
    print()

    if chunks_modified:
        print('Per chunk:')
        for ch, cnt in sorted(chunks_modified.items()):
            print(f'  {ch}: {cnt}')

    print('\nSamples:')
    for le in log_entries[:15]:
        print(f"  {le['entry_id']} {le['mot'][:25]:25s} REMOVED: \"{le['removed'][:30]}\"")

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_JSON, 'w', encoding='utf-8') as f:
        json.dump({
            'mode': mode,
            'timestamp': datetime.now().isoformat(),
            'total_entries': total_entries,
            'stripped': total_stripped,
            'chunks_modified': chunks_modified,
            'samples': log_entries,
        }, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
