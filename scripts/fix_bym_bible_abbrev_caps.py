#!/usr/bin/env python3
"""
fix_bym_bible_abbrev_caps.py — Capitalise les abréviations de livres bibliques
dans les définitions BYM.

Règle : quand une abréviation biblique est suivie de ". chiffre" (référence),
la première lettre doit être en majuscule.

Exemples :
  ge. 12:1  → Ge. 12:1
  1 co. 12  → 1 Co. 12
  2 r. 15   → 2 R. 15
"""

import json
import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(r"C:\Users\caeng\OneDrive\Documents\A l'ombre du figuier\dictionnaire-biblique-main")
BYM_PATH = BASE / "uploads" / "dictionnaires" / "bym" / "bym-lexicon.entries.json"

raw = BYM_PATH.read_bytes()
has_bom = raw[:3] == b'\xef\xbb\xbf'
bym = json.loads(raw.decode('utf-8-sig') if has_bom else raw.decode('utf-8'))
print(f"BYM: {len(bym)} entrées chargées\n")

# ══════════════════════════════════════════════════
# Abréviations bibliques → forme capitalisée
# ══════════════════════════════════════════════════
BIBLE_BOOKS = {
    # AT
    'ge': 'Ge', 'ex': 'Ex', 'lé': 'Lé', 'lév': 'Lév', 'no': 'No',
    'de': 'De', 'jos': 'Jos', 'jas': 'Jas', 'jug': 'Jug', 'jg': 'Jg',
    'ru': 'Ru',
    # AT suite
    'ps': 'Ps', 'pr': 'Pr', 'ec': 'Ec', 'ct': 'Ct',
    'es': 'Es', 'jé': 'Jé', 'la': 'La', 'éz': 'Éz', 'da': 'Da',
    'os': 'Os', 'joë': 'Joë', 'am': 'Am', 'ab': 'Ab', 'jon': 'Jon',
    'mi': 'Mi', 'na': 'Na', 'ha': 'Ha', 'so': 'So', 'ag': 'Ag',
    'za': 'Za', 'mal': 'Mal', 'esd': 'Esd', 'né': 'Né',
    # NT
    'mt': 'Mt', 'mc': 'Mc', 'lu': 'Lu', 'jn': 'Jn', 'ac': 'Ac',
    'ro': 'Ro', 'ga': 'Ga', 'ép': 'Ép', 'éph': 'Éph', 'ep': 'Ep',
    'ph': 'Ph', 'col': 'Col', 'ti': 'Ti', 'tt': 'Tt',
    'hé': 'Hé', 'ja': 'Ja', 'pi': 'Pi', 'phm': 'Phm',
    'jud': 'Jud', 'ap': 'Ap',
    # Livres numérotés (partie après le chiffre)
    'co': 'Co', 'th': 'Th', 'r': 'R', 's': 'S', 'chr': 'Chr',
}

# ══════════════════════════════════════════════════
# Phase 1 : Abréviations simples (ge. 12:1)
# Pattern : non-lettre + abréviation + ". " + chiffre
# ══════════════════════════════════════════════════
print("── Phase 1: Abréviations simples ──")

# Sort by length descending to match longer abbreviations first
sorted_abbrevs = sorted(BIBLE_BOOKS.keys(), key=len, reverse=True)

# Build one big regex for efficiency
# Match: (word boundary or non-letter)(lowercase_abbrev)(. )(digit)
# We need to capitalize group 2

p1_count = 0
p1_entries = 0

for entry in bym:
    d = entry.get("definition", "")
    if not d:
        continue

    original = d

    for abbr in sorted_abbrevs:
        cap = BIBLE_BOOKS[abbr]
        if abbr == cap.lower() and abbr in d.lower():
            # Pattern: non-letter before, then lowercase abbrev, then ". " then digit
            # Use negative lookbehind for letters
            pattern = r'(?<![a-zA-ZÀ-ÿ])' + re.escape(abbr) + r'(?=\.\s*\d)'

            def replacer(m):
                found = m.group(0)
                # Only replace if first char is actually lowercase
                if found[0].islower():
                    return cap
                return found

            d = re.sub(pattern, replacer, d)

    if d != original:
        entry["definition"] = d
        p1_count += sum(1 for a, b in zip(original, d) if a != b)
        p1_entries += 1

print(f"  {p1_count} caractères modifiés dans {p1_entries} entrées")

# ══════════════════════════════════════════════════
# Phase 2 : Abréviations après "Voir" et ";"
# Cas: "Voir ge." ou "; ge." sans chiffre immédiat
# (le chiffre peut être sur la ligne suivante)
# ══════════════════════════════════════════════════
print("\n── Phase 2: Abréviations après Voir/; ──")

p2_count = 0
p2_entries = 0

for entry in bym:
    d = entry.get("definition", "")
    if not d:
        continue

    original = d

    for abbr in sorted_abbrevs:
        cap = BIBLE_BOOKS[abbr]
        if abbr in d.lower():
            # Pattern: after "Voir " or "; " or "et " then lowercase abbrev then "."
            pattern = r'(?<=Voir\s)' + re.escape(abbr) + r'(?=\.)'
            d = re.sub(pattern, lambda m: cap if m.group(0)[0].islower() else m.group(0), d)

            pattern2 = r'(?<=;\s)' + re.escape(abbr) + r'(?=\.)'
            d = re.sub(pattern2, lambda m: cap if m.group(0)[0].islower() else m.group(0), d)

            pattern3 = r'(?<=et\s)' + re.escape(abbr) + r'(?=\.)'
            d = re.sub(pattern3, lambda m: cap if m.group(0)[0].islower() else m.group(0), d)

    if d != original:
        entry["definition"] = d
        changes = sum(1 for a, b in zip(original, d) if a != b)
        p2_count += changes
        p2_entries += 1

print(f"  {p2_count} caractères modifiés dans {p2_entries} entrées")

# ══════════════════════════════════════════════════
# Vérification : compter les abréviations restantes en minuscule
# ══════════════════════════════════════════════════
print("\n── Vérification ──")
remaining = 0
for entry in bym:
    d = entry.get("definition", "")
    for abbr in sorted_abbrevs:
        for m in re.finditer(r'(?<![a-zA-ZÀ-ÿ])' + re.escape(abbr) + r'\.\s*\d', d):
            if m.group(0)[0].islower():
                remaining += 1

print(f"  Abréviations bibliques encore en minuscule: {remaining}")

# ══════════════════════════════════════════════════
# Update definition_length + Save
# ══════════════════════════════════════════════════
for entry in bym:
    entry["definition_length"] = len(entry.get("definition", ""))

text = json.dumps(bym, ensure_ascii=False, indent=2)
if has_bom:
    BYM_PATH.write_bytes(b'\xef\xbb\xbf' + text.encode('utf-8'))
else:
    BYM_PATH.write_bytes(text.encode('utf-8'))
print(f"\n  Sauvegardé: {BYM_PATH.name}")

total = p1_count + p2_count
print(f"\n══════════════════════════════════════════════")
print(f"  RÉSUMÉ — ABRÉVIATIONS BIBLIQUES BYM")
print(f"══════════════════════════════════════════════")
print(f"  Phase 1 — Avant chiffre:     {p1_count} ({p1_entries} entrées)")
print(f"  Phase 2 — Après Voir/;/et:   {p2_count} ({p2_entries} entrées)")
print(f"  Restantes en minuscule:       {remaining}")
print(f"  ──────────────────────────────────────────")
print(f"  TOTAL:  {total} corrections")
print(f"══════════════════════════════════════════════")
