#!/usr/bin/env python3
"""
fix_bold_structural_v2.py — Vague 1 PROPRE : gras structurel uniquement sur cas sûrs.

R1  Chiffres romains en CAPS sur leur propre ligne (Easton): "I. TEMPS DE SEMAILLES."
R2  Sous-titres nommés après \n\n (Smith): "Ordinaire." / "Étendue. —"

NE TOUCHE PAS aux chiffres romains inline (trop de faux positifs).
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
BYM_PATH = BASE / "uploads/dictionnaires/bym/bym-lexicon.entries.json"

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
bym = load_json(BYM_PATH)

easton_bom = EASTON_PATH.read_bytes()[:3] == b'\xef\xbb\xbf'
smith_bom = SMITH_PATH.read_bytes()[:3] == b'\xef\xbb\xbf'
bym_bom = BYM_PATH.read_bytes()[:3] == b'\xef\xbb\xbf'

# ═══════════════════════════════════════════════════
# STEP 0: Remove ALL existing ** from previous bad run
# ═══════════════════════════════════════════════════
print("── Nettoyage du gras existant ──")
cleaned = 0
for dataset in [easton, smith, bym]:
    for entry in dataset:
        d = entry.get("definition", "")
        if "**" in d:
            entry["definition"] = d.replace("**", "")
            cleaned += 1
print(f"  Nettoyé: {cleaned} entrées")

# ═══════════════════════════════════════════════════
# R1: Chiffres romains en CAPS sur ligne propre
# Pattern: line starts with "I. TEXTE EN CAPS" / "II. TEXTE EN CAPS"
# Requires 2+ such lines in the same definition
# ═══════════════════════════════════════════════════
print("\n── R1: Chiffres romains CAPS sur ligne propre → gras ──")

ROMAN_PAT = r'(?:I{1,3}V?|IV|VI{0,3}|IX|X{1,3})'

r1_count = 0
r1_examples = []

for ds_name, dataset in [("easton", easton), ("smith", smith)]:
    ds_count = 0
    for entry in dataset:
        d = entry.get("definition", "")
        if len(d) < 500:
            continue

        lines = d.split('\n')
        # Find lines that match: "I. UPPERCASE WORDS"
        roman_indices = []
        for i, line in enumerate(lines):
            s = line.strip()
            m = re.match(r'^(' + ROMAN_PAT + r')\.\s+([A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ][A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ\s,\'\-]+)\.?\s*(.*)', s)
            if m:
                title = m.group(1) + '. ' + m.group(2).strip()
                rest = m.group(3) or ''
                # Title must be at most 60 chars
                if len(title) <= 60:
                    roman_indices.append((i, title, rest))

        if len(roman_indices) < 2:
            continue

        # Apply bold
        for i, title, rest in roman_indices:
            stripped = lines[i].strip()
            # Preserve leading whitespace
            leading = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
            if rest:
                lines[i] = f"{leading}**{title}.** {rest}"
            else:
                lines[i] = f"{leading}**{title}.**"

        entry["definition"] = '\n'.join(lines)
        ds_count += 1
        if len(r1_examples) < 5:
            r1_examples.append({"id": entry["id"], "mot": entry["mot"], "titles": [t for _, t, _ in roman_indices]})

    r1_count += ds_count
    print(f"  {ds_name}: {ds_count}")

for ex in r1_examples:
    print(f"    {ex['mot']}: {ex['titles']}")

# ═══════════════════════════════════════════════════
# R2: Sous-titres nommés dans Smith (après \n\n)
# Pattern: paragraph starts with 1-6 capitalized words + "." + (" — " or space)
# Requires 2+ such titles in the same definition
# ═══════════════════════════════════════════════════
print("\n── R2: Sous-titres nommés Smith → gras ──")

r2_count = 0
r2_examples = []

# Pattern: after double newline, capitalized phrase (1-6 words) ending with period
# Followed by " — " or just a space and lowercase continuation
r2_title_re = re.compile(
    r'(\n\n)'
    r'([A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ][a-zéèêëàâäîïôöùûüçA-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ\' ]{1,55}\.)'
    r'(\s*(?:—|–)\s*|\s+)'
)

for entry in smith:
    d = entry.get("definition", "")
    if len(d) < 800:
        continue

    # Find all potential titles
    matches = list(r2_title_re.finditer(d))

    # Filter: title must be 1-6 words
    valid = []
    for m in matches:
        title = m.group(2).rstrip('.')
        words = title.split()
        if 1 <= len(words) <= 8:
            valid.append(m)

    if len(valid) < 2:
        continue

    # Apply bold (process from end to start to preserve positions)
    new_d = d
    for m in reversed(valid):
        title = m.group(2)
        start = m.start(2)
        end = m.end(2)
        new_d = new_d[:start] + f"**{title}**" + new_d[end:]

    if new_d != d:
        entry["definition"] = new_d
        r2_count += 1
        if len(r2_examples) < 8:
            titles = [m.group(2) for m in valid]
            r2_examples.append({"id": entry["id"], "mot": entry["mot"], "titles": titles})

print(f"  smith: {r2_count}")
for ex in r2_examples:
    print(f"    {ex['mot']}: {ex['titles']}")

# ═══════════════════════════════════════════════════
# R2b: Sous-titres nommés dans Easton (après \n\n)
# Same logic, applied to Easton
# ═══════════════════════════════════════════════════
print("\n── R2b: Sous-titres nommés Easton → gras ──")

r2b_count = 0

for entry in easton:
    d = entry.get("definition", "")
    if len(d) < 800:
        continue

    matches = list(r2_title_re.finditer(d))
    valid = [m for m in matches if 1 <= len(m.group(2).rstrip('.').split()) <= 8]

    if len(valid) < 2:
        continue

    new_d = d
    for m in reversed(valid):
        title = m.group(2)
        start = m.start(2)
        end = m.end(2)
        new_d = new_d[:start] + f"**{title}**" + new_d[end:]

    if new_d != d:
        entry["definition"] = new_d
        r2b_count += 1

print(f"  easton: {r2b_count}")

# ═══════════════════════════════════════════════════
# Update definition_length
# ═══════════════════════════════════════════════════
for dataset in [easton, smith, bym]:
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
save_json(BYM_PATH, bym, bom=bym_bom)
print(f"  {BYM_PATH.name}")

# ═══════════════════════════════════════════════════
total = r1_count + r2_count + r2b_count
print(f"\n══════════════════════════════════════")
print(f"  RÉSUMÉ GRAS STRUCTUREL — VAGUE 1")
print(f"══════════════════════════════════════")
print(f"  R1  Chiffres romains CAPS (ligne):   {r1_count}")
print(f"  R2  Sous-titres nommés (Smith):       {r2_count}")
print(f"  R2b Sous-titres nommés (Easton):      {r2b_count}")
print(f"  ──────────────────────────────────")
print(f"  TOTAL:                                {total} entrées")
print(f"══════════════════════════════════════")
