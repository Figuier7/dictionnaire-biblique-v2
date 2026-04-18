#!/usr/bin/env python3
"""Transpose ISBE C4 redirections: translate See->Voir, mark empties as stub."""
import json, re, sys, os, glob

sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISBE_DIR = os.path.join(BASE, 'work', 'codex_local_isbe')
CIRCLES_PATH = os.path.join(ISBE_DIR, 'isbe-priority-circles.json')
OUT_DIR = os.path.join(ISBE_DIR, 'translated_chunks')

os.makedirs(OUT_DIR, exist_ok=True)

# Load circles
with open(CIRCLES_PATH, 'r', encoding='utf-8-sig') as f:
    circles = json.load(f)
c4_mots = set(c['mot'] for c in circles if c['circle'] == 'C4')

# Load all source entries
source_files = sorted(glob.glob(os.path.join(ISBE_DIR, 'source_chunks', 'chunk_*.source.json')))
all_entries = []
entry_to_chunk = {}
for sf in source_files:
    chunk_id = os.path.basename(sf).replace('.source.json', '')
    with open(sf, 'r', encoding='utf-8-sig') as f:
        chunk = json.load(f)
    for e in chunk:
        all_entries.append(e)
        entry_to_chunk[e['mot'].strip()] = chunk_id

# Build translated C4 entries
translated_c4 = []
stats = {'see_translated': 0, 'see_also': 0, 'same_as': 0, 'empty_stub': 0, 'other': 0}

for entry in all_entries:
    mot = entry['mot'].strip()
    if mot not in c4_mots:
        continue

    defn = entry['definition'].strip()
    translated_defn = ''
    status = 'ready'

    if not defn:
        # Empty entry -> stub
        translated_defn = ''
        status = 'stub'
        stats['empty_stub'] += 1
    else:
        # Translate redirect patterns
        d = defn

        # "See X" -> "Voir X"
        d = re.sub(r'^See\b', 'Voir', d)
        d = re.sub(r'\bSee\b', 'Voir', d)

        # "See also X" -> "Voir aussi X"
        d = d.replace('Voir also', 'Voir aussi')

        # "see X" (lowercase) -> "voir X"
        d = re.sub(r'\bsee\b', 'voir', d)

        # "Same as X" -> "Identique à X"
        d = re.sub(r'^Same as\b', 'Identique à', d)

        # "see under X" -> "voir sous X"
        d = d.replace('voir under', 'voir sous')

        # "compare X" -> "comparer X"
        d = re.sub(r'\bcompare\b', 'comparer', d)

        # Clean up any double spaces
        d = re.sub(r'  +', ' ', d).strip()

        translated_defn = d

        if 'Voir aussi' in d:
            stats['see_also'] += 1
        elif 'Identique' in d:
            stats['same_as'] += 1
        elif 'Voir' in d or 'voir' in d:
            stats['see_translated'] += 1
        else:
            stats['other'] += 1

    translated_c4.append({
        'mot': mot,
        'definition': translated_defn,
        'status': status,
        'circle': 'C4',
        'original': defn,
    })

# Save as a single translated file for C4
c4_out_path = os.path.join(OUT_DIR, 'c4_redirections.fr.json')
with open(c4_out_path, 'w', encoding='utf-8') as f:
    json.dump(translated_c4, f, ensure_ascii=False, indent=2)

print("=== C4 TRANSPOSITION RESULTS ===")
for k, v in stats.items():
    print(f"  {k}: {v}")
print(f"  TOTAL: {len(translated_c4)}")
print(f"\nSaved to: {c4_out_path}")

# Show samples
print("\n=== SAMPLES ===")
for entry in translated_c4[:15]:
    if entry['status'] == 'stub':
        print(f"  {entry['mot']}: [STUB - empty]")
    else:
        print(f"  {entry['mot']}: {entry['definition'][:80]}")

# Show stubs
print(f"\n=== STUBS ({stats['empty_stub']}) ===")
for entry in translated_c4:
    if entry['status'] == 'stub':
        print(f"  {entry['mot']}")
