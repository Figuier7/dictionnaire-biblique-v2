#!/usr/bin/env python3
"""Identify which chunks contain C1 entries for V1 translation priority."""
import json, re, sys, os, glob
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISBE_DIR = os.path.join(BASE, 'work', 'codex_local_isbe')

# Load priority circles
with open(os.path.join(ISBE_DIR, 'isbe-priority-circles.json'), 'r', encoding='utf-8-sig') as f:
    circles = json.load(f)

circle_by_mot = {c['mot']: c['circle'] for c in circles}
concept_by_mot = {c['mot']: c.get('matched_concept_id') for c in circles}

# Load chunk manifest
with open(os.path.join(ISBE_DIR, 'manifests', 'chunk_manifest.json'), 'r', encoding='utf-8-sig') as f:
    manifest = json.load(f)

# Analyze each chunk
chunk_analysis = []
source_dir = os.path.join(ISBE_DIR, 'source_chunks')

for chunk_info in manifest:
    chunk_id = chunk_info['chunk_id']
    chunk_file = os.path.join(source_dir, f'{chunk_id}.source.json')

    if not os.path.exists(chunk_file):
        continue

    with open(chunk_file, 'r', encoding='utf-8-sig') as f:
        entries = json.load(f)

    circles_in_chunk = Counter()
    total_chars = 0
    c1_chars = 0
    c1_entries = []
    all_mots = []

    for e in entries:
        mot = e['mot'].strip()
        defn_len = len(e.get('definition', ''))
        circle = circle_by_mot.get(mot, 'unknown')
        circles_in_chunk[circle] += 1
        total_chars += defn_len
        all_mots.append(mot)

        if circle == 'C1':
            c1_chars += defn_len
            c1_entries.append({
                'mot': mot,
                'chars': defn_len,
                'concept': concept_by_mot.get(mot, '')
            })

    c1_count = circles_in_chunk.get('C1', 0)
    c2_count = circles_in_chunk.get('C2', 0)
    c3_count = circles_in_chunk.get('C3', 0)
    c4_count = circles_in_chunk.get('C4', 0)
    total_entries = len(entries)

    # Determine chunk priority
    c1_ratio = c1_count / max(total_entries, 1)

    chunk_analysis.append({
        'chunk_id': chunk_id,
        'total_entries': total_entries,
        'total_chars': total_chars,
        'c1_count': c1_count,
        'c2_count': c2_count,
        'c3_count': c3_count,
        'c4_count': c4_count,
        'c1_ratio': round(c1_ratio, 2),
        'c1_chars': c1_chars,
        'c1_entries': c1_entries,
        'chunk_mode': chunk_info.get('chunk_mode', ''),
    })

# Classify chunks
pure_c1 = [c for c in chunk_analysis if c['c1_count'] > 0 and c['c2_count'] == 0 and c['c3_count'] == 0 and c['c4_count'] == 0]
mixed_c1 = [c for c in chunk_analysis if c['c1_count'] > 0 and (c['c2_count'] > 0 or c['c3_count'] > 0 or c['c4_count'] > 0)]
has_c1 = [c for c in chunk_analysis if c['c1_count'] > 0]
no_c1 = [c for c in chunk_analysis if c['c1_count'] == 0]

print("=== V1 CHUNK IDENTIFICATION ===")
print(f"Total chunks: {len(chunk_analysis)}")
print(f"Chunks with C1 entries: {len(has_c1)}")
print(f"  Pure C1 chunks: {len(pure_c1)}")
print(f"  Mixed C1 chunks: {len(mixed_c1)}")
print(f"Chunks without C1: {len(no_c1)}")

# V1 translation scope: translate ALL chunks that contain C1 entries
# (since chunks are atomic units, we translate the whole chunk even if mixed)
v1_chunks = sorted(has_c1, key=lambda c: int(c['chunk_id'].replace('chunk_', '')))

total_v1_entries = sum(c['total_entries'] for c in v1_chunks)
total_v1_chars = sum(c['total_chars'] for c in v1_chunks)
total_c1_entries = sum(c['c1_count'] for c in v1_chunks)
total_c1_chars = sum(c['c1_chars'] for c in v1_chunks)

