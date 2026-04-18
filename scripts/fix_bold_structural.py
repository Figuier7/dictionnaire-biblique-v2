#!/usr/bin/env python3
"""
fix_bold_structural.py — Vague 1 : gras structurel sur les sous-titres internes.

Règles appliquées :
  R1  Chiffres romains + CAPS : "I. TEMPS DE SEMAILLES" → "**I. TEMPS DE SEMAILLES.**"
  R2  Sous-titres Smith nommés : "Ordinaire. Oindre..." → "**Ordinaire.** Oindre..."
      Pattern: début de paragraphe + Mot(s) capitalisé(s) + "." + (" — " ou espace+texte)
      Seulement dans les définitions > 500 chars avec structure évidente.

Ne touche PAS :
  - Numéros (1), (2) — déjà visuels
  - Mots isolés
  - Définitions courtes
  - Texte déjà en gras
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

# Check BOM for concepts
concepts_raw = (BASE / "uploads/dictionnaires/concepts.json").read_bytes()
concepts_bom = concepts_raw[:3] == b'\xef\xbb\xbf'

# Detect BOM for each source
easton_bom = EASTON_PATH.read_bytes()[:3] == b'\xef\xbb\xbf'
smith_bom = SMITH_PATH.read_bytes()[:3] == b'\xef\xbb\xbf'
bym_bom = BYM_PATH.read_bytes()[:3] == b'\xef\xbb\xbf'

print(f"Easton: {len(easton)} entrées")
print(f"Smith: {len(smith)} entrées")
print(f"BYM: {len(bym)} entrées")

# ═══════════════════════════════════════════════════
# R1: Chiffres romains en CAPS → gras
# Pattern: "I. MOT(S) EN CAPS" ou "II. MOT(S) EN CAPS."
# Found in Easton and Smith
# ═══════════════════════════════════════════════════
print("\n── R1: Chiffres romains + CAPS → gras ──")

ROMAN = r'(?:I{1,3}V?|IV|VI{0,3}|IX|X{0,3})'

# Pattern: Roman numeral + ". " + UPPERCASE WORDS (+ optional period)
# At start of line or after \n\n
r1_pattern = re.compile(
    r"(?:^|\n)(" + ROMAN + r"\.\s+[A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ][A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ\s,'\-]+\.?)"
)

r1_count = 0
r1_entries = 0

for dataset_name, dataset in [("easton", easton), ("smith", smith)]:
    for entry in dataset:
        d = entry.get("definition", "")
        if len(d) < 500:
            continue
        if '**' in d:
            continue  # Already has bold

        new_d = d
        matches = list(r1_pattern.finditer(d))
        if not matches:
            continue

        # Only proceed if there are at least 2 roman numeral sections
        if len(matches) < 2:
            continue

        # Apply bold to each match
        offset = 0
        for m in matches:
            title = m.group(1).strip()
            # Skip if too long (probably not a title)
            if len(title) > 80:
                continue
            # Skip if already bold
            if '**' in title:
                continue

            start = m.start(1) + offset
            end = m.end(1) + offset
            bold_title = f"**{title.strip()}**"
            new_d = new_d[:start] + ('\n' if m.group(0).startswith('\n') else '') + bold_title + new_d[end:]
            offset += len(bold_title) - (end - start) + (1 if m.group(0).startswith('\n') else 0) - (1 if m.group(0).startswith('\n') else 0)

        if new_d != d:
            # Recompute more carefully with simple replacements
            pass

    # Simpler approach: line-by-line replacement
for dataset_name, dataset in [("easton", easton), ("smith", smith)]:
    ds_count = 0
    for entry in dataset:
        d = entry.get("definition", "")
        if len(d) < 500 or '**' in d:
            continue

        lines = d.split('\n')
        changed = False

        # First pass: count roman numeral lines
        roman_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            m = re.match(r"^(" + ROMAN + r")\.\s+([A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ][A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ\s,'\-]+\.?)\s*(.*)", stripped)
            if m:
                roman_lines.append(i)

        if len(roman_lines) < 2:
            continue

        # Apply bold
        for i in roman_lines:
            stripped = lines[i].strip()
            m = re.match(r"^(" + ROMAN + r"\.\s+[A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ][A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ\s,'\-]+\.?)\s*(.*)", stripped)
            if m:
                title_part = m.group(1).strip()
                rest = m.group(2)
                if len(title_part) <= 80:
                    lines[i] = f"**{title_part}** {rest}".rstrip()
                    changed = True

        if changed:
            entry["definition"] = '\n'.join(lines)
            ds_count += 1
            r1_count += 1

    print(f"  {dataset_name}: {ds_count} entrées")

r1_entries = r1_count

# ═══════════════════════════════════════════════════
# R2: Sous-titres nommés Smith
# Pattern: début de paragraphe (after \n\n) + Mot(s) capitalisé(s) + "." + " — " ou suite
# Only in definitions > 800 chars that have at least 2 such sub-titles
# ═══════════════════════════════════════════════════
print("\n── R2: Sous-titres nommés → gras ──")

# Pattern: after \n\n, a capitalized word (1-4 words) followed by "." then " — " or " – " or space
# The title must be short (< 60 chars), start with uppercase, end with period
r2_title_pattern = re.compile(
    r'(?<=\n\n)([A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ][a-zéèêëàâäîïôöùûüçA-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ\' ]{1,55}\.)\s*(—|–|\s)'
)

r2_count = 0

for entry in smith:
    d = entry.get("definition", "")
    if len(d) < 800 or '**' in d:
        continue

    # Find all potential titles
    matches = list(r2_title_pattern.finditer(d))
    if len(matches) < 2:
        continue

    # Validate: titles should be short (1-4 words before the period)
    valid_matches = []
    for m in matches:
        title = m.group(1)
        words = title.rstrip('.').split()
        if 1 <= len(words) <= 6:
            valid_matches.append(m)

    if len(valid_matches) < 2:
        continue

    # Apply bold to each title
    new_d = d
    offset = 0
    for m in valid_matches:
        title = m.group(1)
        start = m.start(1) + offset
        end = m.end(1) + offset
        bold_title = f"**{title}**"
        new_d = new_d[:start] + bold_title + new_d[end:]
        offset += 4  # len("****") = 4

    if new_d != d:
        entry["definition"] = new_d
        r2_count += 1

print(f"  smith: {r2_count} entrées")

# ═══════════════════════════════════════════════════
# R2b: Sous-titres "I. MATÉRIELLE" type inline (Smith)
# Pattern: "I. MOT" or "II. MOT" inline (not necessarily on their own line)
# ═══════════════════════════════════════════════════
print("\n── R2b: Sous-titres romains inline Smith → gras ──")

r2b_count = 0
for entry in smith:
    d = entry.get("definition", "")
    if len(d) < 500:
        continue
    if '**' in d and d.count('**') > 2:
        continue  # Already has significant bold

    # Find inline roman numeral patterns: "I. Mot" "II. Mot" in the middle of text
    # These are NOT on their own line
    matches = list(re.finditer(r'(?<!\*\*)\b(' + ROMAN + r'\.\s+[A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ][A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ]+(?:\.\s*—?)?)(?!\*)', d))

    if len(matches) < 2:
        continue

    new_d = d
    offset = 0
    for m in matches:
        title = m.group(1).strip()
        if len(title) > 60:
            continue
        start = m.start(1) + offset
        end = m.end(1) + offset
        bold = f"**{title}**"
        new_d = new_d[:start] + bold + new_d[end:]
        offset += 4

    if new_d != d:
        entry["definition"] = new_d
        r2b_count += 1

print(f"  smith: {r2b_count} entrées")

# ═══════════════════════════════════════════════════
# Also apply R1/R2b to Easton for inline roman numerals
# ═══════════════════════════════════════════════════
print("\n── R2b: Sous-titres romains inline Easton → gras ──")

r2b_easton = 0
for entry in easton:
    d = entry.get("definition", "")
    if len(d) < 500:
        continue
    if '**' in d and d.count('**') > 2:
        continue

    matches = list(re.finditer(r'(?<!\*\*)\b(' + ROMAN + r'\.\s+[A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ][A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ]+(?:\.\s*—?)?)(?!\*)', d))

    if len(matches) < 2:
        continue

    new_d = d
    offset = 0
    for m in matches:
        title = m.group(1).strip()
        if len(title) > 60:
            continue
        start = m.start(1) + offset
        end = m.end(1) + offset
        bold = f"**{title}**"
        new_d = new_d[:start] + bold + new_d[end:]
        offset += 4

    if new_d != d:
        entry["definition"] = new_d
        r2b_easton += 1

print(f"  easton: {r2b_easton} entrées")

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
# Summary
# ═══════════════════════════════════════════════════
total = r1_entries + r2_count + r2b_count + r2b_easton
print(f"\n══════════════════════════════════════")
print(f"  RÉSUMÉ GRAS STRUCTUREL — VAGUE 1")
print(f"══════════════════════════════════════")
print(f"  R1  Chiffres romains CAPS:          {r1_entries} entrées")
print(f"  R2  Sous-titres nommés (Smith):      {r2_count} entrées")
print(f"  R2b Romans inline (Smith):           {r2b_count} entrées")
print(f"  R2b Romans inline (Easton):          {r2b_easton} entrées")
print(f"  ──────────────────────────────────")
print(f"  TOTAL entrées avec gras structurel:  {total}")
print(f"══════════════════════════════════════")
