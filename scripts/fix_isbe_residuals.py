#!/usr/bin/env python3
"""Fix English residuals in ISBE translated chunks."""
import json, re, os, glob

isbe_dir = 'uploads/dictionnaires/isbe'
chunks = {}
for path in sorted(glob.glob(os.path.join(isbe_dir, 'isbe-*.json'))):
    letter = os.path.basename(path).replace('isbe-', '').replace('.json', '')
    with open(path, 'r', encoding='utf-8-sig') as f:
        chunks[letter] = json.load(f)

total = sum(len(v) for v in chunks.values())
print(f"Loaded {total} entries across {len(chunks)} chunks")

fixes = {
    'christ': 0, 'god': 0, 'jesus': 0,
    'new_testament': 0, 'old_testament': 0,
    'revised_version': 0, 'holy_spirit': 0,
}

for letter, entries in chunks.items():
    for e in entries:
        d = e['definition']

        # ── Christ → Mashiah ──
        has_mashiah = 'Mashiah' in d
        parts = re.split(r'(\bChrist\b)', d)
        rebuilt = []
        first_done = has_mashiah
        for part in parts:
            if part == 'Christ':
                before = ''.join(rebuilt)
                pre = before[-20:] if len(before) >= 20 else before
                if (pre.rstrip().endswith('Mashiah') or
                    pre.rstrip().endswith('ashiah') or
                    pre.rstrip().endswith('-') or
                    pre.rstrip().endswith('sus')):
                    rebuilt.append(part)
                elif not first_done:
                    rebuilt.append('Mashiah (Christ)')
                    first_done = True
                    fixes['christ'] += 1
                else:
                    rebuilt.append('Mashiah')
                    fixes['christ'] += 1
            else:
                rebuilt.append(part)
        d = ''.join(rebuilt)

        # ── God → Elohim ──
        has_elohim = 'Eloh' in d
        parts = re.split(r'(\bGod\b)', d)
        rebuilt = []
        first_done = has_elohim
        for part in parts:
            if part == 'God':
                before = ''.join(rebuilt)
                pre = before[-25:] if len(before) >= 25 else before
                if 'Eloh' in pre or 'loh' in pre[-8:]:
                    rebuilt.append(part)
                elif not first_done:
                    rebuilt.append('Elohim (Dieu)')
                    first_done = True
                    fixes['god'] += 1
                else:
                    rebuilt.append('Elohim')
                    fixes['god'] += 1
            else:
                rebuilt.append(part)
        d = ''.join(rebuilt)

        # ── Jesus → Yehoshoua ──
        has_y = 'hoshoua' in d
        parts = re.split(r'(\bJesus\b)', d)
        rebuilt = []
        first_done = has_y
        for part in parts:
            if part == 'Jesus':
                before = ''.join(rebuilt)
                pre = before[-25:] if len(before) >= 25 else before
                if 'hoshoua' in pre or pre.rstrip().endswith('-'):
                    rebuilt.append(part)
                elif not first_done:
                    rebuilt.append('Yehoshoua (Jesus)')
                    first_done = True
                    fixes['jesus'] += 1
                else:
                    rebuilt.append('Yehoshoua')
                    fixes['jesus'] += 1
            else:
                rebuilt.append(part)
        d = ''.join(rebuilt)

        # ── New/Old Testament ──
        n = len(re.findall(r'\bNew Testament\b', d))
        if n:
            d = re.sub(r'\bNew Testament\b', 'Nouveau Testament', d)
            fixes['new_testament'] += n

        n = len(re.findall(r'\bOld Testament\b', d))
        if n:
            d = re.sub(r'\bOld Testament\b', 'Ancien Testament', d)
            fixes['old_testament'] += n

        # ── Revised Version ──
        n = len(re.findall(r'\bRevised Version\b', d))
        if n:
            d = re.sub(r'\bRevised Version\b', 'King James Version Revisee', d)
            fixes['revised_version'] += n

        # ── Holy Spirit/Ghost ──
        n = len(re.findall(r'\bHoly (?:Spirit|Ghost)\b', d))
        if n:
            d = re.sub(r'\bHoly Spirit\b', 'Saint-Esprit', d)
            d = re.sub(r'\bHoly Ghost\b', 'Saint-Esprit', d)
            fixes['holy_spirit'] += n

        e['definition'] = d

# Write back
for letter, ents in chunks.items():
    path = os.path.join(isbe_dir, f'isbe-{letter}.json')
    with open(path, 'w', encoding='utf-8-sig') as f:
        json.dump(ents, f, ensure_ascii=False)

print("\n=== CORRECTIONS ===")
t = 0
for k, v in fixes.items():
    print(f"  {k}: {v}")
    t += v
print(f"  TOTAL: {t}")