print(f"\n=== V1 TRANSLATION SCOPE ===")
print(f"Chunks to translate: {len(v1_chunks)}")
print(f"Total entries in V1 chunks: {total_v1_entries}")
print(f"  of which C1: {total_c1_entries}")
print(f"  of which C2/C3/C4: {total_v1_entries - total_c1_entries}")
print(f"Total chars: {total_v1_chars:,}")
print(f"  C1 chars: {total_c1_chars:,}")

# Size distribution of V1 chunks
print(f"\n=== V1 CHUNK SIZE DISTRIBUTION ===")
size_buckets = {'small (<10k)': 0, 'medium (10-30k)': 0, 'large (30-60k)': 0, 'xlarge (>60k)': 0}
for c in v1_chunks:
    if c['total_chars'] < 10000:
        size_buckets['small (<10k)'] += 1
    elif c['total_chars'] < 30000:
        size_buckets['medium (10-30k)'] += 1
    elif c['total_chars'] < 60000:
        size_buckets['large (30-60k)'] += 1
    else:
        size_buckets['xlarge (>60k)'] += 1

for k, v in size_buckets.items():
    print(f"  {k}: {v}")

# Save V1 chunk list
v1_manifest = {
    'description': 'V1 translation chunks - all chunks containing C1 entries',
    'total_chunks': len(v1_chunks),
    'total_entries': total_v1_entries,
    'total_chars': total_v1_chars,
    'c1_entries': total_c1_entries,
    'c1_chars': total_c1_chars,
    'chunks': [{
        'chunk_id': c['chunk_id'],
        'total_entries': c['total_entries'],
        'total_chars': c['total_chars'],
        'c1_count': c['c1_count'],
        'c2_count': c['c2_count'],
        'c3_count': c['c3_count'],
        'c4_count': c['c4_count'],
        'c1_ratio': c['c1_ratio'],
        'chunk_mode': c['chunk_mode'],
    } for c in v1_chunks]
}

v1_path = os.path.join(ISBE_DIR, 'manifests', 'v1_chunks_manifest.json')
with open(v1_path, 'w', encoding='utf-8') as f:
    json.dump(v1_manifest, f, ensure_ascii=False, indent=2)

print(f"\nV1 manifest saved: {v1_path}")

# Show first 20 V1 chunks
print(f"\n=== V1 CHUNKS (first 30) ===")
print(f"{'Chunk':<15} {'Entries':>8} {'Chars':>10} {'C1':>5} {'C2':>5} {'C3':>5} {'C4':>5} {'C1%':>6} {'Mode'}")
print('-' * 80)
for c in v1_chunks[:30]:
    print(f"{c['chunk_id']:<15} {c['total_entries']:>8} {c['total_chars']:>10,} {c['c1_count']:>5} {c['c2_count']:>5} {c['c3_count']:>5} {c['c4_count']:>5} {c['c1_ratio']:>5.0%} {c['chunk_mode']}")

# Also save V2 (C2-only) and V3 (C3-only) manifests for future
v2_chunks = [c for c in chunk_analysis if c['c1_count'] == 0 and c['c2_count'] > 0]
v3_chunks = [c for c in chunk_analysis if c['c1_count'] == 0 and c['c2_count'] == 0 and c['c3_count'] > 0]
c4_only = [c for c in chunk_analysis if c['c1_count'] == 0 and c['c2_count'] == 0 and c['c3_count'] == 0 and c['c4_count'] > 0]

print(f"\n=== FUTURE WAVES ===")
print(f"V2 chunks (C2 only, no C1): {len(v2_chunks)} chunks, {sum(c['total_entries'] for c in v2_chunks)} entries")
print(f"V3 chunks (C3 only): {len(v3_chunks)} chunks, {sum(c['total_entries'] for c in v3_chunks)} entries")
print(f"C4-only chunks: {len(c4_only)} chunks (already transposed)")
