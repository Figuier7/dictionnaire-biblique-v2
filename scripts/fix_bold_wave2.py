#!/usr/bin/env python3
"""
fix_bold_wave2.py — Vague 2 : gras structurel sur marqueurs numériques et romains.

V2-R1  Easton: **(1)**, **(2)** etc. en début de paragraphe structurel
V2-R2  Easton: **(a)**, **(b)** etc. en début de paragraphe structurel
V2-R3  Smith: **I. Titre** pour chiffres romains inline avec titre

Seuil: ≥ 2 marqueurs du même type dans la même définition, définition > 500 chars.
"""

import json
import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(r"C:\Users\caeng\OneDrive\Documents\A l'ombre du figuier\dictionnaire-biblique-main")
EASTON_PATH = BASE / "uploads/dictionnaires/easton/easton.entries.json"
SMITH_PATH = BASE / "uploads/dictionnaires/smith/smith.entries.json"

def load_json(path):
    raw = path.read_bytes()
    return json.loads(raw.decode('utf-8-sig') if raw[:3] == b'\xef\xbb\xbf' else raw.decode('utf-8'))

def save_json(path, data, bom=False):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if bom:
        path.write_bytes(b'\xef\xbb\xbf' + text.encode('utf-8'))
    else:
        path.write_bytes(text.encode('utf-8'))

easton = load_json(EASTON_PATH)
smith = load_json(SMITH_PATH)

easton_bom = EASTON_PATH.read_bytes()[:3] == b'\xef\xbb\xbf'
smith_bom = SMITH_PATH.read_bytes()[:3] == b'\xef\xbb\xbf'

# ═══════════════════════════════════════════════════
# V2-R1: Easton — Bold structural (N) markers
# Pattern: \n\n(N) at start of a structural paragraph
# Requires: ≥ 2 numbered markers, definition > 500 chars
# ═══════════════════════════════════════════════════
print("── V2-R1: Easton (N) markers → gras ──")

v2r1_count = 0
v2r1_markers = 0

for entry in easton:
    d = entry.get("definition", "")
    if len(d) < 500:
        continue

    # Find structural (N) markers: after \n\n, then (digit) or (digit.)
    # Pattern: \n\n(1) or \n\n(1.)
    pattern = re.compile(r'(\n\n)(\(\d+\)\.?|\(\d+\.\))')
    matches = list(pattern.finditer(d))

    if len(matches) < 2:
        continue

    # Check that the numbers form a sequence starting at 1
    numbers = []
    for m in matches:
        num_text = m.group(2)
        num = int(re.search(r'\d+', num_text).group())
        numbers.append(num)

    if 1 not in numbers:
        continue

    # Apply bold to each marker (process from end to preserve positions)
    new_d = d
    offset = 0
    applied = 0
    for m in matches:
        marker = m.group(2)
        # Skip if already bold
        before_start = max(0, m.start(2) + offset - 2)
        if new_d[before_start:m.start(2) + offset].endswith('**'):
            continue

        start = m.start(2) + offset
        end = m.end(2) + offset
        bold_marker = f"**{marker}**"
        new_d = new_d[:start] + bold_marker + new_d[end:]
        offset += 4  # len("****")
        applied += 1

    if applied >= 2:
        entry["definition"] = new_d
        v2r1_count += 1
        v2r1_markers += applied

print(f"  Entrées: {v2r1_count}, marqueurs: {v2r1_markers}")

# ═══════════════════════════════════════════════════
# V2-R2: Easton — Bold structural (a) (b) markers
# Same logic for lettered sub-sections
# ═══════════════════════════════════════════════════
print("\n── V2-R2: Easton (a)(b) markers → gras ──")

v2r2_count = 0
v2r2_markers = 0

for entry in easton:
    d = entry.get("definition", "")
    if len(d) < 500:
        continue

    # Find structural (a) (b) markers
    pattern = re.compile(r'(\n\n)(\([a-z]\))')
    matches = list(pattern.finditer(d))

    if len(matches) < 2:
        continue

    # Check sequential letters
    letters = [m.group(2)[1] for m in matches]  # extract letter
    if 'a' not in letters:
        continue

    new_d = d
    offset = 0
    applied = 0
    for m in matches:
        marker = m.group(2)
        start = m.start(2) + offset
        end = m.end(2) + offset

        # Skip if already bold
        if start >= 2 and new_d[start-2:start] == '**':
            continue

        bold_marker = f"**{marker}**"
        new_d = new_d[:start] + bold_marker + new_d[end:]
        offset += 4
        applied += 1

    if applied >= 2:
        entry["definition"] = new_d
        v2r2_count += 1
        v2r2_markers += applied

print(f"  Entrées: {v2r2_count}, marqueurs: {v2r2_markers}")

# ═══════════════════════════════════════════════════
# V2-R3: Smith — Bold inline Roman numerals with titles
# Pattern: "I. TITLE" or "II. Title" inline in the text
# The title must be a capitalized word/phrase (1-5 words)
# ═══════════════════════════════════════════════════
print("\n── V2-R3: Smith inline Roman numerals → gras ──")

ROMAN_PAT = r'(?:I{1,3}V?|IV|VI{0,3}|IX|X{1,3})'

v2r3_count = 0
v2r3_markers = 0
v2r3_examples = []

for entry in smith:
    d = entry.get("definition", "")
    if len(d) < 500:
        continue
    # Skip entries already having bold from wave 1
    if '**' in d:
        continue

    # Find inline Roman numeral markers: "I. " followed by text
    # Must NOT be at the very start of the definition
    # Pattern: space or newline + Roman + ". " + Capitalized word(s)
    pattern = re.compile(
        r'(?:^|\s)(' + ROMAN_PAT + r')\.\s+'
        r'([A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ][A-Za-zéèêëàâäîïôöùûüçÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ\s,\'-]{0,60}?)(?=\.\s|,\s|\s—|\s–|\n)'
    )
    matches = list(pattern.finditer(d))

    if len(matches) < 2:
        continue

    # Validate: Roman numerals should form a sequence
    romans = []
    roman_vals = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10}
    for m in matches:
        r = m.group(1)
        if r in roman_vals:
            romans.append(roman_vals[r])

    if not romans or min(romans) > 5:
        continue

    # Apply bold: "**I. Title**"
    new_d = d
    offset = 0
    applied = 0

    for m in matches:
        roman = m.group(1)
        title = m.group(2).strip()

        # Skip very short titles (abbreviations)
        if len(title) < 3:
            continue

        # Skip titles that are just common words (not section headings)
        title_words = title.split()
        if len(title_words) > 8:
            continue

        full_text = f"{roman}. {title}"
        start = m.start(1) + offset
        end = m.start(1) + len(roman) + 2 + len(title) + offset  # roman + ". " + title

        # Safer: find exact match position
        search_text = f"{roman}. {title}"
        pos = new_d.find(search_text, m.start(1) + offset - 5)
        if pos == -1:
            continue

        # Skip if already bold
        if pos >= 2 and new_d[pos-2:pos] == '**':
            continue

        bold_text = f"**{search_text}**"
        new_d = new_d[:pos] + bold_text + new_d[pos + len(search_text):]
        offset += 4
        applied += 1

    if applied >= 2:
        entry["definition"] = new_d
        v2r3_count += 1
        v2r3_markers += applied
        if len(v2r3_examples) < 8:
            bolds = re.findall(r'\*\*(.+?)\*\*', new_d)
            v2r3_examples.append({"id": entry["id"], "mot": entry["mot"], "bolds": bolds})

print(f"  Entrées: {v2r3_count}, marqueurs: {v2r3_markers}")
for ex in v2r3_examples:
    print(f"    {ex['mot']}: {ex['bolds']}")

# ═══════════════════════════════════════════════════
# Update definition_length
# ═══════════════════════════════════════════════════
for dataset in [easton, smith]:
    for entry in dataset:
        entry["definition_length"] = len(entry.get("definition", ""))

# ═══════════════════════════════════════════════════
# Save
# ═══════════════════════════════════════════════════
print("\n── Sauvegarde ──")
save_json(EASTON_PATH, easton, bom=easton_bom)
print(f"  {EASTON_PATH.name}")
save_json(SMITH_PATH, smith, bom=smith_bom)
print(f"  {SMITH_PATH.name}")

# ═══════════════════════════════════════════════════
total = v2r1_count + v2r2_count + v2r3_count
total_markers = v2r1_markers + v2r2_markers + v2r3_markers
print(f"\n══════════════════════════════════════")
print(f"  RÉSUMÉ GRAS STRUCTUREL — VAGUE 2")
print(f"══════════════════════════════════════")
print(f"  V2-R1 Easton (N) marqueurs:     {v2r1_count} entrées, {v2r1_markers} marqueurs")
print(f"  V2-R2 Easton (a)(b) marqueurs:  {v2r2_count} entrées, {v2r2_markers} marqueurs")
print(f"  V2-R3 Smith romains inline:     {v2r3_count} entrées, {v2r3_markers} marqueurs")
print(f"  ──────────────────────────────────")
print(f"  TOTAL: {total} entrées, {total_markers} marqueurs")
print(f"══════════════════════════════════════")
